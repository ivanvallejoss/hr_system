"""
Forms para la app Employee
"""
from django import forms;
from django.core.exceptions import ValidationError;
from .models import Employee, Role;
from datetime import date, timedelta;
from decimal import Decimal;


class EmployeeProfilePictureForm(forms.ModelForm):
    """
    Form para actualizar la foto de perfil del empleado.
    Incluye validaciones de size y dimensiones.
    """

    class Meta:
        model = Employee
        fields = ['profile_picture']
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
                'id': 'profilePictureInput'
            })
        }
        labels = {
            'profile_picture': 'Choose new picture'
        }
    
    def clean_profile_picture(self):
        """
        Validacion custom del campo profile_picture
        Valida: size maximo, dimensiones minimos, formato
        """
        picture = self.cleaned_data.get('profile_picture')

        if not picture:
            # Si no se sube el archivo, retornamos None
            return picture
        
        # 1° Validacion para size maximo
        max_size = 2 * 1024 * 1024 # 2MB
        if picture.size > max_size:
            raise ValidationError(
                f'Image file is too large. Maximum size is 2MB.'
                f'Your file is {picture.size / (1024*1024):.1f}MB.'
            )
        
        # 2° Validacion para dimensiones (usamos Pillow)
        try:
            from PIL import Image
            img = Image.open(picture)

            min_width = 200
            min_height = 200

            if img.width < min_width or img.height < min_height:
                raise ValidationError(
                    f'Image dimensions are too small.'
                    f'Minimum size is {min_width}x{min_height} pixels.'
                    f'Your image is {img.width}x{img.height} pixels.'
                )
            
            # Verificamos que se pueda abrir la imagen
            img.verify()

        except Exception as e:
            # Si Pillow no puede abrir la image, no es valida
            raise ValidationError(
                f'Invalid image file. Please upload a valid JPG, PNG or WEBP image.'
            )
        
        return picture
    
    def save(self, commit=True):
        """
        Override del metodo save para manejar la eliminacion de la foto anterior
        """
        instance = super().save(commit=False)

        # Si hay una foto anterior y se esta subiendo una nueva, borramos la anterior
        if instance.pk: # Solo si es un update, no un create
            try:
                old_instance = Employee.objects.get(pk=instance.pk)
                if old_instance.profile_picture and old_instance.profile_picture != instance.profile_picture:
                    # Borramos el archivo anterior
                    old_instance.profile_picture.delete(save=False)
            except Employee.DoesNotExist:
                pass

        if commit:
            instance.save()
        
        return instance



class UpdateSalaryForm(forms.Form):
    """ 
    Form para actualizar el salario de un empleado

    Solo cambio de salary, el employee se pasa en la view
    Incluye effective_date y reason obligatorios.
    """

    new_salary = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter new salary',
            'step': '0.01'
        }),
        label='New Salary',
        help_text='Enter the new salary amount in USD'
    )

    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Effective Date',
        help_text='Date when the new salary takes effect.',
        initial=date.today
    )

    reason = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Annual perfomance raise. Promotion adjustment'
        }),
        label='Reason for Change',
        help_text='Provide a clear reason for this salary change'
    )

    def __init__(self, *args, employee=None, **kwargs):
        """ 
        Custom init para recibir el employee y validar contra el

        Args:
            employee: Employee instance para validaciones contextuales
        """
        super().__init__(*args, **kwargs)
        self.employee = employee

        # Si tenemos employee, mostrar salary actual en el help_text
        if employee:
            self.fields['new_salary'].help_text = (
                f"Current salary :${employee.current_salary:,.2f}."
                f"Enter the new salary amount."
            )

    def clean_new_salary(self):
        """Validaciones correspondientes al nuevo salario"""
        new_salary = self.cleaned_data.get('new_salary')
        current_salary = self.employee.current_salary

        if not self.employee:
            return new_salary
        
        # Validamos que el nuevo salario no sea el mismo que el anterior.
        if new_salary == current_salary:
            raise ValidationError(
                f'New salary must be different from current salary (${self.employee.current_salary:,.2f})'
            )
        
        # Validamos que el nuevo salario no sea numero negativo
        if new_salary <= 0:
            raise ValidationError(
                f'New salary cannot be negative or 0.'
            )
        
        return new_salary
    
    def clean_effective_date(self):
        """Validar que effective_date no sea antes de hire_date or today"""
        effective_date = self.cleaned_data.get('effective_date')

        if not self.employee:
            return effective_date
        
        if effective_date < self.employee.hire_date:
            raise ValidationError(
                f'Effective date cannot be before hire date ({self.employee.hire_date})'
            )
        
        todayDate = date.today()
        if effective_date < todayDate:
            raise ValidationError(
                f'Effective date cannot be before the present day ({todayDate})'
            )
        
        one_year_future = date.today() + timedelta(days=365)
        if effective_date > one_year_future:
            # Esto NO es un error pero, sirve como advertencia para validar 
            pass

        return effective_date
    
    def clean(self):
        """Validacion general del form"""
        cleaned_data = super().clean()

        new_salary = cleaned_data.get('new_salary')
        reason = cleaned_data.get('reason')

        # Validar que se proporcione razon detallada para cambios grandes
        if new_salary and self.employee:
            current = self.employee.current_salary
            change_pct = abs((new_salary - current) / current * 100)

            # Si el cambio es > 30%, la razon debe ser mas detallada
            if change_pct > 30 and reason and len(reason) < 20:
                self.add_error('reason',
                               'Please provide a more detailed reason for such a large salary change'
                               f'({change_pct:.1f}% change)'
                               )
                
        return cleaned_data
    

class UpdateRoleForm(forms.Form):
    """
    Form para actualizar rol y/o seniority de un empleado

    Permite cambiar role, seniority o ambas.
    """
    new_role = forms.ModelChoiceField(
        queryset=Role.objects.select_related('de[artment]').all(),
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='New Role',
        help_text='Select the new role for the employee.',
        required=False # Opcional si solo cambia seniority
    )

    new_seniority = forms.ChoiceField(
        choices=[('', '--- Keep Current ---')] + list(Employee._meta.get_field('seniority_level').choices),
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label='New Seniority Level',
        help_text='Select the new seniority level',
        required=False # Opcional si solo cambia role
    )

    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        label='Effective Date',
        help_text='Date when the change takes effect',
        initial=date.today
    )

    reason = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., Promotion to senior Level, Internal Transfer'
        }),
        label='Reason for change',
        help_text='Provide a clear reason for this role/seniority change'
    )

    def __init__(self, *args, employee=None, **kwargs):
        """ 
        Custom init para recibir el employee

        Args:
            employee: Employee instance
        """
        super().get__init__(*args, **kwargs)
        self.employee = employee

        # Si tenemos employee, mostrar valores actuales
        if employee:
            self.fields['new_role'].help_text = (
                f"Current role: {employee.role.title} ({employee.role.department.name})"
                f"Select new role."
            )
            self.fields['new_seniority'].help_text = (
                f"Current seniority: {employee.get_seniority_level_display()}."
                f"Select new seniority level."
            )

            # Pre-seleccionar valores actuales
            self.initial['new_role'] = employee.role.id
            self.initial['new_seniority'] = employee.seniority_level

    def clean(self):
        """Validar que haya al menos un cambio"""
        cleaned_data = super().clean()

        new_role = cleaned_data.get('new_role')
        new_seniority = cleaned_data.get('new_seniority')

        current_role = self.employee.role
        current_seniority = self.employee.seniority_level

        if not self.employee:
            return cleaned_data
        
        # Si no selecciono role, usar actual
        if not new_role:
            new_role = current_role
            cleaned_data['new_role'] = new_role

        # Si no selecciono seniority, usar actual
        if not new_seniority:
            new_seniority = current_seniority
            cleaned_data['new_seniority'] = new_seniority

        # Validamos que haya al menos un cambio.
        if new_role == current_role and new_seniority == current_seniority:
            raise ValidationError(
                'You must change either the role or the seniority level.'
                f'Current: {current_role.title} - {self.employee.get_seniority_level_display()}'
            )
        
        return cleaned_data
    
    def clean_effective_date(self):
        """Validar effective_date"""
        effective_date = self.cleaned_data.get('effective_date')
        todayDate = date.today()

        if not self.employee:
            return effective_date
        
        if effective_date < self.employee.hire_date:
            raise ValidationError(
                f'Effective date cannot be before hire date ({self.employee.hire_date})'
            )
        
        if effective_date < todayDate:
            raise ValidationError(
                f'Effective date cannot be before the present day ({todayDate})'
            )
        
        return effective_date