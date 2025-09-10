"""
Mixins para control de permisos en Class-Based Views
"""

import logging
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin;
from django.contrib import messages;
from django.shortcuts import redirect;
from django.core.exceptions import PermissionDenied;
from django.http import Http404;
from django.urls import reverse_lazy;
from employee.models import Employee;

logger = logging.getLogger(__name__)

class EmployeeRequiredMixin(LoginRequiredMixin):
    """
    Mixin que requiere que el usuario tenga perfil de Employee activo
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        try:
            # Verificar que exista el perfil de empleado
            if not hasattr(request.user, 'employee'):
                logger.warning(f"User {request.user.username} tried to acess employee area without profile")
                messages.error(request, 'You need an employee profile to acess this area.')
                return redirect('login')
            
            # Verificar que el empleado esta activo.
            if not request.user.employee.is_active:
                logger.warning(f"Inactive employee {request.user.username} tried to access system")
                messages.error(request, 'Your employee account is not active.')
                return redirect('login')
            
        except Employee.DoesNotExist:
            logger.error(f"Employee profile missing for user {request.user.username}")
            messages.error(request, 'Employee profile not found.')
            return redirect('login')
        except Exception as e:
            logger.error(f"Error in EmployeeRequiredMixin: {str(e)}")
            messages.error(request, 'An error occurred during authentication.')
            return redirect('login')
        
        return super().dispatch(request, *args, **kwargs)
    


class GroupRequiredMixin(UserPassesTestMixin):
    """
    Mixin que requiere pertenencia a grupos especificos.
    """
    required_groups = []
    permission_denied_message = "You don't have permission to access this area."

    def test_func(self):
        if self.request.user.is_superuser:
            return True
        
        user_groups = set(self.request.user.groups.values_list('name', flat=True))
        required_groups = set(self.required_groups)

        has_permission = bool(user_groups.intersection(required_groups))

        if not has_permission:
            logger.warning(f"User {self.request.user.username} denied access. Required: {required_groups}, Has: {user_groups}")

        return has_permission
    
    def handle_no_permission(self):
        messages.error(self.request, self.permission_denied_message)
        return redirect('dashboards:home')
    

    
class HRRequiredMixin(GroupRequiredMixin):
    """
    Mixin especifico para usuarios de HR
    """
    required_groups = ['HR']
    permission_denied_message = "You need HR permissions to access this area."



class AdminRequiredMixin(GroupRequiredMixin):
    """
    Mixin especifico para administradores
    """
    required_groups = ['Admin']
    permission_denied_message = "You need administrator permissions to access this area."



class TeamLeadRequiredMixin(EmployeeRequiredMixin):
    """ Mixin que requiere que el usuario sea team lead """

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        # Si el super() dispatch no fue exitoso, retormarlo
        if hasattr(response, 'status_code') and response.status_code != 200:
            return response
        
        try:
            if not request.user.employee.is_team_lead:
                logger.warning(f"Non-team-lead {request.user.username} tried to access team lead area.")
                messages.error(request, 'You need to be a team lead to access this area.')
                return redirect('dashboards:employee_dashboard')
        
        except Exception as e:
            logger.error(f"Error in TeamLeadRequiredMixin: {str(e)}")
            messages.error(request, 'PErmission verification failed.')
            return redirect('dashboards:employee_dashboard')
        
        return response if hasattr(response, 'status_code') else super().dispatch(request, *args, **kwargs)
    


class SafeViewMixin:
    """
    Mixin que proporcniona manejo robusto de errores para CBVs
    """
    fallback_url = reverse_lazy('dashboards:home')

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except PermissionDenied:
            raise
        except Http404:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in {self.__class__.__name__}: {str(e)}", exc_info=True)
            messages.error(request, 'An unexpected error occured. Ivan has been notified.')
            return redirect(self.fallback_url)
        
    def get_context_data(self, **kwargs):
        try:
            return super().get_context_data(**kwargs)
        except Exception as e:
            logger.error(f"Error getting context data in {self.__class__.__name__}: {str(e)}")
            # Return minimal context to prevent complete failure
            return {'error_occurred': True}