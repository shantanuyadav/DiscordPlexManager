# Helper functions for date calculations (e.g., end date)
from datetime import datetime, timedelta

def calculate_end_date(start_date, duration):
    # Convert duration string to days
    duration_map = {
        '2_days': 2,
        '1_month': 30,
        '3_months': 90,
        '6_months': 180,
        '12_months': 365
    }
    
    days = duration_map.get(duration)
    if days is None:
        raise ValueError(f"Invalid duration format: {duration}")
        
    return start_date + timedelta(days=days)