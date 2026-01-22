"""
UCLA Gym Activity Tracker - Data Collector Service

This is the main service that runs continuously on a VPS.
It collects gym zone occupancy data every 15 minutes during operating hours.
"""

import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Optional

from config import (
    API_URL, COLLECTION_INTERVAL, TRACKED_ZONES, 
    OPERATING_HOURS, FACILITY_NAMES, JOHN_WOODEN_ID, BFIT_ID
)
from database import init_database, insert_reading
from aggregator import calculate_hourly_average

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collector.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def is_gym_open(facility_id: int, check_time: Optional[datetime] = None) -> bool:
    """
    Check if a gym is currently open based on operating hours.
    
    Args:
        facility_id: The facility ID to check
        check_time: Time to check (defaults to now)
    
    Returns:
        True if gym is open, False otherwise
    """
    if check_time is None:
        check_time = datetime.now()
    
    day_of_week = check_time.weekday()  # 0 = Monday, 4 = Friday, 5 = Saturday, 6 = Sunday
    
    # Gym is closed on weekends
    if day_of_week >= 5:  # Saturday or Sunday
        return False
    
    hours = OPERATING_HOURS.get(facility_id)
    if not hours:
        return False
    
    # Get the appropriate schedule
    if day_of_week == 4:  # Friday
        schedule = hours["friday"]
    else:  # Monday - Thursday
        schedule = hours["weekday"]
    
    open_hour, open_min, close_hour, close_min = schedule
    
    # Convert current time to minutes since midnight
    current_minutes = check_time.hour * 60 + check_time.minute
    open_minutes = open_hour * 60 + open_min
    close_minutes = close_hour * 60 + close_min
    
    # Handle overnight closing (e.g., 1:00 AM = 25:00)
    if close_hour >= 24:
        # If checking before midnight
        if current_minutes >= open_minutes:
            return True
        # If checking after midnight but before close
        close_minutes_adjusted = (close_hour - 24) * 60 + close_min
        if current_minutes < close_minutes_adjusted:
            return True
        return False
    
    return open_minutes <= current_minutes < close_minutes


def fetch_gym_data() -> Optional[list]:
    """
    Fetch current gym zone data from the API.
    
    Returns:
        List of zone data dictionaries, or None if fetch fails
    """
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch API data: {e}")
        return None


def collect_data():
    """
    Collect data for all tracked zones that are currently open.
    """
    now = datetime.now()
    data = fetch_gym_data()
    
    if not data:
        logger.warning("No data received from API")
        return
    
    collected_count = 0
    
    for zone in data:
        location_id = zone.get("LocationId")
        
        # Skip zones we're not tracking
        if location_id not in TRACKED_ZONES:
            continue
        
        facility_id = zone.get("FacilityId")
        
        # Skip if gym is closed
        if not is_gym_open(facility_id, now):
            continue
        
        # Extract data
        location_name = zone.get("LocationName", "Unknown")
        facility_name = FACILITY_NAMES.get(facility_id, zone.get("FacilityName", "Unknown"))
        count = zone.get("LastCount", 0)
        capacity = zone.get("TotalCapacity", 1)
        percentage = (count / capacity * 100) if capacity > 0 else 0
        
        # Store in database
        insert_reading(
            timestamp=now,
            location_id=location_id,
            location_name=location_name,
            facility_id=facility_id,
            facility_name=facility_name,
            count=count,
            capacity=capacity,
            percentage=round(percentage, 1)
        )
        
        collected_count += 1
        logger.info(f"  {facility_name} {location_name}: {count}/{capacity} ({percentage:.1f}%)")
    
    if collected_count > 0:
        logger.info(f"Collected {collected_count} zone readings")
    else:
        logger.info("All gyms currently closed - no data collected")


def run_collector():
    """
    Main collector loop that runs continuously.
    """
    logger.info("=" * 50)
    logger.info("UCLA Gym Activity Tracker - Starting")
    logger.info("=" * 50)
    
    # Initialize database
    init_database()
    
    last_hour = None
    
    while True:
        now = datetime.now()
        
        # Check if we need to aggregate previous hour
        current_hour = now.hour
        if last_hour is not None and current_hour != last_hour:
            # Calculate averages for the previous hour
            prev_hour_time = now - timedelta(hours=1)
            logger.info(f"Calculating hourly averages for {prev_hour_time.strftime('%Y-%m-%d %H:00')}")
            calculate_hourly_average(prev_hour_time.date(), last_hour)
        
        last_hour = current_hour
        
        # Collect data
        logger.info(f"Collecting data at {now.strftime('%Y-%m-%d %H:%M:%S')}")
        collect_data()
        
        # Wait for next collection interval
        # Calculate seconds until next 15-minute mark
        minutes_until_next = COLLECTION_INTERVAL - (now.minute % COLLECTION_INTERVAL)
        if minutes_until_next == COLLECTION_INTERVAL:
            minutes_until_next = 0
        seconds_until_next = minutes_until_next * 60 - now.second
        
        if seconds_until_next <= 0:
            seconds_until_next = COLLECTION_INTERVAL * 60
        
        logger.info(f"Next collection in {seconds_until_next // 60} minutes")
        time.sleep(seconds_until_next)


if __name__ == "__main__":
    try:
        run_collector()
    except KeyboardInterrupt:
        logger.info("Collector stopped by user")
    except Exception as e:
        logger.exception(f"Collector crashed: {e}")
        raise
