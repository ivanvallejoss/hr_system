# employee/test_views_update.py
"""
Tests para views de Update Salary y Update Role
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User, Group
from django.contrib.messages import get_messages
from employee.models import Employee, Department, Role, SalaryHistory, RoleHistory
from datetime import date, timedelta
from decimal import Decimal


class UpdateEmployeeSalaryViewTest(TestCase):
    """Tests para UpdateEmployeeSalaryView"""
    
    def setUp(self):
        """Setup común para todos los tests"""
        self.client = Client()
        
        # Crear grupo HR
        self.hr_group = Group.objects.create(name='HR')
        
        # Crear HR user
        self.hr_user = User.objects.create_user(
            username='hr_user',
            password='test123',
            first_name='HR',
            last_name='Manager'
        )
        self.hr_user.groups.add(self.hr_group)
        
        # Crear empleado regular
        self.regular_user = User.objects.create_user(
            username='regular_user',
            password='test123'
        )
        
        # Crear department y role
        self.department = Department.objects.create(name="IT", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
        
        # Crear employee target (el que va a ser actualizado)
        self.target_user = User.objects.create_user(
            username='target_employee',
            password='test123',
            first_name='John',
            last_name='Doe'
        )
        self.target_employee = Employee.objects.create(
            user=self.target_user,
            role=self.role,
            seniority_level='MID',
            current_salary=Decimal('60000.00'),
            hire_date=date(2023, 1, 15)
        )
        
        # HR employee
        self.hr_employee = Employee.objects.create(
            user=self.hr_user,
            role=self.role,
            current_salary=70000,
            hire_date=date(2022, 1, 1)
        )
        
        self.url = reverse('employee:update_salary', kwargs={'pk': self.target_employee.pk})
    
    def test_requires_authentication(self):
        """Test: View requiere autenticación"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_requires_hr_group(self):
        """Test: View requiere grupo HR"""
        # Login como empleado regular (sin grupo HR)
        self.client.login(username='regular_user', password='test123')
        
        response = self.client.get(self.url)
        
        # Debe redirigir con mensaje de error
        self.assertEqual(response.status_code, 302)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('HR' in str(m) or 'denied' in str(m).lower() for m in messages))
    
    def test_get_loads_form(self):
        """Test: GET request carga el form correctamente"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employee/update_salary.html')
        self.assertIn('form', response.context)
        self.assertIn('employee', response.context)
        self.assertIn('recent_salary_history', response.context)
    
    def test_form_shows_current_salary(self):
        """Test: Form muestra el salary actual en help_text"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.get(self.url)
        
        # Verificar que el help_text menciona el salary actual
        content = response.content.decode('utf-8')
        self.assertIn('60000', content)
        self.assertIn('Current salary', content)
    
    def test_valid_salary_update(self):
        """Test: Update de salary válido funciona correctamente"""
        self.client.login(username='hr_user', password='test123')
        
        new_salary = Decimal('65000.00')
        
        response = self.client.post(self.url, {
            'new_salary': new_salary,
            'effective_date': date.today(),
            'reason': 'Annual performance raise'
        })
        
        # Debe redirigir al HR dashboard
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar que se actualizó el employee
        self.target_employee.refresh_from_db()
        self.assertEqual(self.target_employee.current_salary, new_salary)
        
        # Verificar que se creó history
        history = SalaryHistory.objects.filter(employee=self.target_employee).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.old_salary, Decimal('60000.00'))
        self.assertEqual(history.new_salary, new_salary)
        self.assertEqual(history.changed_by, self.hr_user)
        self.assertEqual(history.change_reason, 'Annual performance raise')
        
        # Verificar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('success' in str(m).lower() for m in messages))
        self.assertTrue(any('60000' in str(m) for m in messages))
        self.assertTrue(any('65000' in str(m) for m in messages))
    
    def test_salary_decrease(self):
        """Test: Reducción de salary también funciona"""
        self.client.login(username='hr_user', password='test123')
        
        new_salary = Decimal('55000.00')
        
        response = self.client.post(self.url, {
            'new_salary': new_salary,
            'effective_date': date.today(),
            'reason': 'Budget adjustment'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar actualización
        self.target_employee.refresh_from_db()
        self.assertEqual(self.target_employee.current_salary, new_salary)
        
        # Verificar history
        history = SalaryHistory.objects.filter(employee=self.target_employee).first()
        self.assertTrue(history.is_decrease)
    
    def test_same_salary_rejected(self):
        """Test: Rechaza salary igual al actual"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_salary': self.target_employee.current_salary,  # Mismo valor
            'effective_date': date.today(),
            'reason': 'No change'
        })
        
        # No debe redirigir (re-renderiza form con errores)
        self.assertEqual(response.status_code, 200)
        
        # Debe tener errores en el form
        self.assertFormError(
            response.context['form'],
            'new_salary',
            'New salary must be different from current salary ($60,000.00)'
        )
        
        # No debe crear history
        self.assertEqual(SalaryHistory.objects.count(), 0)
    
    def test_negative_salary_rejected(self):
        """Test: Rechaza salary negativo"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_salary': Decimal('-1000.00'),
            'effective_date': date.today(),
            'reason': 'Invalid'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertEqual(SalaryHistory.objects.count(), 0)
    
    def test_effective_date_before_hire_date_rejected(self):
        """Test: Rechaza effective_date antes de hire_date"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_salary': Decimal('65000.00'),
            'effective_date': date(2022, 1, 1),  # Antes de hire_date (2023-01-15)
            'reason': 'Invalid date'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context['form'],
            'effective_date',
            'Effective date cannot be before hire date (2023-01-15)'
        )
    
    def test_future_effective_date_allowed(self):
        """Test: Permite effective_date en el futuro"""
        self.client.login(username='hr_user', password='test123')
        
        future_date = date.today() + timedelta(days=30)
        
        response = self.client.post(self.url, {
            'new_salary': Decimal('65000.00'),
            'effective_date': future_date,
            'reason': 'Future raise scheduled'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar que se creó con fecha futura
        history = SalaryHistory.objects.first()
        self.assertEqual(history.effective_date, future_date)
    
    def test_404_for_nonexistent_employee(self):
        """Test: Retorna 404 para employee que no existe"""
        self.client.login(username='hr_user', password='test123')
        
        url = reverse('employee:update_salary', kwargs={'pk': 99999})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)


class UpdateEmployeeRoleViewTest(TestCase):
    """Tests para UpdateEmployeeRoleView"""
    
    def setUp(self):
        """Setup común"""
        self.client = Client()
        
        # Crear grupo HR
        self.hr_group = Group.objects.create(name='HR')
        
        # Crear HR user
        self.hr_user = User.objects.create_user(
            username='hr_user',
            password='test123'
        )
        self.hr_user.groups.add(self.hr_group)
        
        # Crear departments y roles
        self.it_dept = Department.objects.create(name="IT", budget=100000)
        self.marketing_dept = Department.objects.create(name="Marketing", budget=80000)
        
        self.dev_role = Role.objects.create(title="Developer", department=self.it_dept)
        self.senior_dev_role = Role.objects.create(title="Senior Developer", department=self.it_dept)
        self.marketing_role = Role.objects.create(title="Marketing Manager", department=self.marketing_dept)
        
        # Crear employee target
        self.target_user = User.objects.create_user(
            username='target_employee',
            password='test123',
            first_name='Jane',
            last_name='Smith'
        )
        self.target_employee = Employee.objects.create(
            user=self.target_user,
            role=self.dev_role,
            seniority_level='JUNIOR',
            current_salary=50000,
            hire_date=date(2023, 1, 15)
        )
        
        # HR employee
        self.hr_employee = Employee.objects.create(
            user=self.hr_user,
            role=self.senior_dev_role,
            current_salary=80000,
            hire_date=date(2020, 1, 1)
        )
        
        self.url = reverse('employee:update_role', kwargs={'pk': self.target_employee.pk})
    
    def test_requires_authentication(self):
        """Test: View requiere autenticación"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_requires_hr_group(self):
        """Test: View requiere grupo HR"""
        regular_user = User.objects.create_user(username='regular', password='test123')
        self.client.login(username='regular', password='test123')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 302)
    
    def test_get_loads_form(self):
        """Test: GET request carga el form"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employee/update_role.html')
        self.assertIn('form', response.context)
        self.assertIn('employee', response.context)
    
    def test_promotion_seniority_only(self):
        """Test: Promoción solo de seniority (mismo role)"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.dev_role.pk,  # Mismo role
            'new_seniority': 'MID',  # Promoción
            'effective_date': date.today(),
            'reason': 'Performance promotion'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar actualización
        self.target_employee.refresh_from_db()
        self.assertEqual(self.target_employee.role, self.dev_role)
        self.assertEqual(self.target_employee.seniority_level, 'MID')
        
        # Verificar history
        history = RoleHistory.objects.first()
        self.assertTrue(history.is_promotion)
        self.assertEqual(history.old_seniority, 'JUNIOR')
        self.assertEqual(history.new_seniority, 'MID')
    
    def test_role_change_same_seniority(self):
        """Test: Cambio de role sin cambio de seniority (lateral move)"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.senior_dev_role.pk,  # Nuevo role
            'new_seniority': 'JUNIOR',  # Mismo seniority
            'effective_date': date.today(),
            'reason': 'Internal transfer'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar
        self.target_employee.refresh_from_db()
        self.assertEqual(self.target_employee.role, self.senior_dev_role)
        
        # Verificar history
        history = RoleHistory.objects.first()
        self.assertTrue(history.is_lateral_move)
    
    def test_role_and_seniority_change(self):
        """Test: Cambio de role Y seniority simultáneamente"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.senior_dev_role.pk,
            'new_seniority': 'MID',
            'effective_date': date.today(),
            'reason': 'Promotion to senior position'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar
        self.target_employee.refresh_from_db()
        self.assertEqual(self.target_employee.role, self.senior_dev_role)
        self.assertEqual(self.target_employee.seniority_level, 'MID')
        
        # Verificar history
        history = RoleHistory.objects.first()
        self.assertTrue(history.is_promotion)
        self.assertNotEqual(history.old_role, history.new_role)
    
    def test_department_change_detected(self):
        """Test: Detecta cambio de department"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.marketing_role.pk,  # Otro department
            'new_seniority': 'MID',
            'effective_date': date.today(),
            'reason': 'Department transfer'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar history
        history = RoleHistory.objects.first()
        self.assertTrue(history.changed_department)
        self.assertEqual(history.old_role.department, self.it_dept)
        self.assertEqual(history.new_role.department, self.marketing_dept)
    
    def test_no_change_rejected(self):
        """Test: Rechaza si no hay cambio en role ni seniority"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.dev_role.pk,  # Mismo
            'new_seniority': 'JUNIOR',  # Mismo
            'effective_date': date.today(),
            'reason': 'No real change'
        })
        
        # No debe redirigir
        self.assertEqual(response.status_code, 200)
        
        # Debe tener errores
        self.assertTrue(response.context['form'].errors)
        
        # No debe crear history
        self.assertEqual(RoleHistory.objects.count(), 0)
    
    def test_success_message_for_promotion(self):
        """Test: Mensaje de éxito específico para promoción"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.dev_role.pk,
            'new_seniority': 'SENIOR',
            'effective_date': date.today(),
            'reason': 'Promoted to senior'
        })
        
        messages = list(get_messages(response.wsgi_request))
        
        # Debe contener emoji de celebración para promoción
        message_text = ' '.join(str(m) for m in messages)
        self.assertIn('🎉', message_text)
        self.assertIn('Promotion', message_text)
    
    def test_success_message_for_lateral_move(self):
        """Test: Mensaje específico para lateral move"""
        self.client.login(username='hr_user', password='test123')
        
        response = self.client.post(self.url, {
            'new_role': self.senior_dev_role.pk,
            'new_seniority': 'JUNIOR',
            'effective_date': date.today(),
            'reason': 'Lateral transfer'
        })
        
        messages = list(get_messages(response.wsgi_request))
        message_text = ' '.join(str(m) for m in messages)
        
        self.assertIn('↔️', message_text)
        self.assertIn('Role change', message_text)


class UpdateViewsPermissionsTest(TestCase):
    """Tests específicos de permisos"""
    
    def setUp(self):
        """Setup"""
        self.client = Client()
        
        # Crear superuser
        self.superuser = User.objects.create_superuser(
            username='admin',
            password='admin123',
            email='admin@test.com'
        )
        
        # Crear department y role
        self.department = Department.objects.create(name="IT", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
        
        # Crear employee
        user = User.objects.create_user(username='employee', password='test123')
        self.employee = Employee.objects.create(
            user=user,
            role=self.role,
            current_salary=60000,
            hire_date=date.today()
        )
    
    def test_superuser_can_access_without_hr_group(self):
        """Test: Superuser puede acceder sin estar en grupo HR"""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('employee:update_salary', kwargs={'pk': self.employee.pk})
        response = self.client.get(url)
        
        # Debe poder acceder
        self.assertEqual(response.status_code, 200)
    
    def test_superuser_can_update_salary(self):
        """Test: Superuser puede actualizar salary"""
        self.client.login(username='admin', password='admin123')
        
        url = reverse('employee:update_salary', kwargs={'pk': self.employee.pk})
        response = self.client.post(url, {
            'new_salary': Decimal('70000.00'),
            'effective_date': date.today(),
            'reason': 'Superuser adjustment'
        })
        
        self.assertRedirects(response, reverse('dashboards:hr_dashboard'))
        
        # Verificar que se actualizó
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.current_salary, Decimal('70000.00'))
        
        # Verificar que el changed_by es el superuser
        history = SalaryHistory.objects.first()
        self.assertEqual(history.changed_by, self.superuser)