"""
Services especificos para dashboards.
"""

from datetime import date, timedelta;
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
        return {
            'total_users': User.objects.count(),
            'total_employees': Employee.objects.filter(termination_date__isnull=True).count(),
            'total_departments': Department.objects.count(),
        }
    
    @staticmethod
    def get_users_without_profile():
        """Usuarios sin Employee profile asociado"""
        return User.objects.filter(
            employee__isnull=True
        ).select_related().order_by('-date_joined')
    
    @staticmethod
    def get_group_distribution():
        """Distribucion de usuarios por grupo"""
        return Group.objects.annotate(
            user_count=Count('user')
        ).values('name', 'user_count')
    
    @staticmethod
    def get_recent_users(limit=None):
        """Usuarios creados recientemente"""
        if limit is None:
            limit = DEFAULT_RECENT_ITEMS_LIMIT
        
        recent_threshold = get_recent_date_threshold()
        return User.objects.filter(
            date_joined__gte=recent_threshold
        ).select_related('employee').order_by('-date_joined')[:limit]
    
    
class EmployeeDashboardService:
    """Service para logica especifica de employee dashboard"""

    @staticmethod
    def get_employee_by_user(user):
        """Obtiene empleado por usuario con manejo de errores"""
        try:
            return Employee.objects.select_related(
                'role__department', 'manager__user'
            ).get(user=user)
        except Employee.DoesNotExist:
            return None
        
    @staticmethod
    def get_team_members(employee):
        """Obtener miembros del equipo si es team lead"""
        if not employee or not employee.is_team_lead:
            return Employee.objects.none()
        
        return Employee.objects.filter(
            manager=employee
        ).select_related('role__department', 'user')

    @staticmethod
    def get_team_stats(team_members):
        """Estadisticas del equipo"""
        total_members = len(team_members)
        return {
            'total_members': total_members,
            'junior_count': len([m for m in team_members if m.seniority_level == 'JUNIOR']),
            'mid_count': len([m for m in team_members if m.seniority_level == 'MID']),
            'senior_count': len([m for m in team_members if m.seniority_level == 'SENIOR']),
        }
    
    @staticmethod
    def get_team_by_department(team_members):
        """Agrupa team members por departamento"""
        team_by_department = {}
        for member in team_members:
            dept_name = member.role.department.name
            if dept_name not in team_by_department:
                team_by_department[dept_name] = []
            team_by_department[dept_name].append(member)
        return team_by_department