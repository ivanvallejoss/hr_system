from django.db import models;
from django.shortcuts import get_object_or_404;
from employee.models import Employee, Department;

class EmployeeContextMixin:
    """Mixin para agregar contexto relacionado con empleados"""
    
    def get_employee(self):
        # Obtenemos el empleado
        return get_object_or_404(Employee, user=self.request.user)
    
    def get_team_members(self, employee):
        """Obtener los miembros del equipo si es team lead"""
        if not employee.is_team_lead:
            return Employee.objects.none()
        return Employee.objects.filter(
            manager=employee
        ).select_related('role_id__department_id')
    
    def get_employment_duration(self, employee):
        """Calcula el tiempo que lleva el empleado en la empresa"""
        from datetime import date;
        days_employed = (date.today() - employee.hire_date).days
        return{
            'days_employed': days_employed,
            'years_employed': days_employed // 365,
            'months_employed': days_employed // 30,
        }
    
    def get_employee_context(self):
        """Metodo convenience que combina todo?"""
        employee = self.get_employee()
        if employee:
            return {
                'employee': employee,
                'team_members': self.get_team_members(employee),
                'is_team_lead': employee.is_team_lead,
                **self.get_employment_duration(employee)
            }
        
class HRContextMixin:
    """Mixin que agrega contexto especifico para HR Dashboard"""

    def get_company_stats(self):
        """Estadisticas generales de la empresa"""
        from django.db.models import Count, Sum;

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
    
    def get_department_stats(self):
        """Estadisticas por departamento"""
        from django.db.models import Count, Sum;

        dept_stats = Department.objects.annotate(
            employee_count=Count('role__employee', filter=models.Q(role__employee__termination_date__isnull=True)),
            total_budget = models.F('budget')
        ).values('name', 'employee_count', 'total_budget', 'department_manager__user__first_name', 'department_manager__user__last_name')

        return list(dept_stats)
    
    def get_recent_activity(self):
        """Actividad reciente (ultimos 30 dias)"""
        from datetime import date, timedelta;

        a_month_ago = date.today() - timedelta(days=30)

        recent_hires = Employee.objects.filter(
            hire_date__gte = a_month_ago
        ).select_related('user', 'role_id__department_id').order_by('-hire_date')

        return {
            'recent_hires': recent_hires,
            'recent_hires_count': recent_hires.count(),
        }
    
    def get_hr_context(self):
        """Metodo convenience que combina todo el contexto HR"""
        context = {}
        context.update(self.get_company_stats())
        context.update({
            'department_stats': self.get_department_stats(),
            'recent_hires':self.get_recent_activity(),
            **self.get_recent_activity()
        })
        return context