from django.shortcuts import render, redirect;
from django.contrib.auth.decorators import login_required;
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
    except Employee.DoesNotExist:
        # User existe pero no es empleado (ej: superuser)
        if request.user.is_superuser:
            return redirect('dashboards:admin_dashboard')
        messages.error(request, 'No employee profile found')
        return redirect('login')
    
    #Logica hibrida: Groups + Employee data
    user_groups = request.user.groups.values_list('name', flat=True)

    #1. Admin tiene prioridad maxima
    if 'Admin' in user_groups or request.user.is_superuser:
        return redirect('dashboards:admin_dashboard')
    
    #2. HR tiene segunda prioridad
    if 'HR' in user_groups:
        return redirect('dashboards:hr_dashboard')
    
    #3. Team Lead (derivado de datos)
    elif employee.is_team_lead:
        return redirect('dashboards:team_lead_dashboard')
    
    #4. Empleado regular
    else:
        return redirect('dashboards:employee_dashboard')
    

# Stubs para las vistas especificas
@login_required
def employee_dashboard(request):
    return render(request, 'dashboards/employee_dashboard.html')

@login_required
def team_lead_dashboard(request):
    return render(request, 'dashboards/team_lead_dashboard.html')

@login_required
def hr_dashboard(request):
    return render(request, 'dashboards/hr_dashboard.html')

@login_required
def admin_dashboard(request):
    return render(request, 'dashboards/admin_dashboard.html')