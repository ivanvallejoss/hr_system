from django.shortcuts import render, redirect, get_object_or_404;
from django.contrib.auth.decorators import login_required;
from django.contrib.auth.mixins import LoginRequiredMixin;
from django.views.generic import TemplateView;
from django.contrib.auth.models import Group;
from django.contrib import messages;
from employee.models import Employee;

# Create your views here.

def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboards:dashboard_redirect')
    return redirect('login')

@login_required
def dashboard_redirect(request):
    try:
        employee = Employee.objects.get(user=request.user)

    # User existe pero no es empleado (ej: superuser)
    except Employee.DoesNotExist:
        if request.user.is_superuser:
            return redirect('dashboards:admin_dashboard')
        messages.error(request, 'No employee profile found')
        return redirect('login')
    
    #Logica hibrida: Groups + Employee data
    user_groups = request.user.groups.values_list('name', flat=True)

    if 'Admin' in user_groups or request.user.is_superuser:
        return redirect('dashboards:admin_dashboard')
    
    if 'HR' in user_groups:
        return redirect('dashboards:hr_dashboard')
    elif employee.is_team_lead:
        return redirect('dashboards:team_lead_dashboard')
    else:
        return redirect('dashboards:employee_dashboard')
    

# Stubs para las vistas especificas
class EmployeeDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard para empleados regulares"""
    template_name = 'dashboards/employee_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener employee asociado al user
        employee = get_object_or_404(Employee, user=self.request.user)

        # Obtener team members si es team lead (para casos hibridos)
        team_members = []
        if employee.is_team_lead:
            team_members = Employee.objects.filter(
                manager=employee
            ).select_related('role_id__department_id')
        
        # Calcular tiempo en la empresa
        from datetime import date
        days_employed = (date.today() - employee.hire_date).days
        years_employed = days_employed // 365

        context.update({
            'employee': employee,
            'team_members': team_members,
            'is_team_lead': employee.is_team_lead,
            'days_employed': days_employed,
            'years_employed': years_employed,
        })

        return context

class TeamLeadDashboardView(EmployeeDashboardView):
    """Dashboard para Team Leads - hereda de EmployeeDashboardView"""
    template_name = 'dashboards/team_lead_dashboard.html'

    def get_context_data(self, **kwargs):
        #Obtener todo el contexto de Employee Dashboard
        context = super().get_context_data(**kwargs)

        # Obtener las propiedades heredadas. 
        employee = context['employee']
        
        team_members = context['team_members']

        # Estadisticas del equipo
        team_stats = {
            'total_members': len(team_members),
            'junior_count': len([m for m in team_members if m.seniority_level == 'JUNIOR']),
            'mid_count': len([m for m in team_members if m.seniority_level == 'MID']),
            'senior_count': len([m for m in team_members if m.seniority_level == 'SENIOR']),
        }

        # Contexto del departamento.
        department = employee.role_id.department_id

        # Team members por departmamento (en caso de team lead cross-department)
        team_by_department = {}
        for member in team_members:
            dept_name = member.role_id.department_id
            if dept_name not in team_by_department:
                team_by_department[dept_name] = []
            team_by_department[dept_name].append(member)

        # Enviar contexto con info de Team Lead
        context.update({
            'team_stats': team_stats,
            'department': department,
            'team_by_department': team_by_department,
            'is_cross_deparment_lead': len(team_by_department) > 1,
        })

        return context



@login_required
def hr_dashboard(request):
    return render(request, 'dashboards/hr_dashboard.html')

@login_required
def admin_dashboard(request):
    return render(request, 'dashboards/admin_dashboard.html')