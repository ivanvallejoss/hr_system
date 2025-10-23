from django.contrib import admin;
from .models import Department, Role, Employee, SalaryHistory, RoleHistory;

# Register your models here.

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'department_manager', 'budget', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'created_at']
    list_filter = ['department', 'created_at']
    search_fields = ['title']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'get_role', 'seniority_level', 'manager', 'is_active']
    list_filter = ['seniority_level', 'role__department', 'hire_date']
    search_fields = ['user__first_name', 'user__last_name']

    def get_role(self, obj):
        return f"{obj.role.title} - {obj.role.department.name}" 
    get_role.short_description = 'Role & Department'

    def get_is_active(self, obj):
        return obj.is_active
    get_is_active.boolean = True
    get_is_active.short_description = 'Active'

@admin.register(SalaryHistory)
class SalaryHistoryAdmin(admin.ModelAdmin):
    """Admin para SalaryHistory"""

    list_display = [
        'employee',
        'old_salary',
        'new_salary',
        'change_amount_display',
        'change_percentage_display',
        'effective_date',
        'changed_by',
        'created_at'
    ]

    list_filter = [
        'effective_date',
        'created_at',
        'changed_by'
    ]

    search_fields = [
        'employee__user__first_name',
        'employee__user__last_name',
        'employee__user__username',
        'change_reason'
    ]

    readonly_fields = [
        'employee',
        'old_salary',
        'new_salary',
        'changed_by',
        'change_reason',
        'effective_date',
        'created_at',
        'updated_at',
        'change_amount_display',
        'change_percentage_display'
    ]

    ordering = ['-effective_date', '-created_at']

    def change_amount_display(self, obj):
        """Muestra el cambio en pesos con formato"""
        amount = obj.change_amount
        if amount > 0:
            return f"+${amount:,.2f}"
        return f"${amount:,.2f}"
    change_amount_display.short_description = 'Change Amount'

    def change_percentage_display(self, obj):
        """Muestra el cambio en porcentaje con color"""
        percentage = obj.change_percentage
        if percentage > 0:
            return f"+{percentage}%"
        return f"{percentage}%"
    change_percentage_display.short_description = 'Change %'

    def has_add_permission(self, request):
        """No permitir crear history manualmente en admin"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir borrar history en admin (auditoria)"""
        return False
    

@admin.register(RoleHistory)
class RoleHistoryAdmin(admin.ModelAdmin):
    """Admin para RoleHistory"""

    list_display = [
        'employee',
        'old_role',
        'new_role',
        'old_seniority',
        'new_seniority',
        'change_type_display',
        'effective_date',
        'changed_by',
        'created_at'
    ]

    list_filter = [
        'old_seniority',
        'new_seniority',
        'effective_date',
        'created_at',
        'changed_by'
    ]

    search_fields = [
        'employee__user__first_name',
        'employee__user__last_name',
        'employee__user__username',
        'old_role__title',
        'new_role__title',
        'change_reason'
    ]

    readonly_fields = [
        'employee',
        'old_role',
        'new_role',
        'old_seniority',
        'new_seniority',
        'changed_by',
        'change_reason',
        'effective_date',
        'change_type_display',
        'created_at',
        'updated_at',
        'department_change_display'
    ]

    date_hierarchy = 'effective_date'

    ordering = ['-effective_date', '-created_at']

    def change_type_display(self, obj):
        """Muestra el tipo de cambio (Promotion, Lateral, etc)"""
        if obj.promotion_or_demotion == 'promotion':
            return "PROMOTION!"
        if obj.promotion_or_demotion == 'demotion':
            return "DEMOTION"
        if obj.is_lateral_move:
            return "Lateral Move"
        return "Change"
    change_type_display.short_description = 'Type'

    def department_change_display(self, obj):
        """Indica si hubo cambio de departamento"""
        if obj.changed_department:
            return f"{obj.old_role.department} -> {obj.new_role.department}"
        return "-"
    department_change_display.short_description = 'Department Change'

    def has_add_permission(self, request):
        """No permitir crear history manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir borrar history (auditoria)"""
        return False