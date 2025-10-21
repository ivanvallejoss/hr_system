# employee/test_forms.py
"""
Tests para forms de Employee app
"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from employee.forms import EmployeeProfilePictureForm
from employee.models import Employee, Department, Role
from employee.test_utils import (
    create_test_image,
    create_oversized_image,
    create_small_image,
    create_invalid_file
)
from django.contrib.auth.models import User


class EmployeeProfilePictureFormTest(TestCase):
    """Tests para EmployeeProfilePictureForm"""
    
    def setUp(self):
        """Setup ejecutado antes de cada test"""
        # Crear objetos necesarios
        self.department = Department.objects.create(name="IT", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
        self.user = User.objects.create_user(username='testuser', password='test123')
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.role,
            current_salary=50000,
            hire_date='2024-01-01'
        )
    
    def test_form_with_valid_image(self):
        """Test: Form acepta imagen válida"""
        image = create_test_image(size=(300, 300))
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': image},
            instance=self.employee
        )
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.errors, {})
    
    def test_form_with_valid_png(self):
        """Test: Form acepta PNG válido"""
        image = create_test_image(
            name='test.png',
            format='PNG',
            content_type='image/png'
        )
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': image},
            instance=self.employee
        )
        
        self.assertTrue(form.is_valid())
    
    def test_form_with_valid_webp(self):
        """Test: Form acepta WEBP válido"""
        image = create_test_image(
            name='test.webp',
            format='WEBP',
            content_type='image/webp'
        )
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': image},
            instance=self.employee
        )
        
        self.assertTrue(form.is_valid())
    
    def test_form_rejects_oversized_image(self):
        """Test: Form rechaza imagen > 2MB"""
        oversized_image = create_oversized_image(size_mb=3)
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': oversized_image},
            instance=self.employee
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('profile_picture', form.errors)
        self.assertIn('too large', str(form.errors['profile_picture']).lower())
    
    def test_form_rejects_small_dimensions(self):
        """Test: Form rechaza imagen < 200x200px"""
        small_image = create_small_image(size=(100, 100))
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': small_image},
            instance=self.employee
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('profile_picture', form.errors)
        self.assertIn('too small', str(form.errors['profile_picture']).lower())
    
    def test_form_rejects_invalid_file_type(self):
        """Test: Form rechaza archivo no-imagen"""
        invalid_file = create_invalid_file()
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': invalid_file},
            instance=self.employee
        )
        
        self.assertFalse(form.is_valid())
        self.assertIn('profile_picture', form.errors)
    
    def test_form_accepts_minimum_dimensions(self):
        """Test: Form acepta exactamente 200x200px (límite mínimo)"""
        min_image = create_test_image(size=(200, 200))
        
        form = EmployeeProfilePictureForm(
            files={'profile_picture': min_image},
            instance=self.employee
        )
        
        self.assertTrue(form.is_valid())
    
    def test_form_without_file(self):
        """Test: Form es válido sin archivo (campo opcional)"""
        form = EmployeeProfilePictureForm(
            instance=self.employee
        )
        
        # Form vacío debería ser válido (campo opcional)
        self.assertTrue(form.is_valid())
    
    def test_form_save_deletes_old_picture(self):
        """Test: Al guardar nueva foto, borra la anterior"""
        # Subir primera foto
        first_image = create_test_image(name='first.jpg')
        self.employee.profile_picture = first_image
        self.employee.save()
        
        # Guardar path de la primera foto
        first_picture_path = self.employee.profile_picture.path
        
        # Subir segunda foto
        second_image = create_test_image(name='second.jpg')
        form = EmployeeProfilePictureForm(
            files={'profile_picture': second_image},
            instance=self.employee
        )
        
        self.assertTrue(form.is_valid())
        form.save()
        
        # Verificar que la nueva foto es diferente
        self.employee.refresh_from_db()
        self.assertNotEqual(self.employee.profile_picture.name, first_image.name)
        
        # Verificar que el archivo anterior fue borrado
        import os
        self.assertFalse(os.path.exists(first_picture_path))