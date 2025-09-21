"""
Logica para servir las estadisticas por area. Mas relacionado a la logica de negocio
"""


from django.db import models;
from django.core.cache import cache;
from django.db.models import Count, Sum, Q;
from .models import Employee, Department;

class DepartmentStatsService:
    """Service para calculos relacionados con estadisticas de departamentos"""

    @staticmethod
    def get_overview():
        """Obtiene overview completo de departamentos con metricas"""
        
        # Manejo de cache para optimizacion
        cache_key = 'department_stats_overview'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result
        

        dept_stats = Department.objects.select_related(
            'department_manager__user'
        ).annotate(
            employee_count=Count(
                'role__employee',
                filter=Q(role__employee__termination_date__isnull=True)
            ),
            total_budget=models.F('budget'),
            total_salaries=Sum(
                'role__employee__current_salary',
                filter=Q(role__employee__termination_date__isnull=True)
            ),
            avg_salaries=models.Avg(
                'role__employee__current_salary',
                filter=Q(role__employee__termination_date__isnull=True)
            ),
        ).values(
            'name',
            'employee_count',
            'total_budget',
            'total_salaries',
            'avg_salaries',
            'department_manager__user__first_name',
            'department_manager__user__last_name'
        )


        dept_list = list(dept_stats)

        for dept in dept_list:
            if dept['total_budget'] and dept['total_salaries']:
                # Porcentaje del budget utilizado en sueldos
                dept['salary_budget_percentage'] = (dept['total_salaries'] / dept['total_budget']) * 100

                # Budget restante luego de sueldos
                dept['remaining_budget'] = dept['total_budget'] - dept['total_salaries']
            else:
                dept['salary_budget_percentage'] = None
                dept['remaining_budget'] = None

        # Cache por 10 minutos.
        cache.set(cache_key, dept_list, 600)
        return dept_list
    


class CompanyStatsService:
    """Service para estadisticas generales de la empresa"""

    @staticmethod
    def get_overview():
        """Estadisticas generales de la empresa"""

        cache_key = 'company_stats_overview'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result
        

        active_employee = Employee.objects.filter(
            termination_date__isnull=True
        ).values('seniority_level').annotate(
            count=Count('id')
        )

        # Convertir a dict para template
        seniority_breakdown = {
            'JUNIOR': 0,
            'MID': 0,
            'SENIOR': 0
        }

        total_employee = 0
        for stat in active_employee:
            seniority_breakdown[stat['seniority_level']] = stat['count']
            total_employee += stat['count']

        result = {
            'total_employee': total_employee,
            'seniority_breakdown': seniority_breakdown,
        }

        # cache por 5 minutos
        cache.set(cache_key, result, 300)
        return result
    

from core.utils import get_recent_date_threshold;
from core.constants import RECENT_ACTIVITY_DAYS;

class HRActivityService:
    """Service para actividad reciente de HR"""

    @staticmethod
    def get_recent_hires(days=None):
        """Contrataciones recientes"""
        if days is None:
            days = RECENT_ACTIVITY_DAYS

        cache_key = f'recent_hires_{days}'
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            return cached_result

        recent_threshold = get_recent_date_threshold(days)
        recent_hires = Employee.objects.filter(
            hire_date__gte=recent_threshold
        ).select_related('user', 'role__department').order_by('-hire_date')

        result = {
            'recent_hires': recent_hires,
            'recent_hires_count': recent_hires.count(),
        }

        # Cache por 30 minutos
        cache.set(cache_key, result, 1800)
        return result