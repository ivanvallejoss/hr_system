# dashboards/test_routing.py
"""
Tests para DashboardRouter
"""
from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
from employee.models import Employee, Department, Role
from dashboards.services import DashboardRouter


class DashboardRouterTest(TestCase):
    """Tests para el DashboardRouter"""
    
    def setUp(self):
        """Setup común para todos los tests"""
        # Crear grupos
        self.admin_group = Group.objects.create(name='Admin')
        self.hr_group = Group.objects.create(name='HR')
        
        # Crear department y role
        self.department = Department.objects.create(name="IT", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
    
    def test_superuser_goes_to_admin_dashboard(self):
        """Test: Superuser siempre va a admin dashboard"""
        superuser = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@test.com'
        )
        
        url = DashboardRouter.get_dashboard_url(superuser)
        self.assertEqual(url, 'dashboards:admin_dashboard')
    
    def test_admin_group_goes_to_admin_dashboard(self):
        """Test: Usuario en grupo Admin va a admin dashboard"""
        user = User.objects.create_user(username='admin_user', password='test123')
        user.groups.add(self.admin_group)
        
        url = DashboardRouter.get_dashboard_url(user)
        self.assertEqual(url, 'dashboards:admin_dashboard')
    
    def test_hr_group_goes_to_hr_dashboard(self):
        """Test: Usuario en grupo HR va a HR dashboard"""
        user = User.objects.create_user(username='hr_user', password='test123')
        user.groups.add(self.hr_group)
        
        url = DashboardRouter.get_dashboard_url(user)
        self.assertEqual(url, 'dashboards:hr_dashboard')
    
    def test_team_lead_goes_to_team_lead_dashboard(self):
        """Test: Team lead va a team lead dashboard"""
        user = User.objects.create_user(username='tl_user', password='test123')
        employee = Employee.objects.create(
            user=user,
            role=self.role,
            current_salary=80000,
            hire_date='2023-01-01'
        )
        
        # Hacer que sea team lead (tiene team members)
        subordinate_user = User.objects.create_user(username='sub', password='test123')
        Employee.objects.create(
            user=subordinate_user,
            role=self.role,
            manager=employee,
            current_salary=60000,
            hire_date='2024-01-01'
        )
        
        url = DashboardRouter.get_dashboard_url(user, employee)
        self.assertEqual(url, 'dashboards:team_lead_dashboard')
    
    def test_regular_employee_goes_to_employee_dashboard(self):
        """Test: Empleado regular va a employee dashboard"""
        user = User.objects.create_user(username='emp_user', password='test123')
        employee = Employee.objects.create(
            user=user,
            role=self.role,
            current_salary=60000,
            hire_date='2024-01-01'
        )
        
        url = DashboardRouter.get_dashboard_url(user, employee)
        self.assertEqual(url, 'dashboards:employee_dashboard')
    
    def test_priority_admin_over_hr(self):
        """Test: Si usuario está en Admin + HR, prioriza Admin"""
        user = User.objects.create_user(username='multi_user', password='test123')
        user.groups.add(self.admin_group)
        user.groups.add(self.hr_group)
        
        url = DashboardRouter.get_dashboard_url(user)
        self.assertEqual(url, 'dashboards:admin_dashboard')
    
    def test_priority_hr_over_team_lead(self):
        """Test: Si usuario está en HR y es team lead, prioriza HR"""
        user = User.objects.create_user(username='hr_tl', password='test123')
        user.groups.add(self.hr_group)
        
        employee = Employee.objects.create(
            user=user,
            role=self.role,
            current_salary=80000,
            hire_date='2023-01-01'
        )
        
        # Hacer que sea team lead
        subordinate_user = User.objects.create_user(username='sub2', password='test123')
        Employee.objects.create(
            user=subordinate_user,
            role=self.role,
            manager=employee,
            current_salary=60000,
            hire_date='2024-01-01'
        )
        
        url = DashboardRouter.get_dashboard_url(user, employee)
        self.assertEqual(url, 'dashboards:hr_dashboard')
    
    def test_add_group_mapping_dynamically(self):
        """Test: Agregar nuevo grupo dinámicamente"""
        # Agregar nuevo grupo
        DashboardRouter.add_group_mapping('Finance', 'dashboards:finance_dashboard')
        
        # Crear usuario con ese grupo
        finance_group = Group.objects.create(name='Finance')
        user = User.objects.create_user(username='finance_user', password='test123')
        user.groups.add(finance_group)
        
        url = DashboardRouter.get_dashboard_url(user)
        self.assertEqual(url, 'dashboards:finance_dashboard')
    
    def test_user_without_employee_profile(self):
        """Test: Usuario sin perfil de empleado (employee=None)"""
        user = User.objects.create_user(username='no_profile', password='test123')
        self.client.login(username='noprofile', password='test123')

        response = self.client.get(reverse('dashboards:dashboard_redirect'))
        self.assertRedirects(response, '/accounts/login/?next=/dashboard/')