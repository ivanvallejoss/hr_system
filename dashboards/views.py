from django.shortcuts import redirect;
from django.contrib.auth.decorators import login_required;
from django.views.generic import TemplateView;
from django.contrib import messages;
from django.contrib.auth.models import User, Group;
from employee.models import Employee;
from .mixins import EmployeeContextMixin, HRContextMixin;
from core.mixins import (
    EmployeeRequiredMixin,
    HRRequiredMixin,
    AdminRequiredMixin,
    TeamLeadRequiredMixin,
    SafeViewMixin
);
from core.decorator import safe_view;
import logging

logger = logging.getLogger(__name__)


#
#   PAGINA DE INICIO / REDIRECCION
#

@safe_view('login')
def home_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboards:dashboard_redirect')
    return redirect('login')

@login_required
@safe_view('login')
def dashboard_redirect(request):
    try:
        employee = Employee.objects.get(user=request.user)

    # User existe pero no es empleado (ej: superuser)
    except Employee.DoesNotExist:
        if request.user.is_superuser:
            logger.info(f"Superuser {request.user.username} accessing admin dashboard")
            return redirect('dashboards:admin_dashboard')
        logger.warning(f"User {request.user.username} has no employee profile.")
        messages.error(request, 'No employee profile found')
        return redirect('login')
    
    #Logica hibrida: Groups + Employee data
    user_groups = request.user.groups.values_list('name', flat=True)

    if 'Admin' in user_groups or request.user.is_superuser:
        logger.info(f"Admin {request.user.username} accessing admin dashboard")
        return redirect('dashboards:admin_dashboard')
    
    if 'HR' in user_groups:
        logger.info(f"HR user {request.user.username} accessing HR dashboard")
        return redirect('dashboards:hr_dashboard')
    
    elif employee.is_team_lead:
        logger.info(f"Team Lead {request.user.username} accessing team lead dashboard")
        return redirect('dashboards:team_lead_dashboard')
    else:
        logger.info(f"Employee {request.user.username} accessing employee dashboard")
        return redirect('dashboards:employee_dashboard')


#
#   EMPLEADO / TEAM-lEAD
#

class EmployeeDashboardView(SafeViewMixin, EmployeeRequiredMixin, EmployeeContextMixin, TemplateView):
    """Dashboard para empleados regulares"""
    template_name = 'dashboards/employee_dashboard.html'
    fallback_url = 'login'

    # Agregamos el contexto del Mixin a la vista del empleado regular
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            # Intentamos obtener el contexto especifico del empleado.
            employee_context = self.get_employee_context()
            if not employee_context.get('employee'):
                logger.error(f"No employee context for user {self.request.user.username}")
                messages.error(self.request, 'Coul not load employee information.')
                return context
            
            # Si lo obtenemos, lo cargamos al contexto.
            context.update(employee_context)

            # Datos para action buttons
            context['quick_actions']= [
                {
                    'label':'Update Profile',
                    'icon': 'fas fa-user-edit',
                    'disabled': True,
                    'col_size': '3'
                },
                {
                    'label': 'View Schedule',
                    'icon': 'fas fa-calendar',
                    'disabled': True,
                    'col_size': '3'
                },
                {
                    'label': 'Request Leave',
                    'icon': 'fas fa-file-alt',
                    'disabled': True,
                    'col_size': '3'
                },
                {
                    'label': 'View Reports',
                    'icon': 'fas fa-chart-line',
                    'disabled': True,
                    'col_size': '3'
                }
            ]

        except Exception as e:
            logger.error(f"Error in EmployeeDashboardView context: {str(e)}")
            messages.error(self.request, 'Error loading dashboard data.')

        return context


class TeamLeadDashboardView(SafeViewMixin, TeamLeadRequiredMixin, EmployeeContextMixin, TemplateView): 
    """Dashboard para Team Leads """
    template_name = 'dashboards/team_lead_dashboard.html'
    fallback_url = 'dashboard:employee_dashboard'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            print("Entrando al try")
            employee_context = self.get_employee_context()
            if not employee_context.get('employee'):
                logger.error(f"No employee context for team lead {self.request.user.username}")
                return context
            
            print("Employee context obtenido")
            
            context.update(employee_context)

            # Obtener los miembros del equipo y sus estadisticas.
            team_members = context['team_members']
            team_stats = context['team_stats']

            # Enviar contexto con info de Team Lead
            context.update({
                'team_overview_data':{
                    'main_number': team_stats['total_members'],
                    'main_label': 'Total Team Members',
                    'breakdown': {
                        'junior': team_stats['junior_count'],
                        'mid': team_stats['mid_count'],
                        'senior': team_stats['senior_count']
                    }
                },
                'leadership_actions': [
                    {
                        'label': 'Add Team Member',
                        'icon': 'fas fa-user-plus',
                        'disabled': True,
                        'col_size': '6'
                    },
                    {
                        'label': 'Schedule Team Meetings',
                        'icon': 'fas fa-calendar-check',
                        'col_size': '6'
                    },
                    {
                        'label': 'Perfomance Reviews',
                        'icon': 'fas fa-star',
                        'disabled': True,
                        'col_size': '6'
                    },
                ],
                'team_table_headers': ['Name', 'Role', 'Seniority', 'Hire Date', 'Email'],
                'team_table_data':[[
                    f"<strong>{member.full_name}</strong>",
                    member.role.title,
                    f'<span class="badge bg-light text-dark">{member.get_seniority_level_display()}</span>',
                    member.hire_date.strftime("%b %d, %Y"),
                    member.user.email
                ] for member in team_members]
            })
        
        except Exception as e:
            logger.error(f"Error in TeamLeadDashboardView context: {str(e)}")
            messages.error(self.request, 'Error loading team lead dashboard data.')

        return context

#
#   HR DEPARTMENT
#

class HRDashboardView(SafeViewMixin, HRRequiredMixin, HRContextMixin, TemplateView):
    """Dashboard para usuarios de HR"""
    template_name = 'dashboards/hr_dashboard.html'
    fallback_url = 'dashboard:home'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:
            # Agregar contexto especifico de HR
            hr_context = self.get_hr_context()
            context.update(hr_context)

            # Info templates.
            context.update({
                'hr_user': self.request.user,
                'company_overview_data':{
                    'main_number': context.get('total_employee', 0),
                    'main_label': 'Active Employees',
                    'breakdown': {
                        'junior': context.get('seniority_breakdown', {}).get('JUNIOR', 0),
                        'mid': context.get('seniority_breakdown', {}).get('MID', 0),
                        'senior': context.get('seniority_breakdown', {}).get('SENIOR', 0)
                    }
                },
                'hr_actions': [
                    {
                        'label': 'Add Employee',
                        'icon': 'fas fa-user-plus',
                        'disabled': True,
                        'col_size': '3'
                    },
                    {
                        'label': 'Manage Departments',
                        'icon': 'fas fa-building',
                        'disabled': True,
                        'col_size': '3'
                    },
                    {
                        'label': 'Generate Reports',
                        'icon': 'fas fa-chart-bar',
                        'disabled': True,
                        'col_size': '3'
                    },
                    {
                        'label': 'HR Settings',
                        'icon': 'fas fa-cog',
                        'disabled': True,
                        'col_size': '3'
                    },
                ],
                'dept_table_headers': ['Department', 'Manager', 'Employees', 'Total Salaries', 'Avg. Salaries', 'Budget', 'Budget Usage'],
                'dept_table_data': self._format_department_table_data(context.get('department_stats', []))
            })

        except Exception as e:
            logger.error(f"Error in HRDashboardView context: {str(e)}")
            messages.error(self.request, 'Error loading HR dashboard data.')

        return context
    
    def _format_department_table_data(self, dept_stats):
        """Helper method to format department table data safely"""

        try:
            return [[
                f"<strong> {dept['name']}</strong>",
                f"{dept['department_manager__user__first_name']} {dept['department_manager__user__last_name']}" if dept['department_manager__user__first_name'] else '<em class="text-muted">No manager assigned.</em>',
                f'<span class="badge bg-primary">{dept["employee_count"]}</span>',
                f'{dept["total_salaries"]:,.0f}' if dept["total_salaries"] else '<em class="text-muted">No salaries</em>',
                f'{dept["avg_salaries"]:,.0f}' if dept["avg_salaries"] else '<em class="text-muted">N/A</em>',
                f'{dept["total_budget"]:,.0f}' if dept["total_budget"] else '<em class="text-muted">N/A</em>',
                self._format_budget_badge(dept.get('salary_budget_percentage'))
            ] for dept in dept_stats]
        except Exception as e:
            logger.error(f"Error formatting department table data: {str(e)}")
            return []
        
    def _format_budget_badge(self, percentage):
        """Helper method to format budget percentage badge"""
        if not percentage:
            return '<em class="text-muted">N/A</em>'
        
        if percentage > 80:
            color = "danger"
        elif percentage > 60:
            color = "warning"
        else:
            color = "success"

        return f'<span class="badge bg-{color}">{percentage:.1f}</span>'

#
#   ADMIN
#

class AdminDashboardView(SafeViewMixin, AdminRequiredMixin, TemplateView):
    """Dashboard para administradores del sistema"""
    template_name = 'dashboards/admin_dashboard.html'
    fallback_url = 'dashboards:home'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        try:

            from employee.services import CompanyStatsService;
            from dashboards.services import UserManagementService

            # System overview Stats usando services
            system_stats = UserManagementService.get_system_overview()
            company_stats = CompanyStatsService.get_overview()

            # User Management Stats
            users_without_profile = UserManagementService.get_users_without_profile()
            group_distribution = UserManagementService.get_group_distribution()
            recent_users = UserManagementService.get_recent_users()


            context.update({
                # System overview
                **system_stats,
                'user_without_profile_count': len(users_without_profile),

                # User Management
                'users_without_profile': users_without_profile[:5], # No entiendo porque pero top 5 para mostrar
                'group_distribution': group_distribution,
                'recent_users': recent_users,

                # Company data
                **company_stats,

                # Admin user info
                'admin_user': self.request.user,
            })

        except Exception as e:
            logger.error(f"ERror in AdminDashboardView context: {str(e)}")
            messages.error(self.request, 'Error loading admin dashboard data.')

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