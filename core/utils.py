"""
Utilidades comunes para fecha/tiempo
"""

from datetime import date, timedelta;
from .constants import RECENT_ACTIVITY_DAYS;

def get_recent_date_threshold(days=None):
    """Obtiene fecha limite para actividad reciente"""
    if days is None:
        days = RECENT_ACTIVITY_DAYS
    return date.today() - timedelta(days=days)

def calculate_employment_duration(hire_date):
    """Calcula duracion del empleo"""
    days_employed = (date.today() - hire_date).days
    return {
        'days_employed': days_employed,
        'years_employed': days_employed // 365,
        'months_employed': days_employed // 30,
    }