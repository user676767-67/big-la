"""
UCLA Gym Activity Tracker - Database Operations
"""

import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / "gym_data.db"


def get_connection() -> sqlite3.Connection:
    """Get a database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Raw readings table
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
    
    # Create index for faster queries
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_timestamp 
        ON readings(timestamp)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_readings_location 
        ON readings(location_id)
    """)
    
    # Hourly averages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hourly_averages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            hour INTEGER NOT NULL,
            day_of_week INTEGER NOT NULL,
            location_id INTEGER NOT NULL,
            location_name TEXT NOT NULL,
            facility_name TEXT NOT NULL,
            avg_percentage REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            UNIQUE(date, hour, location_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def insert_reading(
    timestamp: datetime,
    location_id: int,
    location_name: str,
    facility_id: int,
    facility_name: str,
    count: int,
    capacity: int,
    percentage: float
):
    """Insert a single reading into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO readings 
        (timestamp, location_id, location_name, facility_id, facility_name, count, capacity, percentage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, location_id, location_name, facility_id, facility_name, count, capacity, percentage))
    
    conn.commit()
    conn.close()


def get_readings_for_hour(target_date: date, hour: int, location_id: int) -> list:
    """Get all readings for a specific hour and location."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM readings 
        WHERE date(timestamp) = ? 
        AND strftime('%H', timestamp) = ?
        AND location_id = ?
    """, (target_date.isoformat(), f"{hour:02d}", location_id))
    
    rows = cursor.fetchall()
    conn.close()
    return rows


def insert_hourly_average(
    target_date: date,
    hour: int,
    day_of_week: int,
    location_id: int,
    location_name: str,
    facility_name: str,
    avg_percentage: float,
    sample_count: int
):
    """Insert or update hourly average."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT OR REPLACE INTO hourly_averages
        (date, hour, day_of_week, location_id, location_name, facility_name, avg_percentage, sample_count)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (target_date.isoformat(), hour, day_of_week, location_id, location_name, facility_name, avg_percentage, sample_count))
    
    conn.commit()
    conn.close()


def get_hourly_averages(start_date: Optional[date] = None, end_date: Optional[date] = None) -> list:
    """Get hourly averages, optionally filtered by date range."""
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM hourly_averages"
    params = []
    
    if start_date and end_date:
        query += " WHERE date BETWEEN ? AND ?"
        params = [start_date.isoformat(), end_date.isoformat()]
    elif start_date:
        query += " WHERE date >= ?"
        params = [start_date.isoformat()]
    elif end_date:
        query += " WHERE date <= ?"
        params = [end_date.isoformat()]
    
    query += " ORDER BY date, hour, facility_name, location_name"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    init_database()
