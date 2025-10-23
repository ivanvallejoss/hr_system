from django.db import models;
from django.contrib.auth.models import User;
from django.core.validators import FileExtensionValidator;
from core.models import TimeStampedModel;
from core.constants import SENIORITY_LEVELS;
from .managers import SalaryHistoryManager, RoleHistoryManager, EmployeeQuerySet;
import logging;

logger = logging.getLogger(__name__)


class Department(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    department_manager = models.ForeignKey(
        'Employee',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_department'
    )
    budget = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.name
    
    
class Role(TimeStampedModel):
    title = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} - {self.department.name}"
    
    
class Employee(TimeStampedModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    seniority_level = models.CharField(
        max_length=10,
        choices=SENIORITY_LEVELS,
        default='JUNIOR'
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members'
    )
    current_salary = models.DecimalField(max_digits=10, decimal_places=2)
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    profile_picture = models.ImageField(
        upload_to='employee_profiles/%Y/%m/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'webp']
            )
        ],
        help_text="Profile Picture (JPG, PNG, WEBP). Max 2MB recommended."
    )
    objects = models.Manager.from_queryset(EmployeeQuerySet)()

    def update_salary(self, new_salary, changed_by, reason='', effective_date=None):
        """
        Actualiza el salario del empleado y registra el cambio en history

        Args:
            new_salary (Decimal): Nuevo Salario
            changed_by (User): Usuario que realizo el cambio
            reason (str): Razon del cambio
            effective_date (date): Fecha efectiva del cambio (default: hoy)

        Returns:
            SalaryHistory: Registro del cambio creado

        Raises:
            ValidationError: Si new_salary es invalido
        
        Example:
            >>> employee.update_salary(
            ... new_salary=85000,
            ... changed_by=hr_user,
            ... reason="Annual perfomance raise",
            ... effective_date=date(2025, 1, 1)
            ... )
        """
        from datetime import date

        if effective_date is None:
            effective_date = date.today()

        # Creamos registro de history
        history = SalaryHistory(
            employee=self,
            old_salary=self.current_salary,
            new_salary=new_salary,
            changed_by=changed_by,
            change_reason=reason,
            effective_date=effective_date
        )
        
        # Validamos el history record
        history.full_clean()

        # Guardamos el history primero (por si falla)
        history.save()

        # Actualizamos el salario actual.
        old_salary = self.current_salary
        self.current_salary = new_salary
        self.save(update_fields=['current_salary', 'updated_at'])

        logger.info(
            f"Salary updated for {self.full_name}: "
            f"${old_salary} -> ${new_salary} by {changed_by.username}"
        )

        return history
    
    def update_role(self, new_role=None, new_seniority=None, changed_by=None, reason='', effective_date=None):
        """
        Actualiza el rol y/o seniority del empleado y registra el cambio

        Args:
            new_role (Role, optional): Nuevo rol
            new_seniority (str, optional): Nuevo nivel del seniority
            changed_by (User): Usuario que realiza el cambio
            reason (str): Razon del cambio
            effective_date (date): Fecha efectiva (default: hoy)

        Returns:
            RoleHistory: REgistro del cambio creado
        
        Raises:
            ValidationError: Si no hay cambios o los valores son invalidos

        Example:
            >>> # Promocion a senior
            >>> employee.update_role(
            ... new_seniority='SENIOR',
            ... changed_by=manager,
            ... reason="Promotion after excellent performance review"
            ... )

            >>> # Cambio de role y seniority
            >>> employee.update_role(
            ... new_role=tech_lead_role,
            ... new_seniority='SENIOR',
            ... changed_by=hr_user,
            ... reason="Promoted to Tech Lead"
            ... )
        """
        from datetime import date;
    
        if effective_date is None:
            effective_date = date.today()

        # Si no se especifica, mantener valores actuales.
        if new_role is None:
            new_role = self.role
        if new_seniority is None:
            new_seniority = self.seniority_level

        # Creamos el registro de history
        history = RoleHistory(
            employee=self,
            old_role=self.role,
            new_role=new_role,
            old_seniority=new_seniority,
            changed_by=changed_by,
            change_reason=reason,
            effective_date=effective_date
        )

        # Validamos el history record
        history.full_clean()

        # Guardamos history
        history.save()

        # Actualizar employee
        old_role = self.role
        old_seniority = self.seniority_level

        self.role = new_role
        self.seniority_level = new_seniority
        self.save(update_fields=['role', 'seniority_level', 'updated_at'])

        logger.info(
            f"Role updated for {self.full_name}"
            f"{old_role.title}/{old_seniority} -> {new_role.title}/{new_seniority}"
            f"by {changed_by.username if changed_by else 'system'}"
        )

        return history


    def get_salary_history(self, start_date=None, end_date=None):
        """ 
        Obtiene el historial de salarios del empleado

        Args:
            start_date (date, optional): Fecha de inicio del filtro.
            end_date (date, optional): Fecha de fin del filtro

        Returns:
            QuerySet[SalaryHistory]: Historial filtrado y ordenado

        Example:
            >>> # ultimo 6 meses
            >>> from datetime import date, timedelta
            >>> six_monts_ago = date.today() - timedelta(days=180)
            >>> employee.get_salary_history(start_date=six_monts_ago)
        """
        history = self.salary_history.all()

        if start_date:
            history = history.filter(effective_date__gte=start_date)

        if end_date:
            history = history.filter(effective_date__lte=end_date)

        return history
    

    def get_role_history(self, start_date=None, end_date=None):
        """ 
        Obtiene el historial de roles del empleado

        Args:
            start_date (date, optional): Fecha de inicio del filtro.
            end_date (date, optional): Fecha de fin del filtro

        Returns:
            QuerySet[RoleHistory]: Historial filtrado y ordenado
        """
        history = self.role_history.all()

        if start_date:
            history = history.filter(effective_date__gte=start_date)

        if end_date:
            history = history.filter(effective_date__lte=end_date)

        return history
    
    @property
    def total_salary_increases(self):
        """Total de aumentos de salarios recibidos"""
        return self.salary_history.filter(new_salary__gt=models.F('old_salary')).count()
    
    @property
    def total_promotions(self):
        """Total de promociones (aumento de seniority)"""
        return self.role_history.filter(
            new_seniority__in=['MID', 'SENIOR'],
            old_seniority__in=['JUNIOR', 'MID']
        ).count()
    
    @property
    def salary_growth_percentage(self):
        """ 
        Crecimiento salarial total desde el primer registro.

        Returns:
            float: Porcentaje de crecimiento o 0 si no hay history
        """
        first_history = self.salary_history.order_by('effective_date').first()

        if not first_history:
            return 0
        
        initial_salary = first_history.old_salary
        current_salary = self.current_salary

        if initial_salary == 0:
            return 0
        
        return round(((current_salary - initial_salary) / initial_salary) * 100, 2)


    def __str__(self):
        return f"{self.user.get_full_name()} - {self.role.title}"
    
    @property
    def is_active(self):
        return self.termination_date is None
    
    @property
    def is_team_lead(self):
        return self.team_members.exists()
    
    @property
    def full_name(self):
        return self.user.get_full_name() or self.user.username
    
    class Meta:
        ordering = ['user__last_name', 'user__first_name']


class SalaryHistory(TimeStampedModel):
    """
    Historial de cambios de salario de un empleado.

    Registra las siguientes modificaciones:
    - Valores anteriores y nuevos.
    - Quien realizo el cambio.
    - Razon del cambio.
    - Fecha efectiva del cambio.

    Permite auditoria completa y analisis del crecimiento salarial
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='salary_history'
    )

    # Datos del cambio
    old_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Salary before the change"
    )
    new_salary = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Salary after the change"
    )

    # Metada del cambio
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='salary_changes_made',
        help_text="User who made the change"
    )
    change_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reason for the salary change (e.g 'Annual raise', 'Promotion')"
    )
    effective_date = models.DateField(
        help_text="Date when the new salary takes effect"
    )

    objects = SalaryHistoryManager()

    class Meta:
        ordering = ['-effective_date','-created_at']
        verbose_name_plural = 'Salaries histories'
        indexes = [
            models.Index(fields=['employee', '-effective_date']),
            models.Index(fields=['changed_by', '-created_at'])
        ]

    def __str__(self):
        return f"{self.employee.full_name}: ${self.old_salary} -> ${self.new_salary}"
    
    @property
    def change_amount(self):
        """Diferencia en pesos"""
        return self.new_salary - self.old_salary
    
    @property
    def change_percentage(self):
        """Diferencia porcentual"""
        if self.old_salary == 0:
            return 0
        if not self.old_salary:
            return 0
        return round(((self.new_salary - self.old_salary) / self.old_salary) * 100, 2)
    
    @property
    def is_raise(self):
        """True si fue un aumento"""
        return self.new_salary > self.old_salary
    
    @property
    def is_decrease(self):
        """True si fue una reduccion"""
        return self.old_salary > self.new_salary
    
    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError

        # Validar que las fechas tengan sentido
        if self.employee_id:
            if self.effective_date < self.employee.hire_date:
                raise ValidationError(
                    f'Effective date cannot be before hire date ({self.employee.hire_date})'
                )
        
        # Validar que haya un cambio real
        if self.old_salary == self.new_salary:
            raise ValidationError('Old salary and new salary cannot be the same')
        
        # Validar que los salaries sean positivos
        if self.old_salary < 0 or self.new_salary < 0:
            raise ValidationError('Salaries must be positive')
        


class RoleHistory(TimeStampedModel):
    """
    Historial de cambios de rol y seniority de un empleado

    Registra cada cambio de:
    - Rol/posicion (ej: Developer -> Senior Developer)
    - Nivel de seniority: (ej: JUNIOR -> MID)
    - Department (si cambia con el rol)

    Permite tracking de carrera y analisis de promociones
    """
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='role_history'
    )

    # Datos del cambio de rol
    old_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        related_name='history_as_old_role',
        help_text="Role before the change"
    )
    new_role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        related_name='history_as_new_role',
        help_text="Role after the change"
    )

    # Datos del cambio de seniority
    old_seniority = models.CharField(
        max_length=10,
        choices=SENIORITY_LEVELS,
        help_text="Seniority level before the change"
    )
    new_seniority = models.CharField(
        max_length=10,
        choices=SENIORITY_LEVELS,
        help_text="Seniority level after the change"
    )

    # Metadata del cambio
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='role_changes_made',
        help_text="User who made the change"
    )
    change_reason = models.CharField(
        max_length=255,
        blank=True,
        help_text="Reason for the role change(e.g. 'Promotion', 'Internal transfer'.)"
    )
    effective_date = models.DateField(
        help_text="Date when the new role takes effect"
    )

    objects = RoleHistoryManager()

    class Meta:
        ordering = ['-effective_date', '-created_at']
        verbose_name_plural = 'Role histories'
        indexes = [
            models.Index(fields=['employee', '-effective_date']),
            models.Index(fields=['changed_by', '-created_at']),
            models.Index(fields=['old_role']),
            models.Index(fields=['new_role']),
        ]

    def __str__(self):
        old_role_title = self.old_role.title if self.old_role else "Unknown"
        new_role_title = self.new_role.title if self.new_role else "Unknown"
        return f"{self.employee.full_name}: {old_role_title} -> {new_role_title}"
    
    @property
    def promotion_or_demotion(self):
        """
        Evalua si fue una promocion o una democion de seniority.
        Devuelve str con los valores promotion (en caso de haber sido una promocion) o demotion (en caso de haber sido una democion)
        Siempre hablando de seniorities.
        """
        seniority_order = {'JUNIOR': 1, 'MID': 2, 'SENIOR': 3}
        old_level = seniority_order.get(self.old_seniority, 0)
        new_level = seniority_order.get(self.new_seniority, 0)
        if new_level > old_level:
            return 'promotion'
        elif old_level > new_level:
            return 'promotion'
        else:
            return None
    
    @property
    def is_lateral_move(self):
        """Cambio de role sin cambio de seniority"""
        return self.old_seniority == self.new_seniority and self.old_role != self.new_role
    
    @property
    def changed_department(self):
        """True si cambio de department"""
        if not self.old_role or not self.new_role:
            return False
        return self.old_role.department != self.new_role.department
    
    def clean(self):
        """Validaciones del modelo"""
        from django.core.exceptions import ValidationError

        # Validar que las fechas tengan sentido
        if self.employee_id:
            if self.effective_date < self.employee.hire_date:
                raise ValidationError(
                    f'Effective date cannot be before hire date ({self.employee.hire_date})'
                )
            
        # Validar que haya un cambio real
        if self.old_role == self.new_role and self.old_seniority == self.new_seniority:
            raise ValidationError('There must be a change in either role or seniority')