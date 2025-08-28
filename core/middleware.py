"""
Custom middleware for the HR system
"""
import logging
from django.http import HttpResponseRedirect;
from django.contrib import messages;
from django.urls import reverse;
from employee.models import Employee;

logger = logging.getLogger(__name__)

class EmployeeProfileMiddleware:
    """
    Middleware que verifica que usuarios autenticados tengan perfil de empleado
    Excepto superusers y rutas especificas
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # Rutas que no requieren perfil de empleado
        self.excluded_paths = [
            '/admin/',
            '/accounts/',
            '/logout/',
            reverse('dashboards:admin_dashboard'),
        ]

    def __call__(self, request):
        # Solo verificar para usuarios autenticados
        if request.user.is_authenticated and not request.user.is_superuser:
            # Verificar si la ruta actual esta excluida
            path_excluded = any(request.path.startswith(path) for path in self.excluded_paths)

            if not path_excluded:
                try:
                    # Verificar que el usuario tiene el perfil de empleado activo.
                    if not hasattr(request.user, 'employee'):
                        logger.warning(f"User {request.user.username} without employee profile tried to access {request.path}")
                        messages.error(request, 'You need an employee profile to access the system.')
                        return HttpResponseRedirect(reverse('login'))
                    
                    if not request.user.employee.is_active:
                        logger.warning(f"Inactive employee {request.user.username} tried to access {request.path}")
                        messages.error(request, 'Your employee account is not active.')
                        return HttpResponseRedirect(reverse('login'))
                    
                except Employee.DoesNotExist:
                    logger.error(f"Employee DoesNotExist for user {request.user.username}")
                    messages.error(request, 'Employee profile not found.')
                    return HttpResponseRedirect(reverse('login'))
                except Exception as e:
                    logger.error(f"Error in EmployeeProfileMiddleware: {str(e)}")
                    # No bloquear en caso de error inesperado, pero registrarlo
                    pass
            
        response = self.get_response(request)
        return response
    
class SecurityHeadersMiddleware:
    """
    Middleware que agrega headers de seguridad
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Agregar headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; model=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'

        return response