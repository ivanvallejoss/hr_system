"""
Tests para models de Employee app
"""

from django.test import TestCase;
from django.contrib.auth.models import User;
from django.core.exceptions import ValidationError;
from datetime import date;
from employee.models import Department, Role, Employee;


class DepartmentModelTest(TestCase):
    """Tests para el model Department"""

    def setUp(self):
        """Metodo que se ejecuta antes de cada test"""
        self.department = Department.objects.create(
            name="Engineering",
            description="Software development team",
            budget=100000.00
        )

    def test_department_creation(self):
        """Test basico: crear un departamento"""
        # Verificar que el departamento se creo correctamente
        self.assertEqual(self.department.name, "Engineering")
        self.assertEqual(self.department.budget, 100000.00)
        self.assertIsNotNone(self.department.created_at)

    def test_department_string_representation(self):
        """Test del metodo __str__"""
        self.assertEqual(str(self.department), "Engineering")

    def test_department_unique_name(self):
        """Test que el nombre del departamento es unico"""
        with self.assertRaises(Exception): # Deberia fallar
            Department.objects.create(name="Engineering")

    
class EmployeeModelTest(TestCase):
    """Tests para el modelo Employee"""

    def setUp(self):
        """Preparar datos para cada test"""

        # Crear departamento y Rol
        self.department = Department.objects.create(
            name="IT",
            budget=50000.00
        )
        self.role = Role.objects.create(
            title="Software Developer",
            department=self.department
        )

        # Crear usuario
        self.user = User.objects.create(
            username="testuser",
            first_name="Juancito",
            last_name="Perez",
            email="juancito@example.com"
        )

        # Crear empleado
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.role,
            seniority_level="MID",
            current_salary=75000.00,
            hire_date=date(2023, 1, 15)
        )

    def test_employee_creation(self):
        """Test basico de creacion de empleado"""
        self.assertEqual(self.employee.user.username, "testuser")
        self.assertEqual(self.employee.role.title, "Software Developer")
        self.assertEqual(self.employee.seniority_level, "MID")
        self.assertEqual(self.employee.current_salary, 75000.00)

    def test_employee_is_active_property(self):
        """Test de la propiedad is_active"""
        # Empleado sin fecha de terminacion deberia estar activo
        self.assertTrue(self.employee.is_active)

        # Empleado con fecha de terminacion no deberia estar activo
        self.employee.termination_date = date.today()
        self.assertFalse(self.employee.is_active)

    def test_employee_full_name_property(self):
        """Test de la propiedad full_name"""
        expected_name = "Juancito Perez"
        self.assertEqual(self.employee.full_name, expected_name)

        # Test con usuario sin first_name/last_name
        user_no_name = User.objects.create_user(username="noname")
        employee_no_name = Employee.objects.create(
            user=user_no_name,
            role=self.role,
            current_salary=50000.00,
            hire_date=date.today()
        )
        self.assertEqual(employee_no_name.full_name, "noname")

    def test_employee_is_team_lead_property(self):
        """Test de la propiedad is_team_lead"""
        # Inicialmente no deberia ser team lead
        self.assertFalse(self.employee.is_team_lead)

        # Crear un subordinado para convertirlo en team lead
        subordinate_user = User.objects.create_user(username="subordinate")
        Employee.objects.create(
            user=subordinate_user,
            role=self.role,
            manager=self.employee,
            current_salary=60000.00,
            hire_date=date.today()
        )

        # Ahora deberia ser team lead
        self.assertTrue(self.employee.is_team_lead)

    def test_employee_string_representation(self):
        """Test del metodo __str__"""
        expected_str = "Juancito Perez - Software Developer"
        self.assertEqual(str(self.employee), expected_str)