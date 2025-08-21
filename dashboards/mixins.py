from core.utils import calculate_employment_duration;
from dashboards.services import EmployeeDashboardService;

class EmployeeContextMixin:
    """Mixin para agregar contexto relacionado con empleados"""
    
    def get_employee_context(self):
        """Metodo convenience que usa service"""
        employee = EmployeeDashboardService.get_employee_by_user(self.request.user)

        if not employee:
            return {'employee': None}
        
        team_members = EmployeeDashboardService.get_team_members(employee)

        context = {
            'employee': employee,
            'team_members': team_members,
            'is_team_lead': employee.is_team_lead,
            **calculate_employment_duration(employee.hire_date),
        }

        return context


class HRContextMixin:
    """Mixin que agrega contexto especifico para HR Dashboard"""
    
    def get_hr_context(self):
        """Metodo convenience que combina todo el contexto HR"""
        from employee.services import DepartmentStatsService, CompanyStatsService, HRActivityService;

        context = {}

        # Obtenemos estadisticas: department_stats - recent_hires/recent_hires_count - total_employee/seniority_breakdown. En ese orden.
        context.update({
            'department_stats': DepartmentStatsService.get_overview(),
            **HRActivityService.get_recent_hires(),
            **CompanyStatsService.get_overview(),
        })

        return context