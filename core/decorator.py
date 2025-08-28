"""
Decorators para control de permisos y manejo de errores
"""

import logging
from functools import wraps;
from django.contrib.auth.decorators import login_required;
from django.contrib import messages;
from django.shortcuts import redirect;
from django.core.exceptions import PermissionDenied;
from django.http import Http404;
from employee.models import Employee;

logger = logging.getLogger(__name__)

def employee_required(view_func):
    """
    Decorator que requiere que el usuario tenga perfil de Employee
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            # Verificar que el usuario tiene perfil de empleado
            if not hasattr(request.user, 'employee'):
                logger.warning(f"User {request.user.username} tried to access employee area without profile")
                messages.error(request, 'You need an employee profile to access this area.')
                return redirect('login')
            
            # Verificar que el empleado esta activo
            if not request.user.employee.is_active:
                logger.warning(f"Inactive employee {request.user.username} tried to access system")
                messages.error(request, 'Your employee account is not active.')
                return redirect('login')
            
            return view_func(request, *args, **kwargs)
        
        except Employee.DoesNotExist:
            logger.error(f"Employee profile missing for user {request.user.username}")
            messages.error(request, 'Employee profile not found.')
            return redirect('login')
        except Exception as e:
            logger.error(f"Unexpected error in employee_required: {str(e)}")
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('login')
    
    return _wrapped_view



def group_required(*group_name):
    """
    Decorator que requiere que el usuario pertenezca a uno de los grupo especificados.
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            try:
                user_groups = set(request.user.groups.values_list('name', flat=True))
                required_groups = set(group_names)

                # Superuser siempre tiene acceso
                if request.user.is_superuser:
                    return view_func(request, *args, **kwargs)
                
                # Verificar si el usuario pertenece a alguno de los grupos.
                if not user_groups.intersection(required_groups):
                    logger.warning(f"User {request.user.username} denied access. Required: {required_groups}, Has: {user_groups}")
                    raise PermissionDenied(f"Access denied. Required groups: {', '.join(group_names)}")
                
                return view_func(request, *args, **kwargs)
            
            except PermissionDenied:
                raise # Re-raise PermissionDenied
            except Exception as e:
                logger.error(f"Error in group_required decorator: {str(e)}")
                messages.error(request, 'Permission verification failed.')
                return redirect('login')
        
        return _wrapped_view
    return decorator



def team_lead_required(view_func):
    """
    Decorator que requiere que el usuario sea team lead
    """
    @wraps(view_func)
    @employee_required
    def _wrapped_view(request, *args, **kwargs):
        try:
            if not request.user.employee.is_team_lead:
                logger.warning(f"Non-team-lead {request.user.username} tried to access team lead area.")
                messages.error(request, 'You need to be a team lead to access this area.')
                return redirect('dashboards:employee_dashboard')
            
            return view_func(request, *args, **kwargs)

        except Exception as e:
            logger.error(f"Error in team_lead_required: {str(e)}")
            messages.error(request, 'Permission verification failed.')
            return redirect('dashboards:employee_dashboard')
        
    return _wrapped_view



def safe_view(fallback_redirect='dashboards:home'):
    """
    Decorator que proporciona manejo robusto de errores para views
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except PermissionDenied:
                raise # PermissionDenied para que Django lo maneje
            except Http404:
                raise # Http404 para que Django lo maneje
            except Exception as e:
                logger.error(f"Unexpected error in {view_func.__name__}: {str(e)}", exc_info=True)
                messages.error(request, 'An unexpected error occurred. The IT teams has been notified.')
                return redirect(fallback_redirect)
        
        return _wrapped_view
    return decorator