"""
Forms para la app Employee
"""
from django import forms;
from django.core.exceptions import ValidationError;
from .models import Employee;


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
