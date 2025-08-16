from django.shortcuts import get_object_or_404;
from employee.models import Employee;

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