from django.contrib import admin;
from .models import Department, Role, Employee;

# Register your models here.

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'department_manager', 'budget', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['title', 'department_id', 'created_at']
    list_filter = ['department_id', 'created_at']
    search_fields = ['title']

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'role_id', 'seniority_level', 'manager', 'is_active']
    list_filter = ['seniority_level', 'role_id__department_id', 'hire_date']
    search_fields = ['user__first_name', 'user__last_name']

    def get_role(self, obj):
        return f"{obj.role_id.title} - {obj.role_id.department_id.name}" 
    get_role.short_description = 'Role & Department'

    def get_is_active(self, obj):
        return obj.is_Active
    get_is_active.boolean = True
    get_is_active.short_description = 'Active'