# employee/test_history.py
"""
Tests para modelos de history tracking (SalaryHistory, RoleHistory)
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from employee.models import Employee, Department, Role, SalaryHistory, RoleHistory
from datetime import date, timedelta
from decimal import Decimal


class SalaryHistoryModelTest(TestCase):
    """Tests para el modelo SalaryHistory"""
    
    def setUp(self):
        """Setup común para todos los tests"""
        self.department = Department.objects.create(name="IT", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
        
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.hr_user = User.objects.create_user(username='hr_user', password='test123')
        
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.role,
            current_salary=Decimal('60000.00'),
            hire_date=date(2023, 1, 15)
        )
    
    def test_create_salary_history(self):
        """Test: Crear registro de salary history básico"""
        history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('65000.00'),
            changed_by=self.hr_user,
            change_reason="Annual raise",
            effective_date=date.today()
        )
        
        self.assertIsNotNone(history.id)
        self.assertEqual(history.employee, self.employee)
        self.assertEqual(history.old_salary, Decimal('60000.00'))
        self.assertEqual(history.new_salary, Decimal('65000.00'))
    
    def test_change_amount_calculation(self):
        """Test: Cálculo de change_amount"""
        history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('66000.00'),
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        self.assertEqual(history.change_amount, Decimal('6000.00'))
    
    def test_change_percentage_calculation(self):
        """Test: Cálculo de change_percentage"""
        history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('66000.00'),
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        # 6000 / 60000 * 100 = 10%
        self.assertEqual(history.change_percentage, 10.0)
    
    def test_change_percentage_with_zero_old_salary(self):
        """Test: change_percentage maneja old_salary = 0 sin error"""
        history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('0.00'),
            new_salary=Decimal('60000.00'),
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        # No debe lanzar ZeroDivisionError
        self.assertEqual(history.change_percentage, 0)
    
    def test_is_raise_property(self):
        """Test: is_raise detecta aumentos correctamente"""
        raise_history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('65000.00'),
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        self.assertTrue(raise_history.is_raise)
        self.assertFalse(raise_history.is_decrease)
    
    def test_is_decrease_property(self):
        """Test: is_decrease detecta reducciones correctamente"""
        decrease_history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('55000.00'),
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        self.assertTrue(decrease_history.is_decrease)
        self.assertFalse(decrease_history.is_raise)
    
    def test_validation_same_salary(self):
        """Test: Validación rechaza old_salary == new_salary"""
        history = SalaryHistory(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('60000.00'),  # Mismo valor
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        with self.assertRaises(ValidationError) as context:
            history.full_clean()
        
        self.assertIn('cannot be the same', str(context.exception))
    
    def test_validation_negative_salary(self):
        """Test: Validación rechaza salaries negativos"""
        history = SalaryHistory(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('-5000.00'),  # Negativo
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        with self.assertRaises(ValidationError) as context:
            history.full_clean()
        
        self.assertIn('must be positive', str(context.exception))
    
    def test_validation_effective_date_before_hire_date(self):
        """Test: Validación rechaza effective_date antes de hire_date"""
        history = SalaryHistory(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('65000.00'),
            changed_by=self.hr_user,
            effective_date=date(2022, 1, 1)  # Antes de hire_date (2023-01-15)
        )
        
        with self.assertRaises(ValidationError) as context:
            history.full_clean()
        
        self.assertIn('before hire date', str(context.exception))
    
    def test_ordering_by_effective_date(self):
        """Test: History se ordena por effective_date descendente"""
        # Crear múltiples registros
        SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('62000.00'),
            effective_date=date(2023, 6, 1),
            changed_by=self.hr_user
        )
        SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('62000.00'),
            new_salary=Decimal('65000.00'),
            effective_date=date(2024, 1, 1),
            changed_by=self.hr_user
        )
        SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('65000.00'),
            new_salary=Decimal('70000.00'),
            effective_date=date(2024, 6, 1),
            changed_by=self.hr_user
        )
        
        # Obtener todos
        all_history = list(self.employee.salary_history.all())
        
        # Verificar orden (más reciente primero)
        self.assertEqual(all_history[0].new_salary, Decimal('70000.00'))
        self.assertEqual(all_history[1].new_salary, Decimal('65000.00'))
        self.assertEqual(all_history[2].new_salary, Decimal('62000.00'))
    
    def test_str_representation(self):
        """Test: __str__ retorna formato legible"""
        history = SalaryHistory.objects.create(
            employee=self.employee,
            old_salary=Decimal('60000.00'),
            new_salary=Decimal('65000.00'),
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        expected = f"{self.employee.full_name}: $60000.00 -> $65000.00"
        self.assertEqual(str(history), expected)


class RoleHistoryModelTest(TestCase):
    """Tests para el modelo RoleHistory"""
    
    def setUp(self):
        """Setup común para todos los tests"""
        self.department = Department.objects.create(name="IT", budget=100000)
        self.dev_role = Role.objects.create(title="Developer", department=self.department)
        self.senior_dev_role = Role.objects.create(title="Senior Developer", department=self.department)
        
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.hr_user = User.objects.create_user(username='hr_user', password='test123')
        
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.dev_role,
            seniority_level='JUNIOR',
            current_salary=50000,
            hire_date=date(2023, 1, 15)
        )
    
    def test_create_role_history(self):
        """Test: Crear registro de role history básico"""
        history = RoleHistory.objects.create(
            employee=self.employee,
            old_role=self.dev_role,
            new_role=self.senior_dev_role,
            old_seniority='JUNIOR',
            new_seniority='MID',
            changed_by=self.hr_user,
            change_reason="Promotion",
            effective_date=date.today()
        )
        
        self.assertIsNotNone(history.id)
        self.assertEqual(history.employee, self.employee)
        self.assertEqual(history.old_role, self.dev_role)
        self.assertEqual(history.new_role, self.senior_dev_role)
    
    def test_is_promotion_or_demotion(self):
        """Test: is_promotion detecta promociones de seniority"""
        promotion = RoleHistory.objects.create(
            employee=self.employee,
            old_role=self.dev_role,
            new_role=self.senior_dev_role,
            old_seniority='JUNIOR',
            new_seniority='MID',  # Promoción
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        self.assertEqual(promotion.promotion_or_demotion, 'promotion')
        self.assertNotEqual(promotion.promotion_or_demotion, 'demotion')
    
    def test_is_lateral_move_property(self):
        """Test: is_lateral_move detecta cambio de role sin cambio de seniority"""
        lateral = RoleHistory.objects.create(
            employee=self.employee,
            old_role=self.dev_role,
            new_role=self.senior_dev_role,
            old_seniority='MID',
            new_seniority='MID',  # Mismo seniority
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        self.assertTrue(lateral.is_lateral_move)
        self.assertFalse(lateral.is_promotion)
    
    def test_changed_department_property(self):
        """Test: changed_department detecta cambio de department"""
        # Crear department y role diferentes
        new_dept = Department.objects.create(name="Marketing", budget=50000)
        marketing_role = Role.objects.create(title="Marketing Manager", department=new_dept)
        
        history = RoleHistory.objects.create(
            employee=self.employee,
            old_role=self.dev_role,  # IT department
            new_role=marketing_role,  # Marketing department
            old_seniority='MID',
            new_seniority='MID',
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        self.assertTrue(history.changed_department)
    
    def test_validation_no_change(self):
        """Test: Validación rechaza si no hay cambio en role ni seniority"""
        history = RoleHistory(
            employee=self.employee,
            old_role=self.dev_role,
            new_role=self.dev_role,  # Mismo role
            old_seniority='JUNIOR',
            new_seniority='JUNIOR',  # Mismo seniority
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        with self.assertRaises(ValidationError) as context:
            history.full_clean()
        
        self.assertIn('change in either role or seniority', str(context.exception))
    
    def test_validation_effective_date_before_hire_date(self):
        """Test: Validación rechaza effective_date antes de hire_date"""
        history = RoleHistory(
            employee=self.employee,
            old_role=self.dev_role,
            new_role=self.senior_dev_role,
            old_seniority='JUNIOR',
            new_seniority='MID',
            changed_by=self.hr_user,
            effective_date=date(2022, 1, 1)  # Antes de hire_date
        )
        
        with self.assertRaises(ValidationError) as context:
            history.full_clean()
        
        self.assertIn('before hire date', str(context.exception))
    
    def test_str_representation(self):
        """Test: __str__ retorna formato legible"""
        history = RoleHistory.objects.create(
            employee=self.employee,
            old_role=self.dev_role,
            new_role=self.senior_dev_role,
            old_seniority='JUNIOR',
            new_seniority='MID',
            changed_by=self.hr_user,
            effective_date=date.today()
        )
        
        expected = f"{self.employee.full_name}: Developer -> Senior Developer"
        self.assertEqual(str(history), expected)


class EmployeeHistoryMethodsTest(TestCase):
    """Tests para los helper methods de Employee relacionados con history"""
    
    def setUp(self):
        """Setup común"""
        self.department = Department.objects.create(name="IT", budget=100000)
        self.dev_role = Role.objects.create(title="Developer", department=self.department)
        self.senior_role = Role.objects.create(title="Senior Developer", department=self.department)
        
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.hr_user = User.objects.create_user(username='hr_user', password='test123')
        
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.dev_role,
            seniority_level='JUNIOR',
            current_salary=Decimal('60000.00'),
            hire_date=date(2023, 1, 15)
        )
    
    def test_update_salary_creates_history(self):
        """Test: update_salary() crea registro de history"""
        old_salary = self.employee.current_salary
        new_salary = Decimal('65000.00')
        
        history = self.employee.update_salary(
            new_salary=new_salary,
            changed_by=self.hr_user,
            reason="Annual raise"
        )
        
        # Verificar que se creó history
        self.assertIsNotNone(history.id)
        self.assertEqual(history.old_salary, old_salary)
        self.assertEqual(history.new_salary, new_salary)
        
        # Verificar que se actualizó el employee
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.current_salary, new_salary)
    
    def test_update_salary_validation_same_salary(self):
        """Test: update_salary() rechaza mismo salary"""
        with self.assertRaises(ValidationError) as context:
            self.employee.update_salary(
                new_salary=self.employee.current_salary,
                changed_by=self.hr_user
            )
        
        self.assertIn('different from current', str(context.exception))
    
    def test_update_salary_validation_negative(self):
        """Test: update_salary() rechaza salary negativo"""
        with self.assertRaises(ValidationError) as context:
            self.employee.update_salary(
                new_salary=Decimal('-1000.00'),
                changed_by=self.hr_user
            )
        
        self.assertIn('must be positive', str(context.exception))
    
    def test_update_salary_with_effective_date(self):
        """Test: update_salary() acepta effective_date custom"""
        future_date = date.today() + timedelta(days=30)
        
        history = self.employee.update_salary(
            new_salary=Decimal('70000.00'),
            changed_by=self.hr_user,
            reason="Future raise",
            effective_date=future_date
        )
        
        self.assertEqual(history.effective_date, future_date)
    
    def test_update_role_creates_history(self):
        """Test: update_role() crea registro de history"""
        history = self.employee.update_role(
            new_role=self.senior_role,
            new_seniority='MID',
            changed_by=self.hr_user,
            reason="Promotion"
        )
        
        # Verificar history
        self.assertIsNotNone(history.id)
        self.assertEqual(history.old_role, self.dev_role)
        self.assertEqual(history.new_role, self.senior_role)
        self.assertEqual(history.old_seniority, 'JUNIOR')
        self.assertEqual(history.new_seniority, 'MID')
        
        # Verificar employee actualizado
        self.employee.refresh_from_db()
        self.assertEqual(self.employee.role, self.senior_role)
        self.assertEqual(self.employee.seniority_level, 'MID')
    
    def test_update_role_only_seniority(self):
        """Test: update_role() puede cambiar solo seniority"""
        history = self.employee.update_role(
            new_seniority='MID',
            changed_by=self.hr_user,
            reason="Seniority promotion"
        )
        
        # Role debe ser el mismo
        self.assertEqual(history.old_role, self.dev_role)
        self.assertEqual(history.new_role, self.dev_role)
        
        # Seniority debe cambiar
        self.assertEqual(history.old_seniority, 'JUNIOR')
        self.assertEqual(history.new_seniority, 'MID')
    
    def test_update_role_validation_no_change(self):
        """Test: update_role() rechaza si no hay cambios"""
        with self.assertRaises(ValidationError) as context:
            self.employee.update_role(
                new_role=self.dev_role,  # Mismo role
                new_seniority='JUNIOR',  # Mismo seniority
                changed_by=self.hr_user
            )
        
        self.assertIn('Must change either', str(context.exception))
    
    def test_get_salary_history(self):
        """Test: get_salary_history() retorna history correctamente"""
        # Crear múltiples registros
        self.employee.update_salary(Decimal('62000'), self.hr_user, "Raise 1")
        self.employee.update_salary(Decimal('65000'), self.hr_user, "Raise 2")
        self.employee.update_salary(Decimal('70000'), self.hr_user, "Raise 3")
        
        history = self.employee.get_salary_history()
        
        self.assertEqual(history.count(), 3)
    
    def test_get_salary_history_with_date_filter(self):
        """Test: get_salary_history() filtra por fechas"""
        # Crear registros en diferentes fechas
        past_date = date(2023, 6, 1)
        recent_date = date(2024, 6, 1)
        
        self.employee.update_salary(
            Decimal('62000'), 
            self.hr_user, 
            "Old raise",
            effective_date=past_date
        )
        self.employee.update_salary(
            Decimal('65000'), 
            self.hr_user, 
            "Recent raise",
            effective_date=recent_date
        )
        
        # Filtrar solo recientes
        history = self.employee.get_salary_history(start_date=date(2024, 1, 1))
        
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().new_salary, Decimal('65000'))
    
    def test_total_salary_increases_property(self):
        """Test: total_salary_increases cuenta aumentos correctamente"""
        # Crear aumentos
        self.employee.update_salary(Decimal('62000'), self.hr_user)
        self.employee.update_salary(Decimal('65000'), self.hr_user)
        
        # Crear reducción
        self.employee.update_salary(Decimal('63000'), self.hr_user)
        
        # Solo debe contar 2 aumentos
        self.assertEqual(self.employee.total_salary_increases, 2)
    
    def test_salary_growth_percentage_property(self):
        """Test: salary_growth_percentage calcula correctamente"""
        # Salario inicial: 60000
        initial = self.employee.current_salary
        
        # Primera actualización
        self.employee.update_salary(Decimal('66000'), self.hr_user)
        
        # Segunda actualización
        self.employee.update_salary(Decimal('72000'), self.hr_user)
        
        # Crecimiento: (72000 - 60000) / 60000 * 100 = 20%
        self.assertEqual(self.employee.salary_growth_percentage, 20.0)
    
    def test_salary_growth_percentage_no_history(self):
        """Test: salary_growth_percentage retorna 0 sin history"""
        # Empleado nuevo sin history
        new_user = User.objects.create_user(username='newuser', password='test123')
        new_employee = Employee.objects.create(
            user=new_user,
            role=self.dev_role,
            current_salary=50000,
            hire_date=date.today()
        )
        
        self.assertEqual(new_employee.salary_growth_percentage, 0)