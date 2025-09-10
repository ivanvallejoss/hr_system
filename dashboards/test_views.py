"""
Tests para views de dashboards y sistema de permisos
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.contrib.messages import get_messages
from datetime import date
from employee.models import Department, Role, Employee


class DashboardRedirectTest(TestCase):
    """Tests para la lógica de redirección de dashboards"""
    
    def setUp(self):
        self.client = Client()
        
        # Crear grupos
        self.admin_group = Group.objects.create(name='Admin')
        self.hr_group = Group.objects.create(name='HR')
        
        # Crear department y role para empleados
        self.department = Department.objects.create(name="IT", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
    
    def test_anonymous_user_redirects_to_login(self):
        """Usuario anónimo debe ir a login"""
        response = self.client.get(reverse('dashboards:home'))
        self.assertRedirects(response, '/accounts/login/')
    
    def test_superuser_redirects_to_admin_dashboard(self):
        """Superuser debe ir a admin dashboard"""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )
        self.client.login(username='admin', password='testpass123')
        
        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        self.assertRedirects(response, reverse('dashboards:admin_dashboard'))
    
    def test_admin_group_user_redirects_to_admin_dashboard(self):
        """Usuario del grupo Admin debe ir a admin dashboard"""
        admin_user = User.objects.create_user(
            username='adminuser',
            password='testpass123'
        )
        admin_user.groups.add(self.admin_group)
        
        # Crear perfil de empleado (requerido por middleware)
        Employee.objects.create(
            user=admin_user,
            role=self.role,
            current_salary=80000,
            hire_date=date.today()
        )
        
        self.client.login(username='adminuser', password='testpass123')
        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        self.assertRedirects(response, reverse('dashboards:admin_dashboard'))
    
    def test_hr_user_redirects_to_hr_dashboard(self):
        """Usuario HR debe ir a HR dashboard"""
        hr_user = User.objects.create_user(
            username='hruser',
            password='testpass123'
        )
        hr_user.groups.add(self.hr_group)
        
        Employee.objects.create(
            user=hr_user,
            role=self.role,
            current_salary=70000,
            hire_date=date.today()
        )
        
        self.client.login(username='hruser', password='testpass123')
        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
    
    def test_team_lead_redirects_to_team_lead_dashboard(self):
        """Team lead debe ir a su dashboard específico"""
        # Crear team lead
        lead_user = User.objects.create_user(
            username='teamlead',
            password='testpass123'
        )
        team_lead = Employee.objects.create(
            user=lead_user,
            role=self.role,
            current_salary=90000,
            hire_date=date.today()
        )
        
        # Crear subordinado para convertirlo en team lead
        subordinate_user = User.objects.create_user(username='subordinate')
        Employee.objects.create(
            user=subordinate_user,
            role=self.role,
            manager=team_lead,
            current_salary=60000,
            hire_date=date.today()
        )
        
        self.client.login(username='teamlead', password='testpass123')
        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        self.assertRedirects(response, reverse('dashboards:team_lead_dashboard'))
    
    def test_regular_employee_redirects_to_employee_dashboard(self):
        """Empleado regular debe ir a employee dashboard"""
        employee_user = User.objects.create_user(
            username='employee',
            password='testpass123'
        )
        Employee.objects.create(
            user=employee_user,
            role=self.role,
            current_salary=50000,
            hire_date=date.today()
        )
        
        self.client.login(username='employee', password='testpass123')
        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        self.assertRedirects(response, reverse('dashboards:employee_dashboard'))
    
    def test_user_without_employee_profile_gets_error(self):
        """Usuario sin perfil de empleado debe recibir error"""
        user_no_profile = User.objects.create_user(
            username='noprofile',
            password='testpass123'
        )
        
        self.client.login(username='noprofile', password='testpass123')
        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        
        # Debe redirigir a login con mensaje de error
        self.assertRedirects(response, '/accounts/login/')
        
        # Verificar mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('You need an employee profile to access the system.' in str(m) for m in messages))


class EmployeeDashboardViewTest(TestCase):
    """Tests para EmployeeDashboardView"""
    
    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(name="Engineering", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
        
        self.user = User.objects.create_user(
            username='testemployee',
            first_name='John',
            last_name='Doe',
            password='testpass123'
        )
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.role,
            seniority_level='MID',
            current_salary=75000,
            hire_date=date(2023, 1, 15)
        )
    
    def test_employee_dashboard_requires_login(self):
        """Dashboard requiere login"""
        response = self.client.get(reverse('dashboards:employee_dashboard'))
        self.assertRedirects(response, '/accounts/login/?next=/employee/dashboard/')
    
    def test_employee_dashboard_loads_correctly(self):
        """Dashboard carga correctamente para empleado autenticado"""
        self.client.login(username='testemployee', password='testpass123')
        response = self.client.get(reverse('dashboards:employee_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Employee Dashboard')
        self.assertContains(response, 'John Doe')
        self.assertContains(response, 'Developer')
        self.assertContains(response, 'Engineering')
    
    def test_employee_dashboard_context_data(self):
        """Verificar que el contexto contiene los datos correctos"""
        self.client.login(username='testemployee', password='testpass123')
        response = self.client.get(reverse('dashboards:employee_dashboard'))
        
        context = response.context
        
        # Verificar datos del empleado
        self.assertEqual(context['employee'], self.employee)
        self.assertEqual(context['is_team_lead'], False)
        self.assertIn('years_employed', context)
        self.assertIn('days_employed', context)
        self.assertIn('quick_actions', context)


class TeamLeadDashboardViewTest(TestCase):
    """Tests para TeamLeadDashboardView"""
    
    def setUp(self):
        self.client = Client()
        self.department = Department.objects.create(name="Engineering")
        self.role = Role.objects.create(title="Senior Developer", department=self.department)
        
        # Crear team lead
        self.lead_user = User.objects.create_user(
            username='teamlead',
            first_name='Jane',
            last_name='Smith',
            password='testpass123'
        )
        self.team_lead = Employee.objects.create(
            user=self.lead_user,
            role=self.role,
            seniority_level='SENIOR',
            current_salary=100000,
            hire_date=date(2022, 1, 1)
        )
        
        # Crear miembros del equipo
        self.create_team_member('member1', 'JUNIOR')
        self.create_team_member('member2', 'MID')
        self.create_team_member('member3', 'SENIOR')
    
    def create_team_member(self, username, seniority):
        """Helper para crear miembros del equipo"""
        user = User.objects.create_user(username=username)
        return Employee.objects.create(
            user=user,
            role=self.role,
            manager=self.team_lead,
            seniority_level=seniority,
            current_salary=50000,
            hire_date=date.today()
        )
    
    def test_team_lead_dashboard_requires_team_lead_permission(self):
        """Solo team leads pueden acceder"""
        # Crear empleado regular
        regular_user = User.objects.create_user(username='regular', password='testpass123')
        Employee.objects.create(
            user=regular_user,
            role=self.role,
            current_salary=60000,
            hire_date=date.today()
        )
        
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('dashboards:team_lead_dashboard'))
        
        # Debe redirigir a employee dashboard
        self.assertRedirects(response, reverse('dashboards:employee_dashboard'))
    
    def test_team_lead_dashboard_loads_correctly(self):
        """Team lead dashboard carga correctamente"""
        self.client.login(username='teamlead', password='testpass123')
        response = self.client.get(reverse('dashboards:team_lead_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Team Lead Dashboard')
        self.assertContains(response, 'Jane Smith')
    
    def test_team_lead_dashboard_shows_team_stats(self):
        """Dashboard muestra estadísticas del equipo"""
        self.client.login(username='teamlead', password='testpass123')
        response = self.client.get(reverse('dashboards:team_lead_dashboard'))
        
        context = response.context
        
        # Verificar estadísticas del equipo
        team_overview = context['team_overview_data']
        self.assertEqual(team_overview['main_number'], 3)  # 3 miembros del equipo
        self.assertEqual(team_overview['breakdown']['junior'], 1)
        self.assertEqual(team_overview['breakdown']['mid'], 1)
        self.assertEqual(team_overview['breakdown']['senior'], 1)
        
        # Verificar datos de la tabla
        self.assertIn('team_table_data', context)
        self.assertEqual(len(context['team_table_data']), 3)


class PermissionMixinTest(TestCase):
    """Tests para los mixins de permisos"""
    
    def setUp(self):
        self.client = Client()
        self.hr_group = Group.objects.create(name='HR')
        self.admin_group = Group.objects.create(name='Admin')
        
        self.department = Department.objects.create(name="HR", budget=50000)
        self.role = Role.objects.create(title="HR Manager", department=self.department)
    
    def test_hr_dashboard_requires_hr_group(self):
        """HR Dashboard requiere grupo HR - Test robusto"""
        # Usuario sin grupo HR
        regular_user = User.objects.create_user(username='regular', password='testpass123')
        Employee.objects.create(
            user=regular_user,
            role=self.role,
            current_salary=60000,
            hire_date=date.today()
        )
        
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('dashboards:hr_dashboard'), follow=True)
        
        # Verificar que termina en el dashboard correcto (siguiendo todas las redirecciones)
        self.assertEqual(response.status_code, 200)
        # Como el usuario es empleado regular, debería terminar en employee dashboard
        self.assertContains(response, 'Employee Dashboard')
        
        # Verificar mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('permissions' in str(m).lower() for m in messages))
    
    def test_hr_dashboard_allows_hr_group(self):
        """HR Dashboard permite acceso a grupo HR"""
        hr_user = User.objects.create_user(username='hruser', password='testpass123')
        hr_user.groups.add(self.hr_group)
        Employee.objects.create(
            user=hr_user,
            role=self.role,
            current_salary=80000,
            hire_date=date.today()
        )
        
        self.client.login(username='hruser', password='testpass123')
        response = self.client.get(reverse('dashboards:hr_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'HR Management Dashboard')
    
    def test_admin_dashboard_requires_admin_group(self):
        """Admin Dashboard requiere grupo Admin"""
        regular_user = User.objects.create_user(username='regular', password='testpass123')
        Employee.objects.create(
            user=regular_user,
            role=self.role,
            current_salary=60000,
            hire_date=date.today()
        )
        
        self.client.login(username='regular', password='testpass123')
        response = self.client.get(reverse('dashboards:admin_dashboard'), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Employee Dashboard')
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('permissions' in str(m).lower() for m in messages))
    
    def test_superuser_bypasses_group_requirements(self):
        """Superuser puede acceder a cualquier dashboard"""
        superuser = User.objects.create_superuser(
            username='admin',
            email='admin@test.com', 
            password='testpass123'
        )
        
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('dashboards:admin_dashboard'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'System Administration Dashboard')