"""
UCLA Gym Activity Tracker - Single Collection Run
This version runs once and exits (for GitHub Actions / cron jobs)
"""

import requests
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configuration
API_URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount?AccountAPIKey=73829a91-48cb-4b7b-bd0b-8cf4134c04cd"

JOHN_WOODEN_ID = 802
BFIT_ID = 803

TRACKED_ZONES = {
    3903: "Free Weight Zone",
    4339: "Advanced Circuit Zone", 
    3902: "Novice Circuit Zone",
    4009: "Free Weight & Squat Zones",
    4010: "Cable, Synergy Zones",
    4011: "Selectorized Zone",
}

FACILITY_NAMES = {
    JOHN_WOODEN_ID: "JWC",
    BFIT_ID: "BFIT",
}

# Operating hours (24h format, close times after midnight use 24+)
OPERATING_HOURS = {
    JOHN_WOODEN_ID: {
        "weekday": (5, 15, 25, 0),   # 5:15 AM - 1:00 AM
        "friday": (5, 15, 22, 0),    # 5:15 AM - 10:00 PM
    },
    BFIT_ID: {
        "weekday": (6, 0, 24, 0),    # 6:00 AM - 12:00 AM
        "friday": (6, 0, 21, 0),     # 6:00 AM - 9:00 PM
    },
}

DB_PATH = Path("gym_data.db")


def init_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME NOT NULL,
            location_id INTEGER NOT NULL,
            location_name TEXT NOT NULL,
            facility_id INTEGER NOT NULL,
            facility_name TEXT NOT NULL,
            count INTEGER NOT NULL,
            capacity INTEGER NOT NULL,
            percentage REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def get_pacific_time():
    """Get current time in Pacific Time (approximated as UTC-8 for PST)"""
    # GitHub Actions runs in UTC
    utc_now = datetime.now(timezone.utc)
    # create a fixed offset for PST (UTC-8)
    # We could make this smarter for DST, but for now fixed offset is reliable enough
    # or rely on the Fact that in Jan it is PST.
    pacific_offset = timedelta(hours=-8) 
    return utc_now + pacific_offset


def is_gym_open(facility_id: int, check_time: datetime) -> bool:
    day_of_week = check_time.weekday()
    
    if day_of_week >= 5:  # Weekend
        return False
    
    hours = OPERATING_HOURS.get(facility_id)
    if not hours:
        return False
    
    schedule = hours["friday"] if day_of_week == 4 else hours["weekday"]
    open_hour, open_min, close_hour, close_min = schedule
    
    current_minutes = check_time.hour * 60 + check_time.minute
    open_minutes = open_hour * 60 + open_min
    close_minutes = close_hour * 60 + close_min
    
    if close_hour >= 24:
        if current_minutes >= open_minutes:
            return True
        close_minutes_adjusted = (close_hour - 24) * 60 + close_min
        if current_minutes < close_minutes_adjusted:
            return True
        return False
    
    return open_minutes <= current_minutes < close_minutes


def collect_data():
    # Force Pacific Time
    now = get_pacific_time()
    # Remove timezone info for sqlite compatibility and consistent logging
    now_naive = now.replace(tzinfo=None)
    
    print(f"Collection time (Pacific): {now_naive.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"API fetch failed: {e}")
        return
    
    init_database()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    collected = 0
    for zone in data:
        location_id = zone.get("LocationId")
        if location_id not in TRACKED_ZONES:
            continue
        
        facility_id = zone.get("FacilityId")
        
        # Check if gym is open using Pacific time
        if not is_gym_open(facility_id, now_naive):
            print(f"  Skipping {FACILITY_NAMES.get(facility_id)} (Closed at {now_naive.strftime('%H:%M')})")
            continue
        
        location_name = zone.get("LocationName", "Unknown")
        facility_name = FACILITY_NAMES.get(facility_id, "Unknown")
        count = zone.get("LastCount", 0)
        capacity = zone.get("TotalCapacity", 1)
        percentage = round((count / capacity * 100) if capacity > 0 else 0, 1)
        
        cursor.execute("""
            INSERT INTO readings 
            (timestamp, location_id, location_name, facility_id, facility_name, count, capacity, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (now_naive, location_id, location_name, facility_id, facility_name, count, capacity, percentage))
        
        print(f"  {facility_name} {location_name}: {count}/{capacity} ({percentage}%)")
        collected += 1
    
    conn.commit()
    conn.close()
    
    if collected > 0:
        print(f"✓ Collected {collected} readings")
    else:
        print("Gyms are closed - no data collected")


if __name__ == "__main__":
    collect_data()
