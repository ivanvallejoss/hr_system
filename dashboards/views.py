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
            ).select_related('role_id', 'role_id__department_id')
        
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





@login_required
def team_lead_dashboard(request):
    return render(request, 'dashboards/team_lead_dashboard.html')

@login_required
def hr_dashboard(request):
    return render(request, 'dashboards/hr_dashboard.html')

@login_required
def admin_dashboard(request):
    return render(request, 'dashboards/admin_dashboard.html')