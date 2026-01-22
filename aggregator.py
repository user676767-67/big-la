"""
UCLA Gym Activity Tracker - Data Aggregator

Calculates hourly averages and exports data to CSV.
"""

import csv
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from config import TRACKED_ZONES, FACILITY_NAMES
from database import (
    get_connection, insert_hourly_average, get_hourly_averages, init_database
)

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "exports"


def calculate_hourly_average(target_date: date, hour: int):
    """
    Calculate and store hourly averages for all zones for a specific hour.
    
    Args:
        target_date: The date to calculate averages for
        hour: The hour (0-23) to calculate averages for
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    for location_id, location_name in TRACKED_ZONES.items():
        # Get all readings for this hour and location
        cursor.execute("""
            SELECT facility_id, facility_name, percentage 
            FROM readings 
            WHERE date(timestamp) = ? 
            AND CAST(strftime('%H', timestamp) AS INTEGER) = ?
            AND location_id = ?
        """, (target_date.isoformat(), hour, location_id))
        
        rows = cursor.fetchall()
        
        if not rows:
            continue
        
        # Calculate average
        percentages = [row["percentage"] for row in rows]
        avg_percentage = sum(percentages) / len(percentages)
        sample_count = len(percentages)
        
        facility_id = rows[0]["facility_id"]
        facility_name = FACILITY_NAMES.get(facility_id, rows[0]["facility_name"])
        
        # Store the average
        insert_hourly_average(
            target_date=target_date,
            hour=hour,
            day_of_week=target_date.weekday(),
            location_id=location_id,
            location_name=location_name,
            facility_name=facility_name,
            avg_percentage=round(avg_percentage, 1),
            sample_count=sample_count
        )
        
        logger.info(f"  {hour:02d}:00 {facility_name} {location_name}: {avg_percentage:.1f}% (n={sample_count})")
    
    conn.close()


def calculate_all_pending_averages():
    """
    Calculate hourly averages for all readings that haven't been aggregated yet.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Find all distinct date-hour combinations in readings
    cursor.execute("""
        SELECT DISTINCT date(timestamp) as date, CAST(strftime('%H', timestamp) AS INTEGER) as hour
        FROM readings
        ORDER BY date, hour
    """)
    
    date_hours = cursor.fetchall()
    conn.close()
    
    for row in date_hours:
        target_date = date.fromisoformat(row["date"])
        hour = row["hour"]
        
        # Skip current hour (still collecting data)
        now = datetime.now()
        if target_date == now.date() and hour == now.hour:
            continue
        
        logger.info(f"Processing {target_date} {hour:02d}:00")
        calculate_hourly_average(target_date, hour)


def export_hourly_averages_to_csv(
    output_path: Optional[Path] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> Path:
    """
    Export hourly averages to a CSV file.
    
    Args:
        output_path: Path for the output file (auto-generated if None)
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        Path to the created CSV file
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"hourly_averages_{timestamp}.csv"
    
    averages = get_hourly_averages(start_date, end_date)
    
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        
        # Write header
        writer.writerow([
            "Date", "Day", "Hour", "Facility", "Zone", "Avg %", "Samples"
        ])
        
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        for row in averages:
            hour_str = f"{row['hour']:02d}:00"
            day_name = day_names[row["day_of_week"]]
            
            writer.writerow([
                row["date"],
                day_name,
                hour_str,
                row["facility_name"],
                row["location_name"],
                f"{row['avg_percentage']:.0f}%",
                row["sample_count"]
            ])
    
    logger.info(f"Exported {len(averages)} records to {output_path}")
    return output_path


def export_summary_by_day_and_hour(output_path: Optional[Path] = None) -> Path:
    """
    Export a summary showing average occupancy by day of week and hour.
    Format: 8:00AM BFIT Selectorized Zone: 32%
    
    Args:
        output_path: Path for the output file
    
    Returns:
        Path to the created CSV file
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = OUTPUT_DIR / f"weekly_summary_{timestamp}.csv"
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get average by day of week and hour
    cursor.execute("""
        SELECT 
            day_of_week,
            hour,
            facility_name,
            location_name,
            ROUND(AVG(avg_percentage), 1) as overall_avg,
            COUNT(*) as num_days
        FROM hourly_averages
        GROUP BY day_of_week, hour, facility_name, location_name
        ORDER BY day_of_week, hour, facility_name, location_name
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Day", "Hour", "Facility", "Zone", "Avg %", "Days Sampled"])
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for row in rows:
            hour = row["hour"]
            am_pm = "AM" if hour < 12 else "PM"
            display_hour = hour if hour <= 12 else hour - 12
            if display_hour == 0:
                display_hour = 12
            hour_str = f"{display_hour}:00{am_pm}"
            
            writer.writerow([
                day_names[row["day_of_week"]],
                hour_str,
                row["facility_name"],
                row["location_name"],
                f"{row['overall_avg']:.0f}%",
                row["num_days"]
            ])
    
    logger.info(f"Exported weekly summary to {output_path}")
    return output_path


def print_current_status():
    """Print a summary of stored data to the console."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Count readings
    cursor.execute("SELECT COUNT(*) as count FROM readings")
    readings_count = cursor.fetchone()["count"]
    
    # Count hourly averages
    cursor.execute("SELECT COUNT(*) as count FROM hourly_averages")
    averages_count = cursor.fetchone()["count"]
    
    # Get date range
    cursor.execute("SELECT MIN(date(timestamp)) as min_date, MAX(date(timestamp)) as max_date FROM readings")
    date_range = cursor.fetchone()
    
    conn.close()
    
    print("\n" + "=" * 50)
    print("UCLA Gym Activity Tracker - Status")
    print("=" * 50)
    print(f"Total readings: {readings_count}")
    print(f"Hourly averages: {averages_count}")
    if date_range["min_date"]:
        print(f"Date range: {date_range['min_date']} to {date_range['max_date']}")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    import argparse
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="UCLA Gym Data Aggregator")
    parser.add_argument("--aggregate", action="store_true", help="Calculate all pending hourly averages")
    parser.add_argument("--export", action="store_true", help="Export hourly averages to CSV")
    parser.add_argument("--summary", action="store_true", help="Export weekly summary by day and hour")
    parser.add_argument("--status", action="store_true", help="Print current data status")
    
    args = parser.parse_args()
    
    init_database()
    
    if args.status:
        print_current_status()
    
    if args.aggregate:
        logger.info("Calculating pending hourly averages...")
        calculate_all_pending_averages()
    
    if args.export:
        path = export_hourly_averages_to_csv()
        print(f"Exported to: {path}")
    
    if args.summary:
        path = export_summary_by_day_and_hour()
        print(f"Exported to: {path}")
    
    if not any([args.aggregate, args.export, args.summary, args.status]):
        parser.print_help()
