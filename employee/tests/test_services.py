"""
Tests para services usando pytest
"""
import pytest;
from datetime import date, timedelta;
from django.contrib.auth.models import User;
from employee.models import Department, Role, Employee;
from employee.services import CompanyStatsService, DepartmentStatsService, HRActivityService;

# Fixtures - Datos reutilizables para tests
@pytest.fixture
def department_factory():
    """Factory para crear departamentos"""
    def create_department(name="Engineering", budget=100000):
        return Department.objects.create(
            name=name,
            budget=budget,
            description=f"{name} Department"
        )
    return create_department

@pytest.fixture
def role_factory():
    """Factory para crear roles"""
    def create_role(title="Developer", department=None):
        if department is None:
            department = Department.objects.create(name="Default Dept")
        return Role.objects.create(
            title=title,
            department=department,
            description=f"{title} role"
        )
    return create_role

@pytest.fixture
def employee_factory():
    """Factory para crear empleados"""
    def create_employee(username="testuser", seniority="JUNIOR", salary=50000, hire_date=None, role=None):
        if hire_date is None:
            hire_date = date.today()

        user = User.objects.create_user(
            username=username,
            first_name = "Test",
            last_name = "User",
            email=f"{username}@example.com"
        )

        if role is None:
            dept = Department.objects.create(name=f"Dept_{username}")
            role = Role.objects.create(title=f"Role_{username}", department=dept)

        return Employee.objects.create(
            user=user,
            role=role,
            seniority_level=seniority,
            current_salary=salary,
            hire_date=hire_date
        )
    return create_employee



# Tests de COMPANY STATS SERVICES.
@pytest.mark.django_db
class TestCompanyStatsService:
    """Test para CompanyStatsService"""
    
    def test_get_overview_empty_company(self):
        """Test con empresa vacia"""
        stats = CompanyStatsService.get_overview()

        assert stats['total_employee'] == 0
        assert stats['seniority_breakdown']['JUNIOR'] == 0
        assert stats['seniority_breakdown']['MID'] == 0
        assert stats['seniority_breakdown']['SENIOR'] == 0

    def test_get_overview_with_employees(self, employee_factory):
        """Test con varios empleados"""
        # Crear empleados de diferentes seniorities
        employee_factory(username="junior1", seniority="JUNIOR")
        employee_factory(username="junior2", seniority="JUNIOR")
        employee_factory(username="mid1", seniority="MID")
        employee_factory(username="senior1", seniority="SENIOR")

        stats = CompanyStatsService.get_overview()

        assert stats['total_employee'] == 4
        assert stats['seniority_breakdown']['JUNIOR'] == 2
        assert stats['seniority_breakdown']['MID'] == 1
        assert stats['seniority_breakdown']['SENIOR'] == 1

    def test_get_overview_excludes_teminated_employees(self, employee_factory):
        """Test que excluye empleados terminados"""
        # Empleado activo
        employee_factory(username="active")

        # Empleado terminado
        terminated = employee_factory(username="terminated")
        terminated.termination_date = date.today()
        terminated.save()

        stats = CompanyStatsService.get_overview()

        # Solo debe contar el empleado activo
        assert stats['total_employee'] == 1


# Tests de HR ACTIVITY SERVICE
@pytest.mark.django_db
class TestHRActivityService:
    """Tests para HRActivityService"""

    def test_get_recent_hires_empty(self):
        """Test sin contrataciones recientes"""
        result = HRActivityService.get_recent_hires()

        assert result['recent_hires_count'] == 0
        assert len(result['recent_hires']) == 0

    def test_get_recent_hires_within_period(self, employee_factory):
        """Test con contrataciones recientes"""
        # Empleado contratado hace 10 dias (reciente)
        recent_date = date.today() - timedelta(days=10)
        employee_factory(username="recent", hire_date=recent_date)

        # Empleado contratado hace 40 dias (no reciente)
        old_date = date.today() - timedelta(days=40)
        employee_factory(username="old", hire_date=old_date)

        result = HRActivityService.get_recent_hires()

        assert result['recent_hires_count'] == 1
        assert result['recent_hires'][0].user.username == "recent"

    def test_get_recent_hires_custom_days(self, employee_factory):
        """Test con periodo personalizado"""
        # Empleado contratado hace 5 dias
        recent_date = date.today() - timedelta(days=5)
        employee_factory(username="recent", hire_date=recent_date)

        # Test con 3 dias - no deberia aparecer
        result = HRActivityService.get_recent_hires(days=3)
        assert result['recent_hires_count'] == 0

        # Test con 7 dias - deberia aparecer
        result = HRActivityService.get_recent_hires(days=7)
        assert result['recent_hires_count'] == 1



# Tests de Department Stats Services
@pytest.mark.django_db
class TestDepartmentStatsService:
    """TEsts para DepartmentStatsService"""

    def test_get_overview_empty_departments(self):
        """Test sin departamentos"""
        stats = DepartmentStatsService.get_overview()
        assert len(stats) == 0

    def test_get_overview_with_employees(self, department_factory, role_factory, employee_factory):
        """Test con departamentos y empleados"""
        # Creamos departamentos con presupuesto
        dept = department_factory(name="Engineering", budget=200000)
        role = role_factory(title="Developer", department=dept)

        # Creamos empleados
        employee_factory(username="dev1", salary=80000, role=role)
        employee_factory(username="dev2", salary=90000, role=role)

        stats = DepartmentStatsService.get_overview()

        assert len(stats) == 1
        dept_stat = stats[0]

        assert dept_stat['name'] == 'Engineering'
        assert dept_stat['employee_count'] == 2
        assert dept_stat['total_budget'] == 200000
        assert dept_stat['total_salaries'] == 170000 # 80k + 90k

    def test_budget_calculation(self, department_factory, role_factory, employee_factory):
        """Test calculos de presupuesto"""
        dept = department_factory(budget=100000)
        role = role_factory(department=dept)

        # Empleado que usa 60% del presupuesto
        employee_factory(salary=60000, role=role)

        stats = DepartmentStatsService.get_overview()
        dept_stat = stats[0]

        assert dept_stat['salary_budget_percentage'] == 60.0
        assert dept_stat['remaining_budget'] == 40000



# Tests parametrizados - un test, multiples casos
@pytest.mark.django_db
@pytest.mark.parametrize("seniority,expected_count", [
    ("JUNIOR", 1),
    ("MID", 1),
    ("SENIOR", 1),
])
def test_seniority_counting(employee_factory, seniority, expected_count):
    """Test parametrizado para contar seniorities"""
    employee_factory(seniority=seniority)

    stats = CompanyStatsService.get_overview()
    assert stats['seniority_breakdown'][seniority] == expected_count