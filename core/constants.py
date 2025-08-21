"""
Constantes globales del proyecto
"""

# paginacion y limites de consulta
DEFAULT_RECENT_ITEMS_LIMIT = 10
DASHBOARD_RECENT_USERS_LIMIT = 5
RECENT_ACTIVITY_DAYS = 30

# Estados y niveles
SENIORITY_LEVELS = [
    ('JUNIOR', 'Junior'),
    ('MID', 'Mid'),
    ('SENIOR', 'Senior'),
]

# Umbrales para alertas de presupuesto
BUDGET_WARNING_THRESHOLD = 60 # %
BUDGET_DANGER_THRESHOLD = 80 # %

# Grupos de usuarios
USER_GROUPS = {
    'ADMIN': 'Admin',
    'HR': 'HR',
    'EMPLOYEE': 'Employee'
}