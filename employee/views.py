import logging;
from django.shortcuts import redirect, get_object_or_404;
from django.views.generic import UpdateView, FormView, ListView;
from django.urls import reverse_lazy, reverse;
from django.core.exceptions import ValidationError;
from core.decorator import group_required;
from django.utils.decorators import method_decorator;
from django.contrib import messages;
from core.mixins import EmployeeRequiredMixin, SafeViewMixin;
from .models import Employee;
from .forms import EmployeeProfilePictureForm, UpdateRoleForm, UpdateSalaryForm;

logger = logging.getLogger(__name__)


class UpdateProfilePictureView(SafeViewMixin, EmployeeRequiredMixin, UpdateView):
    """
    View para actualizar la foto de perfil del empleado.
    Solo el propio empleado puede actualizar su foto.
    """
    model = Employee
    form_class = EmployeeProfilePictureForm
    template_name = 'employee/update_profile_picture.html'
    success_url = reverse_lazy('dashboards:employee_dashboard')
    fallback_url = reverse_lazy('dashboards:employee_dashboard')

    def get_object(self, queryset=None):
        """
        Retorna el empleado del usuario logueado.
        Esto previene que un usuario edite la foto de otro.
        """
        return self.request.user.employee
    
    def form_valid(self, form):
        """
        Callback cuando el form es valido.
        Agregamos mensaje de exito y logging.
        """
        logger.info(f"User {self.request.user.username} updated profile picture")
        messages.success(self.request, 'V Profile picture updated successfuly!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """
        Callback cuando el form tiene errores
        """
        messages.error(self.request, 'Please correct the error below.')
        return super().form_invalid(form)
    



#
#  SALARY AND ROLE UDPATES
#       HR VIEWS
#

@method_decorator(group_required('HR'), name='dispatch')
class UpdateEmployeeSalaryView(SafeViewMixin, FormView):
    """
    View para que HR actualice el salario de un empleado
    
    Requiere:
    - Grupo HR o superuser (convencion Django)
    - Employee ID en URL
    
    Usa employee.update_salary() para registrar en history
    """
    template_name = 'employee/update_salary.html'
    form_class = UpdateSalaryForm
    fallback_url = reverse_lazy('dashboards:hr_dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Cargar el employee antes de procesar"""
        self.employee = get_object_or_404(
            Employee.objects.select_related('user', 'role', 'role__department'),
            pk=self.kwargs['pk']
        )
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Pasar el employee al form"""
        kwargs = super().get_form_kwargs()
        kwargs['employee'] = self.employee
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Agregar employee y su history al contexto"""
        context = super().get_context_data(**kwargs)
        context['employee'] = self.employee
        
        # Últimos 5 cambios de salary
        context['recent_salary_history'] = self.employee.salary_history.all()[:5]
        
        return context
    
    def form_valid(self, form):
        """Procesar el form válido"""
        try:
            # Usar el helper method del modelo
            history = self.employee.update_salary(
                new_salary=form.cleaned_data['new_salary'],
                changed_by=self.request.user,
                reason=form.cleaned_data['reason'],
                effective_date=form.cleaned_data['effective_date']
            )
            
            logger.info(
                f"HR user {self.request.user.username} updated salary for "
                f"{self.employee.full_name}: ${history.old_salary} → ${history.new_salary}"
            )
            
            messages.success(
                self.request,
                f'✓ Salary updated successfully for {self.employee.full_name}. '
                f'Change: ${history.old_salary:,.2f} → ${history.new_salary:,.2f} '
                f'({history.change_percentage:+.1f}%)'
            )
            
            return redirect('dashboards:hr_dashboard')
        
        except ValidationError as e:
            logger.error(f"Validation error updating salary: {e}")
            messages.error(self.request, f'Error: {e.message}')
            return self.form_invalid(form)
        
        except Exception as e:
            logger.exception(f"Unexpected error updating salary: {e}")
            messages.error(
                self.request,
                'An unexpected error occurred while updating the salary. '
                'Please try again or contact support.'
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Redirigir al HR dashboard"""
        return reverse('dashboards:hr_dashboard')


@method_decorator(group_required('HR'), name='dispatch')
class UpdateEmployeeRoleView(SafeViewMixin, FormView):
    """
    View para que HR actualice el rol/seniority de un empleado
    
    Requiere:
    - Grupo HR
    - Employee ID en URL
    
    Usa employee.update_role() para registrar en history
    """
    template_name = 'employee/update_role.html'
    form_class = UpdateRoleForm
    fallback_url = reverse_lazy('dashboards:hr_dashboard')
    
    def dispatch(self, request, *args, **kwargs):
        """Cargar el employee antes de procesar"""
        self.employee = get_object_or_404(
            Employee.objects.select_related('user', 'role', 'role__department'),
            pk=self.kwargs['pk']
        )
        return super().dispatch(request, *args, **kwargs)
    
    def get_form_kwargs(self):
        """Pasar el employee al form"""
        kwargs = super().get_form_kwargs()
        kwargs['employee'] = self.employee
        return kwargs
    
    def get_context_data(self, **kwargs):
        """Agregar employee y su history al contexto"""
        context = super().get_context_data(**kwargs)
        context['employee'] = self.employee
        
        # Últimos 5 cambios de role
        context['recent_role_history'] = self.employee.role_history.all()[:5]
        
        return context
    
    def form_valid(self, form):
        """Procesar el form válido"""
        try:
            # Usar el helper method del modelo
            history = self.employee.update_role(
                new_role=form.cleaned_data['new_role'],
                new_seniority=form.cleaned_data['new_seniority'],
                changed_by=self.request.user,
                reason=form.cleaned_data['reason'],
                effective_date=form.cleaned_data['effective_date']
            )
            
            logger.info(
                f"HR user {self.request.user.username} updated role for "
                f"{self.employee.full_name}: {history.old_role}/{history.old_seniority} → "
                f"{history.new_role}/{history.new_seniority}"
            )
            
            # Mensaje personalizado según tipo de cambio
            promotion_or_demotion = history.promotion_or_demotion # Devuelve string con promotion/demotion dependiendo el cambio o None si no es ninguno 
            if promotion_or_demotion:
                message_icon = '🎉' if promotion_or_demotion == 'promotion' else ':(' 
                change_type = promotion_or_demotion
            elif history.is_lateral_move:
                message_icon = '↔️'
                change_type = 'Role change'
            else:
                message_icon = '✓'
                change_type = 'Role/seniority updated'
            
            messages.success(
                self.request,
                f'{message_icon} {change_type} successful for {self.employee.full_name}. '
                f'{history.old_role.title}/{history.old_seniority} → '
                f'{history.new_role.title}/{history.new_seniority}'
            )
            
            return redirect('dashboards:hr_dashboard')
        
        except ValidationError as e:
            logger.error(f"Validation error updating role: {e}")
            messages.error(self.request, f'Error: {e.message}')
            return self.form_invalid(form)
        
        except Exception as e:
            logger.exception(f"Unexpected error updating role: {e}")
            messages.error(
                self.request,
                'An unexpected error occurred while updating the role. '
                'Please try again or contact support.'
            )
            return self.form_invalid(form)
    
    def get_success_url(self):
        """Redirigir al HR dashboard"""
        return reverse('dashboards:hr_dashboard')

#
#  View de Busqueda
# 

from django.views.generic import ListView;
from django.db.models import Q

@method_decorator(group_required('HR'), name='dispatch')
class EmployeeSearchView(SafeViewMixin, ListView):
    """
    View para buscar empleados

    Permite a HR buscar empleados nombre o username
    y acceder a las opciones de actualizacion
    """
    model = Employee
    template_name = 'employee/employee_search.html'
    context_object_name = 'employees'
    paginate_by = 9
    fallback_url = reverse_lazy('dashboards:hr_dashboard')

    def get_queryset(self):
        """ 
        Retorna empleados activos, filtrados por busqueda si existe
        """
        queryset = Employee.objects.select_related(
            'user', 'role', 'role__department'
        ).filter(
            termination_date__isnull=True
        ).order_by('user__last_name', 'user__first_name')

        # Obtenemos la query de busqueda
        query = self.request.GET.get('q', '').strip()

        if query:
            # Buscamos por nombre, apellido o username
            queryset = queryset.filter(
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(user__username__icontains=query) 
            )

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        # Utilizamos el paginator.
        # Para hacer el conteo del total de empleados activos.
        if context.get('is_paginated'):
            context['total_results'] = context['paginator'].count
        else:
            # Esto ejecuta el queryset ya ejecutado, posible N+1 queries
            context['total_results'] = len(context['employees'])
        
        return context