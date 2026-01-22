"""
UCLA Gym Activity Tracker - Configuration
"""

API_URL = "https://goboardapi.azurewebsites.net/api/FacilityCount/GetCountsByAccount?AccountAPIKey=73829a91-48cb-4b7b-bd0b-8cf4134c04cd"

# Collection interval in minutes
COLLECTION_INTERVAL = 15

# Facility IDs
JOHN_WOODEN_ID = 802
BFIT_ID = 803

# Tracked zones by LocationId
TRACKED_ZONES = {
    # John Wooden Center
    3903: "Free Weight Zone",
    4339: "Advanced Circuit Zone", 
    3902: "Novice Circuit Zone",
    # Bruin Fitness Center
    4009: "Free Weight & Squat Zones",
    4010: "Cable, Synergy Zones",
    4011: "Selectorized Zone",
}

# Operating hours: (open_hour, open_minute, close_hour, close_minute)
# Note: close times after midnight use 24+ hour format (e.g., 25 = 1:00 AM next day)
OPERATING_HOURS = {
    # John Wooden Center
    JOHN_WOODEN_ID: {
        # Monday = 0, Tuesday = 1, ..., Friday = 4
        "weekday": (5, 15, 25, 0),   # 5:15 AM - 1:00 AM (Mon-Thu)
        "friday": (5, 15, 22, 0),    # 5:15 AM - 10:00 PM (Fri)
    },
    # Bruin Fitness Center
    BFIT_ID: {
        "weekday": (6, 0, 24, 0),    # 6:00 AM - 12:00 AM (Mon-Thu)
        "friday": (6, 0, 21, 0),     # 6:00 AM - 9:00 PM (Fri)
    },
}

# Facility name shortcuts for display
FACILITY_NAMES = {
    JOHN_WOODEN_ID: "JWC",
    BFIT_ID: "BFIT",
}
