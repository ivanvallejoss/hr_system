from django.db import models;
from django.contrib.auth.models import User;
from core.models import TimeStampedModel;
from core.constants import SENIORITY_LEVELS;


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