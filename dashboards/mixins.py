from django.shortcuts import get_object_or_404;
from employee.models import Employee;

class EmployeeContextMixin:
    """Mixin para agregar contexto relacionado con empleados"""
    
    def get_employee(self):
        return get_object_or_404(Employee, user=self.request.user)
    
    def get_team_members(self, employee):
        """Obtener los miembros del equipo si es team lead"""
        if not employee.is_team_lead:
            return Employee.objects.none()
        return Employee.objects.filter(
            manager=employee
        ).select_related('role__department')
    
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
        
    def get_recent_activity(self):
        """Actividad reciente (ultimos 30 dias)"""
        from datetime import date, timedelta;

        a_month_ago = date.today() - timedelta(days=30)

        recent_hires = Employee.objects.filter(
            hire_date__gte = a_month_ago
        ).select_related('user', 'role__department').order_by('-hire_date')

        return {
            'recent_hires': recent_hires,
            'recent_hires_count': recent_hires.count(),
        }
    
    def get_hr_context(self):
        """Metodo convenience que combina todo el contexto HR"""
        from employee.services import DepartmentStatsService, CompanyStatsService;

        context = {}

        # Obtenemos estadisticas: department_stats - recent_hires/recent_hires_count - total_employee/seniority_breakdown. En ese orden.
        context.update({
            'department_stats': DepartmentStatsService.get_overview(),
            **self.get_recent_activity(),
            **CompanyStatsService.get_overview(),
        })
        return context