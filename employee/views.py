import logging;
from django.views.generic import UpdateView;
from django.urls import reverse_lazy;
from django.contrib import messages;
from core.mixins import EmployeeRequiredMixin, SafeViewMixin;
from .models import Employee;
from .forms import EmployeeProfilePictureForm;

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