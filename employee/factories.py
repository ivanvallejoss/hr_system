"""
Factories para generar datos de prueba usando Factory Boy
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from datetime import date, timedelta
import random

from .models import Department, Role, Employee
from core.constants import SENIORITY_LEVELS

fake = Faker()

# ==========================================
# USER & AUTH FACTORIES
# ==========================================

class GroupFactory(DjangoModelFactory):
    """Factory para grupos de usuarios"""
    class Meta:
        model = Group
        django_get_or_create = ('name',)  # No duplicar grupos
    
    name = factory.Iterator(['Admin', 'HR', 'Employee'])


class UserFactory(DjangoModelFactory):
    """Factory para usuarios de Django"""
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@company.com")
    is_active = True
    is_staff = False
    is_superuser = False
    
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        """Asignar password por defecto"""
        if create:
            obj.set_password('testpass123')
            obj.save()
    
    @factory.post_generation
    def groups(obj, create, extracted, **kwargs):
        """Asignar grupos si se especifican"""
        if not create:
            return
        
        if extracted:
            for group in extracted:
                obj.groups.add(group)
    
    class Params:
        # Trait para crear superuser
        is_admin = factory.Trait(
            is_staff=True,
            is_superuser=True,
            username=factory.Sequence(lambda n: f"admin{n}")
        )
        
        # Trait para usuario HR
        is_hr = factory.Trait(
            username=factory.Sequence(lambda n: f"hr_user{n}")
        )


# ==========================================
# EMPLOYEE APP FACTORIES
# ==========================================

class DepartmentFactory(DjangoModelFactory):
    """Factory para departamentos"""
    class Meta:
        model = Department
        django_get_or_create = ('name',)
    
    name = factory.Iterator([
        'Engineering',
        'Human Resources', 
        'Sales',
        'Marketing',
        'Finance',
        'Operations',
        'Product',
        'Customer Success'
    ])
    description = factory.LazyAttribute(
        lambda obj: f"{obj.name} department handling related operations"
    )
    budget = factory.Faker('random_int', min=50000, max=500000, step=10000)
    department_manager = None  # Se asignará después


class RoleFactory(DjangoModelFactory):
    """Factory para roles"""
    class Meta:
        model = Role
    
    title = factory.Faker('job')
    department = factory.SubFactory(DepartmentFactory)
    description = factory.LazyAttribute(
        lambda obj: f"Responsible for {obj.title.lower()} tasks in {obj.department.name}"
    )


class EmployeeFactory(DjangoModelFactory):
    """Factory para empleados con múltiples traits"""
    class Meta:
        model = Employee
    
    user = factory.SubFactory(UserFactory)
    role = factory.SubFactory(RoleFactory)
    seniority_level = 'JUNIOR'
    current_salary = factory.Faker('random_int', min=50000, max=70000)
    hire_date = factory.LazyFunction(
        lambda: date.today() - timedelta(days=random.randint(30, 1095))
    )
    termination_date = None
    manager = None
    profile_picture = None
    
    class Params:
        # Trait para empleado Junior
        is_junior = factory.Trait(
            seniority_level='JUNIOR',
            current_salary=factory.Faker('random_int', min=50000, max=70000)
        )
        
        # Trait para empleado Mid
        is_mid = factory.Trait(
            seniority_level='MID',
            current_salary=factory.Faker('random_int', min=70000, max=100000)
        )
        
        # Trait para empleado Senior
        is_senior = factory.Trait(
            seniority_level='SENIOR',
            current_salary=factory.Faker('random_int', min=100000, max=150000)
        )
        
        # Trait para empleado recién contratado (últimos 30 días)
        recently_hired = factory.Trait(
            hire_date=factory.LazyFunction(
                lambda: date.today() - timedelta(days=random.randint(1, 30))
            )
        )
        
        # Trait para empleado antiguo
        is_veteran = factory.Trait(
            hire_date=factory.LazyFunction(
                lambda: date.today() - timedelta(days=random.randint(1095, 3650))
            )
        )
        
        # Trait para empleado terminado
        is_terminated = factory.Trait(
            termination_date=factory.LazyFunction(
                lambda: date.today() - timedelta(days=random.randint(1, 180))
            )
        )

        with_picture = factory.Trait(
            profile_picture=factory.LazyFunction(
                lambda: SimpleUploadedFile(
                    name='test_profile.jpg',
                    content=b'fake_image_content',
                    content_type='image/jpg'
                )
            )
        )
