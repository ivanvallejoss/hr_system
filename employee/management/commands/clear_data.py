"""
Comando para limpiar datos de prueba del sistema HR
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.db import transaction
from django.db.models import Count, Q
from django.conf import settings

from employee.models import Employee, Department, Role
from ._utils import (
    ColoredOutput, 
    confirm_action, 
    print_section_header, 
    handle_error,
    print_summary
)


class Command(BaseCommand):
    help = 'Limpiar todos los datos de prueba del sistema HR'
    
    def add_arguments(self, parser):
        """Agregar argumentos al comando"""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Limpiar sin pedir confirmación (¡PELIGROSO!)',
        )
        
        parser.add_argument(
            '--keep-superusers',
            action='store_true',
            help='Mantener superusers durante la limpieza',
        )
        
        parser.add_argument(
            '--keep-groups',
            action='store_true',
            help='Mantener grupos de usuarios (Admin, HR, Employee)',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular limpieza sin borrar nada (para ver qué se borraría)',
        )
    
    def handle(self, *args, **options):
        """Punto de entrada principal"""
        self.stdout.write(ColoredOutput.header("🗑️  LIMPIEZA DE DATOS DEL SISTEMA HR"))
        self.stdout.write("=" * 60)
        
        # Verificar si estamos en producción
        if not settings.DEBUG and not options['force']:
            self.stdout.write(ColoredOutput.error(
                "⚠️  MODO PRODUCCIÓN DETECTADO"
            ))
            self.stdout.write(
                "Este comando está diseñado para desarrollo.\n"
                "Si realmente quieres ejecutarlo en producción, usa --force"
            )
            return
        
        # Mostrar información actual
        self._show_current_data()
        
        # Confirmación (si no es --force)
        if not options['force'] and not options['dry_run']:
            if not confirm_action(
                self, 
                "\n🚨 ¿Estás SEGURO que quieres borrar todos estos datos?",
                default=False
            ):
                self.stdout.write(ColoredOutput.info("Operación cancelada"))
                return
        
        # Ejecutar limpieza
        try:
            if options['dry_run']:
                self._dry_run_cleanup(options)
            else:
                self._perform_cleanup(options)
        except Exception as e:
            handle_error(self, e, "durante la limpieza")
    
    def _show_current_data(self):
        """Mostrar datos actuales en el sistema"""
        print_section_header(self, "DATOS ACTUALES EN EL SISTEMA")

        # Estadisticas de usuarios.
        user_stats = User.objects.select_related('employee').aggregate(
            total_users=Count('id'),
            superusers=Count('id', filter=Q(is_superuser=True)),
            regular_users=Count('id', filter=Q(is_superuser=False)),
            users_without_employee=Count('id', filter=Q(employee__isnull=True))
        )

        # Estadisticas de empleados
        employee_stats = Employee.objects.aggregate(
            total_employees=Count('id'),
            active_employees=Count('id', filter=Q(termination_date__isnull=True)),
            terminated_employees=Count('id', filter=Q(termination_date__isnull=False)),
            team_leads=Count('manager', distinct=True, filter=Q(manager__isnull=False))
        )

        # Estadisticas generales
        company_stats = {
            'total_departments': Department.objects.count(),
            'total_roles': Role.objects.count(),
            'total_groups': Group.objects.count()
        }

        # comprimiendo los stats
        stats = {**user_stats, **employee_stats, **company_stats}
        print_summary(self, stats)


    def _dry_run_cleanup(self, options):
        """Simular limpieza sin borrar nada"""
        print_section_header(self, "SIMULACIÓN DE LIMPIEZA (DRY RUN)")
        
        self.stdout.write(ColoredOutput.info("Simulando limpieza..."))
        
        # Contar qué se borraría
        employees_to_delete = Employee.objects.count()
        roles_to_delete = Role.objects.count()
        departments_to_delete = Department.objects.count()
        
        if options['keep_superusers']:
            users_to_delete = User.objects.filter(is_superuser=False).count()
        else:
            users_to_delete = User.objects.count()
        
        if options['keep_groups']:
            groups_to_delete = 0
        else:
            groups_to_delete = Group.objects.count()
        
        self.stdout.write("\n📋 Se borrarían:")
        items_to_delete = {
            'empleados': employees_to_delete,
            'roles': roles_to_delete,
            'departamentos': departments_to_delete,
            'usuarios': users_to_delete,
            'grupos': groups_to_delete,
        }
        
        for item_type, count in items_to_delete.items():
            color = 'red' if count > 0 else 'green'
            self.stdout.write(f"  • {count} {item_type} " + ColoredOutput.colored("🗑️", color))
        
        self.stdout.write(ColoredOutput.success("\n✅ Simulación completada (no se borró nada)"))
    
    def _perform_cleanup(self, options):
        """Ejecutar la limpieza real"""
        print_section_header(self, "EJECUTANDO LIMPIEZA")
        
        deleted_counts = {}
        
        try:
            with transaction.atomic():
                # 1. Borrar empleados (esto también limpia las relaciones manager)
                print_section_header(self, "Limpiando Empleados")
                employees_count = Employee.objects.count()
                if employees_count > 0:
                    Employee.objects.all().delete()
                    deleted_counts['empleados'] = employees_count
                    self.stdout.write(ColoredOutput.success(f"✓ {employees_count} empleados eliminados"))
                else:
                    self.stdout.write(ColoredOutput.info("No hay empleados para eliminar"))
                
                # 2. Borrar roles
                print_section_header(self, "Limpiando Roles")
                roles_count = Role.objects.count()
                if roles_count > 0:
                    Role.objects.all().delete()
                    deleted_counts['roles'] = roles_count
                    self.stdout.write(ColoredOutput.success(f"✓ {roles_count} roles eliminados"))
                else:
                    self.stdout.write(ColoredOutput.info("No hay roles para eliminar"))
                
                # 3. Borrar departamentos
                print_section_header(self, "Limpiando Departamentos")
                departments_count = Department.objects.count()
                if departments_count > 0:
                    Department.objects.all().delete()
                    deleted_counts['departamentos'] = departments_count
                    self.stdout.write(ColoredOutput.success(f"✓ {departments_count} departamentos eliminados"))
                else:
                    self.stdout.write(ColoredOutput.info("No hay departamentos para eliminar"))
                
                # 4. Borrar usuarios (con condiciones)
                print_section_header(self, "Limpiando Usuarios")
                if options['keep_superusers']:
                    users_to_delete = User.objects.filter(is_superuser=False)
                    self.stdout.write(ColoredOutput.info("Manteniendo superusers..."))
                else:
                    users_to_delete = User.objects.all()
                
                users_count = users_to_delete.count()
                if users_count > 0:
                    users_to_delete.delete()
                    deleted_counts['usuarios'] = users_count
                    self.stdout.write(ColoredOutput.success(f"✓ {users_count} usuarios eliminados"))
                else:
                    self.stdout.write(ColoredOutput.info("No hay usuarios para eliminar"))
                
                # 5. Borrar grupos (opcional)
                if not options['keep_groups']:
                    print_section_header(self, "Limpiando Grupos")
                    groups_count = Group.objects.count()
                    if groups_count > 0:
                        Group.objects.all().delete()
                        deleted_counts['grupos'] = groups_count
                        self.stdout.write(ColoredOutput.success(f"✓ {groups_count} grupos eliminados"))
                    else:
                        self.stdout.write(ColoredOutput.info("No hay grupos para eliminar"))
                else:
                    self.stdout.write(ColoredOutput.info("Manteniendo grupos de usuarios..."))
            
            # Resumen final
            print_section_header(self, "LIMPIEZA COMPLETADA")
            if deleted_counts:
                print_summary(self, deleted_counts)
            else:
                self.stdout.write(ColoredOutput.info("No se encontraron datos para eliminar"))
            
            self.stdout.write(ColoredOutput.success("🎉 Limpieza completada exitosamente"))
            
            # Limpiar cache
            self._clear_cache()
            
        except Exception as e:
            self.stdout.write(ColoredOutput.error(f"❌ Error durante la limpieza: {str(e)}"))
            raise
    
    def _clear_cache(self):
        """Limpiar cache después de la limpieza"""
        try:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write(ColoredOutput.success("✓ Cache limpiado"))
        except Exception as e:
            self.stdout.write(ColoredOutput.warning(f"⚠ No se pudo limpiar el cache: {str(e)}"))