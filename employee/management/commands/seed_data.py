"""
Comando para generar datos de prueba masivos del sistema HR
"""

import random
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from django.db import transaction
from django.conf import settings

from employee.factories import (
    GroupFactory, 
    UserFactory, 
    DepartmentFactory, 
    RoleFactory, 
    EmployeeFactory
    )
from employee.models import Employee, Department, Role
from ._utils import (
    ColoredOutput,
    confirm_action,
    print_section_header,
    handle_error,
    print_summary,
    batch_create,
    PRESETS,
    SENIORITY_DISTRIBUTION
)


class Command(BaseCommand):
    help = 'Generar datos de prueba masivos para el sistema HR'
    
    def add_arguments(self, parser):
        """Agregar argumentos al comando"""
        
        # Presets predefinidos
        parser.add_argument(
            '--preset',
            choices=['small', 'medium', 'large'],
            default='medium',
            help='Usar preset predefinido de datos (default: medium)',
        )
        
        # Parámetros personalizados
        parser.add_argument(
            '--employees',
            type=int,
            help='Número de empleados a crear (override preset)',
        )
        
        parser.add_argument(
            '--departments',
            type=int,
            help='Número de departamentos a crear (override preset)',
        )
        
        parser.add_argument(
            '--orphan-users',
            type=int,
            help='Número de usuarios sin perfil de empleado (override preset)',
        )
        
        # Opciones de control
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Limpiar datos existentes antes de generar nuevos',
        )
        
        parser.add_argument(
            '--no-cache-clear',
            action='store_true',
            help='No limpiar cache después de generar datos',
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular generación sin crear datos reales',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Ejecutar sin confirmaciones (para scripts automáticos)',
        )
    
    def handle(self, *args, **options):
        """Punto de entrada principal"""
        self.stdout.write(ColoredOutput.header("🏗️  GENERADOR DE DATOS DEL SISTEMA HR"))
        self.stdout.write("=" * 60)
        
        # Preparar configuración
        config = self._prepare_config(options)
        
        # Mostrar configuración
        self._show_config(config, options)
        
        # Confirmación (si no es --force o --dry-run)
        if not options['force'] and not options['dry_run']:
            if not confirm_action(self, "\n¿Proceder con la generación de datos?", default=True):
                self.stdout.write(ColoredOutput.info("Operación cancelada"))
                return
        
        # Ejecutar generación
        try:
            if options['dry_run']:
                self._dry_run_generation(config)
            else:
                self._generate_data(config, options)
        except Exception as e:
            handle_error(self, e, "durante la generación de datos")
    
    def _prepare_config(self, options):
        """Preparar configuración basada en preset y overrides"""
        preset_name = options['preset']
        config = PRESETS[preset_name].copy()
        
        # Aplicar overrides si se especificaron
        if options['employees']:
            config['employees'] = options['employees']
        
        if options['departments']:
            config['departments'] = options['departments']
            
        if options['orphan_users']:
            config['orphan_users'] = options['orphan_users']
        
        # Calcular roles automáticamente basado en departamentos
        config['total_roles'] = config['departments'] * config['roles_per_dept']
        
        # Calcular distribuciones basadas en empleados
        config['team_leads_count'] = int(config['employees'] * config['team_leads_ratio'])
        config['terminated_count'] = int(config['employees'] * config['terminated_ratio'])
        config['recent_hires_count'] = int(config['employees'] * config['recent_hires_ratio'])
        
        # Distribución de seniority
        config['junior_count'] = int(config['employees'] * SENIORITY_DISTRIBUTION['JUNIOR'])
        config['mid_count'] = int(config['employees'] * SENIORITY_DISTRIBUTION['MID'])
        config['senior_count'] = config['employees'] - config['junior_count'] - config['mid_count']
        
        return config
    
    def _show_config(self, config, options):
        """Mostrar configuración que se va a usar"""
        print_section_header(self, f"CONFIGURACIÓN: PRESET '{options['preset'].upper()}'")
        
        display_config = {
            'preset_usado': options['preset'],
            'departamentos': config['departments'],
            'roles_totales': config['total_roles'],
            'empleados_totales': config['employees'],
            'empleados_junior': config['junior_count'],
            'empleados_mid': config['mid_count'],
            'empleados_senior': config['senior_count'],
            'team_leads': config['team_leads_count'],
            'empleados_terminados': config['terminated_count'],
            'contrataciones_recientes': config['recent_hires_count'],
            'usuarios_sin_perfil': config['orphan_users'],
        }
        
        if options['clear']:
            display_config['accion_previa'] = "🗑️ LIMPIAR DATOS EXISTENTES"
        
        print_summary(self, display_config)
    
    def _dry_run_generation(self, config):
        """Simular generación sin crear datos"""
        print_section_header(self, "SIMULACIÓN DE GENERACIÓN (DRY RUN)")
        
        self.stdout.write(ColoredOutput.info("Simulando creación de datos..."))
        
        steps = [
            ("🏢 Grupos de usuarios", 3),
            ("🏢 Departamentos", config['departments']),
            ("💼 Roles", config['total_roles']),
            ("👥 Empleados Junior", config['junior_count']),
            ("👥 Empleados Mid", config['mid_count']),
            ("👥 Empleados Senior", config['senior_count']),
            ("👑 Team Leads", config['team_leads_count']),
            ("📅 Contrataciones recientes", config['recent_hires_count']),
            ("❌ Empleados terminados", config['terminated_count']),
            ("👤 Usuarios sin perfil", config['orphan_users']),
        ]
        
        self.stdout.write("\n📋 Se crearían:")
        for step_name, count in steps:
            self.stdout.write(f"  • {count:>3} {step_name}")
        
        total_items = sum(count for _, count in steps)
        self.stdout.write(f"\n📊 Total de items: {ColoredOutput.colored(str(total_items), 'cyan')}")
        self.stdout.write(ColoredOutput.success("\n✅ Simulación completada (no se creó nada)"))
    
    def _generate_data(self, config, options):
        """Ejecutar la generación real de datos"""
        print_section_header(self, "GENERANDO DATOS")
        
        created_counts = {}
        
        try:
            with transaction.atomic():
                
                # Paso 0: Limpiar datos existentes si se solicitó
                if options['clear']:
                    print_section_header(self, "Limpiando datos existentes")
                    self._clear_existing_data()
                
                # Paso 1: Crear grupos de usuarios
                print_section_header(self, "Creando Grupos de Usuarios")
                groups = self._create_groups()
                created_counts['grupos'] = len(groups)
                
                # Paso 2: Crear departamentos
                print_section_header(self, "Creando Departamentos")
                departments = self._create_departments(config)
                created_counts['departamentos'] = len(departments)
                
                # Paso 3: Crear roles
                print_section_header(self, "Creando Roles")
                roles = self._create_roles(departments, config)
                created_counts['roles'] = len(roles)
                
                # Paso 4: Crear empleados por seniority
                print_section_header(self, "Creando Empleados")
                employees = self._create_employees(roles, config)
                created_counts.update(employees)
                
                # Paso 5: Asignar managers y crear team leads
                print_section_header(self, "Configurando Jerarquías")
                team_leads = self._setup_hierarchies(config)
                created_counts['team_leads'] = team_leads
                
                # Paso 6: Asignar department managers
                print_section_header(self, "Asignando Managers de Departamento")
                dept_managers = self._assign_department_managers()
                created_counts['department_managers'] = dept_managers
                
                # Paso 7: Crear usuarios sin perfil
                print_section_header(self, "Creando Usuarios sin Perfil")
                orphan_users = self._create_orphan_users(groups, config)
                created_counts['usuarios_sin_perfil'] = len(orphan_users)
            
            # Resumen final
            print_section_header(self, "GENERACIÓN COMPLETADA")
            print_summary(self, created_counts)
            
            self.stdout.write(ColoredOutput.success("🎉 Datos generados exitosamente"))
            
            # Limpiar cache
            if not options['no_cache_clear']:
                self._clear_cache()
                
        except Exception as e:
            self.stdout.write(ColoredOutput.error(f"❌ Error durante la generación: {str(e)}"))
            raise
    
    def _clear_existing_data(self):
        """Limpiar datos existentes"""
        from django.core.management import call_command
        call_command('clear_data', '--force', '--keep-superusers')
    
    def _create_groups(self):
        """Crear grupos de usuarios necesarios"""
        groups = []
        for group_name in ['Admin', 'HR', 'Employee']:
            group, created = Group.objects.get_or_create(name=group_name)
            groups.append(group)
            if created:
                self.stdout.write(f"  ✓ Grupo '{group_name}' creado")
            else:
                self.stdout.write(f"  ℹ Grupo '{group_name}' ya existía")
        
        return groups
    
    def _create_departments(self, config):
        """Crear departamentos"""
        departments = batch_create(
            DepartmentFactory,
            count=config['departments'],
            message="Creando departamentos"
        )
        
        return departments
    
    def _create_roles(self, departments, config):
        """Crear roles distribuidos en departamentos"""
        roles = []
        
        for dept in departments:
            dept_roles = batch_create(
                RoleFactory,
                count=config['roles_per_dept'],
                message=f"Creando roles para {dept.name}",
                department=dept
            )
            roles.extend(dept_roles)
        
        return roles
    
    def _create_employees(self, roles, config):
        """Crear empleados con distribución de seniority"""
        created_counts = {}
        
        # Crear empleados Junior
        junior_employees = []
        for _ in range(config['junior_count']):
            employee = EmployeeFactory(
                is_junior=True,
                role=random.choice(roles)
            )
            junior_employees.append(employee)
        created_counts['empleados_junior'] = len(junior_employees)
        
        # Crear empleados Mid
        mid_employees = []
        for _ in range(config['mid_count']):
            employee = EmployeeFactory(
                is_mid=True,
                role=random.choice(roles)
            )
            mid_employees.append(employee)
        created_counts['empleados_mid'] = len(mid_employees)
        
        # Crear empleados Senior
        senior_employees = []
        for _ in range(config['senior_count']):
            employee = EmployeeFactory(
                is_senior=True,
                role=random.choice(roles)
            )
            senior_employees.append(employee)
        created_counts['empleados_senior'] = len(senior_employees)
        
        # Crear contrataciones recientes
        recent_hires = []
        for _ in range(config['recent_hires_count']):
            employee = EmployeeFactory(
                recently_hired=True,
                role=random.choice(roles)
            )
            recent_hires.append(employee)
        created_counts['contrataciones_recientes'] = len(recent_hires)
        
        # Crear empleados terminados
        terminated = []
        for _ in range(config['terminated_count']):
            employee = EmployeeFactory(
                is_terminated=True,
                role=random.choice(roles)
            )
            terminated.append(employee)
        created_counts['empleados_terminados'] = len(terminated)
        
        return created_counts
    
    def _setup_hierarchies(self, config):
        """Configurar jerarquías de managers"""
        # Obtener empleados activos que pueden ser managers
        potential_managers = list(Employee.objects.filter(
            termination_date__isnull=True,
            seniority_level__in=['MID', 'SENIOR']
        ).select_related('user'))
        
        # Obtener empleados que necesitan manager
        employees_needing_manager = list(Employee.objects.filter(
            manager__isnull=True,
            termination_date__isnull=True
        ).select_related('user'))
        
        team_leads_created = 0
        
        # Asignar managers aleatoriamente
        random.shuffle(employees_needing_manager)
        
        for employee in employees_needing_manager:
            if potential_managers and random.random() < 0.7:  # 70% probabilidad de tener manager
                manager = random.choice(potential_managers)
                if manager != employee:  # No puede ser manager de sí mismo
                    employee.manager = manager
                    employee.save()
                    team_leads_created += 1
        
        return team_leads_created
    
    def _assign_department_managers(self):
        """Asignar managers a departamentos"""
        departments = Department.objects.all()
        department_managers_assigned = 0
        
        for dept in departments:
            # Buscar empleados senior en este departamento
            potential_managers = Employee.objects.filter(
                role__department=dept,
                seniority_level__in=['MID', 'SENIOR'],
                termination_date__isnull=True
            )
            
            if potential_managers.exists():
                manager = random.choice(potential_managers)
                dept.department_manager = manager
                dept.save()
                department_managers_assigned += 1
        
        return department_managers_assigned
    
    def _create_orphan_users(self, groups, config):
        """Crear usuarios sin perfil de empleado"""
        orphan_users = []
        employee_group = next(g for g in groups if g.name == 'Employee')
        
        for _ in range(config['orphan_users']):
            user = UserFactory(groups=[employee_group])
            orphan_users.append(user)
        
        return orphan_users
    
    def _clear_cache(self):
        """Limpiar cache después de la generación"""
        try:
            from django.core.cache import cache
            cache.clear()
            self.stdout.write(ColoredOutput.success("✓ Cache limpiado"))
        except Exception as e:
            self.stdout.write(ColoredOutput.warning(f"⚠ No se pudo limpiar el cache: {str(e)}"))


def factory_random_choice(items):
    """Helper para Factory Boy: elegir item aleatorio de una lista"""
    return random.choice(items)