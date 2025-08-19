from django.db import models;
from django.db.models import Count, Sum, Avg;
from .models import Employee, Department, Role;

class DepartmentStatsService:
    """Service para calculos relacionados con estadisticas de departamentos"""

    @staticmethod
    def get_overview():
        """Obtiene overview completo de departamentos con metricas"""

        dept_stats = Department.objects.annotate(
            employee_count=Count('role__employee', filter=models.Q(role__employee__termination_date__isnull=True)),
            total_budget = models.F('budget'),
            total_salaries = Sum('role__employee__current_salary', filter=models.Q(role__employee__termination_date__isnull=True)),
            avg_salaries = Sum('role__employee__current_salary', filter=models.Q(role__employee__termination_date__isnull=True)),
        ).values('name', 'employee_count', 'total_budget', 'total_salaries', 'avg_salaries', 'department_manager__user__first_name', 'department_manager__user__last_name')

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

        return dept_list
    
class CompanyStatsService:
    """Service para estadisticas generales de la empresa"""

    @staticmethod
    def get_overview():
        """Estadisticas generales de la empresa"""
        from django.db.models import Count;

        total_employee = Employee.objects.filter(termination_date__isnull=True).count()

        # Stats para seniority
        seniority_stats = Employee.objects.filter(
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
        for stat in seniority_stats:
            seniority_breakdown[stat['seniority_level']] = stat['count']

        return {
            'total_employee': total_employee,
            'seniority_breakdown': seniority_breakdown,
        }