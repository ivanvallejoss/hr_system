"""
Logica para servir en la vista de los dashboards.
"""

from django.core.cache import cache;
from django.contrib.auth.models import User, Group;
from django.db.models import Count;
from employee.models import Employee, Department;
from core.utils import get_recent_date_threshold;
from core.constants import (
    DASHBOARD_RECENT_USERS_LIMIT,
    DEFAULT_RECENT_ITEMS_LIMIT,
    RECENT_ACTIVITY_DAYS
);

class UserManagementService:
    """Service para gestion de usuarios en dashboard admin"""

    @staticmethod
    def get_system_overview():
        """Obtiene estadisticas generales del sistema"""
        cache_key = 'system_overview'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        result = {
            'total_users': User.objects.count(),
            'total_employees': Employee.objects.filter(termination_date__isnull=True).count(),
            'total_departments': Department.objects.count(),
        }

        cache.set(cache_key, result, 300)
        return result
    
    @staticmethod
    def get_users_without_profile():
        """Usuarios sin Employee profile asociado"""
        cache_key = 'users_without_profile'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result
        
        users = User.objects.filter(
            employee__isnull=True
        ).select_related().order_by('-date_joined')

        cache.set(cache_key, list(users), 600)
        return list(users)
    
    @staticmethod
    def get_group_distribution():
        """Distribucion de usuarios por grupo"""
        cache_key = 'group_distribution'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        groups = Group.objects.annotate(
            user_count=Count('user')
        ).values('name', 'user_count')

        cache.set(cache_key, list(groups), 900)
        return groups


    @staticmethod
    def get_recent_users(limit=None):
        """Usuarios creados recientemente"""
        if limit is None:
            limit = DEFAULT_RECENT_ITEMS_LIMIT
        
        cache_key = f'recent_users_{limit}'
        cached_result = cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        recent_threshold = get_recent_date_threshold()
        users = User.objects.filter(
            date_joined__gte=recent_threshold
        ).select_related('employee').order_by('-date_joined')[:limit]
        
        cache.set(cache_key, list(users), 600)
        return list(users)
    
class EmployeeDashboardService:
    """Service para logica especifica de employee dashboard"""

    @staticmethod
    def get_employee_by_user(user):
        """Obtiene empleado por usuario con manejo de errores"""
        cache_key = f'employee_data_{user.id}'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result
        
        try:
            employee = Employee.objects.select_related(
                'role__department', 'manager__user'
            ).prefetch_related(
                'team_members'
            ).get(user=user)

            cache.set(cache_key, employee, 900)
            return employee
        except Employee.DoesNotExist:
            return None
        
    @staticmethod
    def get_team_members(employee):
        """Obtener miembros del equipo si es team lead"""
        if not employee or not employee.is_team_lead:
            return []
        
        cache_key = f'team_members_{employee.id}'
        cached_result = cache.get(cache_key)

        if cached_result:
            return cached_result
        
        team_members_list = Employee.objects.filter(
            manager=employee
        ).select_related('role__department', 'user')

        cache.set(cache_key, len(team_members_list), 600)
        return list(team_members_list)

    @staticmethod
    def get_team_stats(team_members):
        """Estadisticas del equipo"""

        cache_key = 'team_stats'
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result

        total_members = len(team_members)

        seniorities = {
            'JUNIOR': 0,
            'MID': 0,
            'SENIOR': 0,
        }
        for m in team_members:
            seniorities[m.seniority_level] += 1

        team_stats = {
            'total_members': total_members,
            'junior_count': seniorities['JUNIOR'],
            'mid_count': seniorities['MID'],
            'senior_count': seniorities['SENIOR'],
        }

        cache.set(cache_key, team_stats, 600)
        return team_stats
    
    @staticmethod
    def get_team_by_department(team_members):
        """Agrupa team members por departamento"""
        cache_key = 'team_by_department'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result
        
        team_by_department = {}
        for member in team_members:
            dept_name = member.role.department.name
            if dept_name not in team_by_department:
                team_by_department[dept_name] = []
            team_by_department[dept_name].append(member)
        
        cache.set(cache_key, team_by_department, 600)
        return team_by_department
    

import logging
from core.exceptions import EmployeeNotFoundError, InactiveEmployeeError, InsufficientPermissionError;

logger = logging.getLogger(__name__)

class ValidationService:
    """Service para validaciones de datos"""

    @staticmethod
    def validate_employee_access(user):
        """
        Valida que un usuario tenga acceso como empleado
        """
        if not user.is_authenticated:
            raise PermissionError("User not authenticated") # No estoy muy seguro de esta linea, en teoria deberia ser PermissionDenied ??
        
        try:
            employee = user.employee
            if not employee.is_active:
                raise InactiveEmployeeError(f"Employee {user.username} is not active")
            return employee
        except Employee.DoesNotExist:
            raise EmployeeNotFoundError(f"No employee profle for user {user.username}")
        
    @staticmethod
    def validate_team_lead_access(user):
        """
        Valida que un usuario tenga acceso como team lead
        """
        employee = ValidationService.validate_employee_access(user)
        if not employee.is_team_lead:
            raise InsufficientPermissionError(f"User {user.username} is not a team lead")
        return employee
    
    @staticmethod
    def validate_group_membership(user, required_groups):
        """
        Valida que un usuario pertenezca a los grupos requeridos
        """

        if user.is_superuser:
            return True
        
        user_groups = set(user.groups.values_list('name', flat=True))
        required_groups = set(required_groups)

        if not user_groups.intersection(required_groups):
            raise InsufficientPermissionError(
                f"User {user.username} lacks required groups: {required_groups}"
            )
        return True
    
#
#   ROUTING
# Service que sirve al acceso a Dashboards.
# 

class DashboardRouter:
    """Servicio para determinar el dashboard apropiado segun rol."""

    DASHBOARD_ROUTING = {
        'Admin': 'dashboards:admin_dashboard',
        'HR': 'dashboards:hr_dashboard',
        'Team Lead': 'dashboards:team_lead_dashboard',
    }

    @classmethod
    def get_dashboard_url(cls, user, employee=None):
        """
        Determina la URL del dashboard apropiado

        Args:
            user: Django User object
            employee: Employee objects (opcional)
        
        Returns:
            str: URL name del dashboard
        """
        user_groups = user.groups.values_list('name', flat=True)

        # Verificar cada condicion en orden de prioridad.
        if user.is_superuser:
            return 'dashboards:admin_dashboard'
        
        for group_name in user_groups:
            if group_name in cls.DASHBOARD_ROUTING:
                return cls.DASHBOARD_ROUTING[group_name]
            
        if employee.is_team_lead:       # Mantenemos esta condicion hasta generar la logica para grupo de team lead
            return 'dashboards:team_lead_dashboard' 
        
        return 'dashboards:employee_dashboard'
    
    @classmethod
    def add_group_mapping(cls, group, group_dashboard):
        """
        Metodo para agregar grupos y rutas al diccionario de routing

        Args:
            group: nombre del grupo a agregar.
            group_dashboard: dashboard al que va a apuntar el grupo

        Returns:
            No retorna ningun valor.
        """
        # Verificamos que el grupo no existe
        if group in cls.DASHBOARD_ROUTING:
            return None
        
        # Verificamos que el dashboard no existe
        if group_dashboard in cls.DASHBOARD_ROUTING.values():
            return None

        cls.DASHBOARD_ROUTING[group] = group_dashboard