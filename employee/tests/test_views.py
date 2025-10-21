# employee/test_views.py
"""
Tests para views de Employee app
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from employee.models import Employee, Department, Role
from employee.test_utils import (
    create_test_image,
    create_oversized_image,
    create_small_image
)


class UpdateProfilePictureViewTest(TestCase):
    """Tests para UpdateProfilePictureView"""
    
    def setUp(self):
        """Setup ejecutado antes de cada test"""
        self.client = Client()
        
        # Crear objetos necesarios
        self.department = Department.objects.create(name="Engineering", budget=100000)
        self.role = Role.objects.create(title="Developer", department=self.department)
        
        self.user = User.objects.create_user(
            username='testemployee',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )
        
        self.employee = Employee.objects.create(
            user=self.user,
            role=self.role,
            seniority_level='MID',
            current_salary=75000,
            hire_date='2023-01-15'
        )
        
        self.url = reverse('employee:update_profile_picture')
    
    def test_view_requires_login(self):
        """Test: View requiere autenticación"""
        response = self.client.get(self.url)
        
        # Debe redirigir a login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)
    
    def test_view_requires_employee_profile(self):
        """Test: View requiere perfil de empleado"""
        # Crear usuario sin perfil de empleado
        user_no_profile = User.objects.create_user(
            username='noprofile',
            password='test123'
        )
        
        self.client.login(username='noprofile', password='test123')
        response = self.client.get(self.url)
        
        # Debe redirigir a login con mensaje de error
        self.assertEqual(response.status_code, 302)
        
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('employee profile' in str(m).lower() for m in messages))
    
    def test_view_get_loads_form(self):
        """Test: GET request carga el form correctamente"""
        self.client.login(username='testemployee', password='testpass123')
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'employee/update_profile_picture.html')
        self.assertIn('form', response.context)
        self.assertIn('employee', response.context)
    
    def test_upload_valid_image_success(self):
        """Test: Upload de imagen válida funciona correctamente"""
        self.client.login(username='testemployee', password='testpass123')
        
        image = create_test_image(size=(300, 300))
        
        response = self.client.post(self.url, {
            'profile_picture': image
        }, format='multipart')
        
        # Debe redirigir al dashboard
        self.assertRedirects(response, reverse('dashboards:employee_dashboard'))
        
        # Debe mostrar mensaje de éxito
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('success' in str(m).lower() for m in messages))
        
        # Empleado debe tener foto
        self.employee.refresh_from_db()
        self.assertTrue(self.employee.profile_picture)
    
    def test_upload_oversized_image_fails(self):
        """Test: Upload de imagen muy grande falla con error"""
        self.client.login(username='testemployee', password='testpass123')
        
        oversized = create_oversized_image(size_mb=3)
        
        response = self.client.post(self.url, {
            'profile_picture': oversized
        }, format='multipart')
        
        # No debe redirigir (re-renderiza form con errores)
        self.assertEqual(response.status_code, 200)
        
        # Debe mostrar mensaje de error
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('error' in str(m).lower() for m in messages))
        
        # Form debe tener errores
        self.assertFormError(response.context['form'], 'profile_picture', [])
        # (el error específico está en form.errors)
        
        # Empleado NO debe tener foto
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.profile_picture)
    
    def test_upload_small_image_fails(self):
        """Test: Upload de imagen muy pequeña falla con error"""
        self.client.login(username='testemployee', password='testpass123')
        
        small_image = create_small_image(size=(100, 100))
        
        response = self.client.post(self.url, {
            'profile_picture': small_image
        }, format='multipart')
        
        # No debe redirigir
        self.assertEqual(response.status_code, 200)
        
        # Empleado NO debe tener foto
        self.employee.refresh_from_db()
        self.assertFalse(self.employee.profile_picture)
    
    def test_update_existing_picture(self):
        """Test: Actualizar foto existente funciona correctamente"""
        self.client.login(username='testemployee', password='testpass123')
        
        # Subir primera foto
        first_image = create_test_image(name='first.jpg')
        self.employee.profile_picture = first_image
        self.employee.save()
        
        first_picture_name = self.employee.profile_picture.name
        
        # Subir segunda foto
        second_image = create_test_image(name='second.jpg')
        response = self.client.post(self.url, {
            'profile_picture': second_image
        }, format='multipart')
        
        self.assertRedirects(response, reverse('dashboards:employee_dashboard'))
        
        # Foto debe haber cambiado
        self.employee.refresh_from_db()
        self.assertNotEqual(self.employee.profile_picture.name, first_picture_name)
    
    def test_user_can_only_update_own_picture(self):
        """Test: Usuario solo puede actualizar su propia foto (seguridad)"""
        # Crear segundo empleado
        other_user = User.objects.create_user(
            username='otheruser',
            password='test123'
        )
        other_employee = Employee.objects.create(
            user=other_user,
            role=self.role,
            current_salary=50000,
            hire_date='2024-01-01'
        )
        
        # Loguearse como primer usuario
        self.client.login(username='testemployee', password='testpass123')
        
        # Intentar subir foto (siempre actualiza al usuario logueado)
        image = create_test_image()
        response = self.client.post(self.url, {
            'profile_picture': image
        }, format='multipart')
        
        self.assertRedirects(response, reverse('dashboards:employee_dashboard'))
        
        # Verificar que solo el usuario logueado tiene foto
        self.employee.refresh_from_db()
        other_employee.refresh_from_db()
        
        self.assertTrue(self.employee.profile_picture)
        self.assertFalse(other_employee.profile_picture)