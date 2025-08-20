from django.shortcuts import redirect;
from django.contrib.auth.decorators import login_required;
from django.contrib.auth.mixins import LoginRequiredMixin;
from django.views.generic import TemplateView;
from django.contrib import messages;
from django.contrib.auth.models import User, Group;
from employee.models import Department, Employee;
from .mixins import EmployeeContextMixin, HRContextMixin;


#
#   PAGINA DE INICIO / REDIRECCION
#

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


#
#   EMPLEADO / TEAM-lEAD
#

class EmployeeDashboardView(LoginRequiredMixin, EmployeeContextMixin, TemplateView):
    """Dashboard para empleados regulares"""
    template_name = 'dashboards/employee_dashboard.html'

    # Agregamos el contexto del Mixin a la vista del empleado regular
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_employee_context())
        return context


class TeamLeadDashboardView(EmployeeDashboardView):
    """Dashboard para Team Leads - hereda de EmployeeDashboardView"""
    template_name = 'dashboards/team_lead_dashboard.html'

    def get_context_data(self, **kwargs):
        #Obtener todo el contexto de Employee Dashboard
        context = super().get_context_data(**kwargs)

        # Logica especifica del Team Lead
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
        department = employee.role.department

        # Team members por departmamento (en caso de team lead cross-department)
        team_by_department = {}
        for member in team_members:
            dept_name = member.role.department
            if dept_name not in team_by_department:
                team_by_department[dept_name] = []
            team_by_department[dept_name].append(member)

        # Enviar contexto con info de Team Lead
        context.update({
            'team_stats': team_stats,
            'department': department,
            'team_by_department': team_by_department,
            'is_cross_department_lead': len(team_by_department) > 1,
        })

        return context

#
#   HR DEPARTMENT
#

class HRDashboardView(LoginRequiredMixin, HRContextMixin, TemplateView):
    """Dashboard para usuarios de HR"""
    template_name = 'dashboards/hr_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Agregar contexto especifico de HR
        context.update(self.get_hr_context())
        # Info del usuario HR actual
        context.update({
            'hr_user': self.request.user,
        })

        return context


#
#   ADMIN
#

class AdminDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard para administradores del sistema"""
    template_name = 'dashboards/admin_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from employee.services import CompanyStatsService;

        # System Overview Stats
        total_users = User.objects.count()
        total_employees = Employee.objects.filter(termination_date__isnull=True).count()
        total_departments = Department.objects.count()

        # User Management Stats
        users_without_profile = self.get_users_without_profile()
        group_distribution = self.get_group_distribution()
        recent_users = self.get_recent_users()

        # Company stats from service
        company_stats = CompanyStatsService.get_overview()

        context.update({
            # System overview
            'total_users': total_users,
            'total_employees': total_employees,
            'total_departments': total_departments,
            'users_without_profile_count': users_without_profile.count(),

            # User Management
            'users_without_profile': users_without_profile[:5], # No entiendo porque pero top 5 para mostrar
            'group_distribution': group_distribution,
            'recent_users': recent_users,

            # Company data
            **company_stats,

            # Admin user info
            'admin_user': self.request.user,
        })

        return context
    
    def get_users_without_profile(self):
        """Usuarios sin Employee profile asociado"""
        return User.objects.filter(employee__isnull=True).select_related().order_by('-date_joined')
    
    def get_group_distribution(self):
        """Distribucion de usuarios sin grupo"""
        from django.db.models import Count;
        return Group.objects.annotate(user_count=Count('user')).values('name', 'user_count')
    
    def get_recent_users(self):
        """Usuarios creados en los ultimos 30 dias"""
        from datetime import date, timedelta;  
        a_month_ago = date.today() - timedelta(days=30)
        return User.objects.filter(date_joined__gte=a_month_ago).order_by('-date_joined')[:10]