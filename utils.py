"""Utility functions for the drone operations coordinator."""
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Tuple


def parse_date(date_str: str) -> datetime:
    """Parse date string to datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def dates_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Check if two date ranges overlap."""
    d1_start = parse_date(start1)
    d1_end = parse_date(end1)
    d2_start = parse_date(start2)
    d2_end = parse_date(end2)
    
    if not all([d1_start, d1_end, d2_start, d2_end]):
        return False
    
    return d1_start <= d2_end and d2_start <= d1_end


def calculate_mission_duration(start_date: str, end_date: str) -> int:
    """Calculate mission duration in days."""
    start = parse_date(start_date)
    end = parse_date(end_date)
    
    if not start or not end:
        return 0
    
    return (end - start).days + 1


def calculate_pilot_cost(daily_rate: float, start_date: str, end_date: str) -> float:
    """Calculate total cost for a pilot based on mission duration."""
    duration = calculate_mission_duration(start_date, end_date)
    return daily_rate * duration


def parse_skills(skills_str: str) -> List[str]:
    """Parse skills string into list."""
    if pd.isna(skills_str) or not skills_str:
        return []
    return [s.strip() for s in str(skills_str).split(",")]


def parse_certifications(certs_str: str) -> List[str]:
    """Parse certifications string into list."""
    if pd.isna(certs_str) or not certs_str:
        return []
    return [c.strip() for c in str(certs_str).split(",")]


def skills_match(pilot_skills: str, required_skills: str) -> bool:
    """Check if pilot has required skills."""
    pilot_skill_list = parse_skills(pilot_skills)
    required_skill_list = parse_skills(required_skills)
    
    return all(skill in pilot_skill_list for skill in required_skill_list)


def certifications_match(pilot_certs: str, required_certs: str) -> bool:
    """Check if pilot has required certifications."""
    pilot_cert_list = parse_certifications(pilot_certs)
    required_cert_list = parse_certifications(required_certs)
    
    return all(cert in pilot_cert_list for cert in required_cert_list)


def is_weather_compatible(drone_weather_resistance: str, mission_weather: str) -> bool:
    """Check if drone is compatible with mission weather."""
    if pd.isna(drone_weather_resistance) or not drone_weather_resistance:
        return mission_weather.lower() in ["sunny", "cloudy"]
    
    weather_resistance = str(drone_weather_resistance).lower()
    mission_weather_lower = mission_weather.lower()
    
    # IP43 or higher can handle rain
    if "ip43" in weather_resistance or "rain" in weather_resistance:
        return True
    
    # No weather resistance means clear sky only
    if "none" in weather_resistance or "clear sky only" in weather_resistance:
        return mission_weather_lower in ["sunny", "cloudy"]
    
    return True


def is_maintenance_due(maintenance_due: str) -> bool:
    """Check if maintenance is due (before or on today's date)."""
    if pd.isna(maintenance_due) or not maintenance_due:
        return False
    
    maintenance_date = parse_date(maintenance_due)
    if not maintenance_date:
        return False
    
    return maintenance_date <= datetime.now()
