"""
Utilidades para comandos management
"""

import sys
from typing import Iterable, Callable, Any
from django.core.management.base import BaseCommand

class ProgressBar:
    """Barra de progreso simple para terminal"""

    def __init__(self, total: int, prefix: str = '', length: int = 50):
        self.total = total
        self.prefix = prefix
        self.length = length
        self.current = 0

    def update(self, step: int = 1):
        """Actualizar progreso"""
        self.current += step
        self._print()

    def _print(self):
        """Imprimir barra de progreso"""
        percent = min(100, (self.current / self.total) * 100)
        filled = int(self.length * self.current // self.total)
        bar = '█' * filled + '░' * (self.length - filled)

        # Usar \r para sobreescribit la linea
        sys.stdout.write(f'\r{self.prefix}: [{bar}] {percent:.1f} ({self.current}/{self.total})')
        sys.stdout.flush()

        # Nueva linea cuando termina
        if self.current >= self.total:
            sys.stdout.write('\n')

    def finish(self):
        """forzar completar al 100%"""
        self.current = self.total
        self._print()


class ColoredOutput:
    """Mensajes con colores en terminal"""

    # Codigos ANSI de colores
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'reset': '\033[0m',
        'bold': '\033[1m',
    }

    @classmethod
    def success(cls, message: str) -> str:
        """Mensaje de éxito (verde)"""
        return f"{cls.COLORS['green']}✓ {message}{cls.COLORS['reset']}"
    
    @classmethod
    def error(cls, message: str) -> str:
        """Mensaje de error (rojo)"""
        return f"{cls.COLORS['red']}✗ {message}{cls.COLORS['reset']}"
    
    @classmethod
    def warning(cls, message: str) -> str:
        """Mensaje de advertencia (amarillo)"""
        return f"{cls.COLORS['yellow']}⚠ {message}{cls.COLORS['reset']}"
    
    @classmethod
    def info(cls, message: str) -> str:
        """Mensaje informativo (cyan)"""
        return f"{cls.COLORS['cyan']}ℹ {message}{cls.COLORS['reset']}"
    
    @classmethod
    def header(cls, message: str) -> str:
        """Encabezado (bold + blue)"""
        return f"{cls.COLORS['bold']}{cls.COLORS['blue']}{message}{cls.COLORS['reset']}"
    
    @classmethod
    def colored(cls, message: str, color: str) -> str:
        """Mensaje con color personalizado"""
        color_code = cls.COLORS.get(color, cls.COLORS['white'])
        return f"{color_code}{message}{cls.COLORS['reset']}"
    
def batch_create(
        factory_class: Callable,
        count: int,
        message: str = "Creating items",
        **factory_kwargs
) -> list:
    """
    Crear multiples instancias con progress bar
    
    Args:
        factory_class: la factory a usar
        count: Cantidad a crear
        message: Mensaje para la barra de progreso
        **factory_kwargs: Argumentos para la factory
    Returns:
        Lista de instancias creadas
    """

    progress = ProgressBar(total=count, prefix=message)
    items = []
    
    for _ in range(count):
        item = factory_class(**factory_kwargs)
        items.append(item)
        progress.update()

    return items

def confirm_action(command: BaseCommand, message: str, default:bool = False) -> bool:
    """
    Pedir confimacion al usuario
    Args:
        command: Instancia del comando (para usar self.stdout)
        message: Mensaje a mostrar
        default: Valor por defecto si solo presiona enter

    Returns:
        True si confirma, False si no confirma
    """
    default_text = "Y/n" if default else "y/N"
    command.stdout.write(f"{message} [{default_text}]: ", ending='')

    response = input().strip().lower()

    if not response:
        return default
    
    return response in ['y', 'yes', 'si', 'sí']

def print_summary(command: BaseCommand, data: dict):
    """
    Imprimir resumen de datos creados
    
    Args:
        command: Instancia del comando
        data: Diccionario con estadísticas
    """
    command.stdout.write("\n" + "=" * 60)
    command.stdout.write(ColoredOutput.header("  📊 RESUMEN DE DATOS GENERADOS"))
    command.stdout.write("=" * 60 + "\n")
    
    for key, value in data.items():
        # Formatear el nombre del key (de snake_case a Title Case)
        formatted_key = key.replace('_', ' ').title()
        command.stdout.write(f"  {formatted_key:.<40} {ColoredOutput.colored(str(value), 'cyan')}")
    
    command.stdout.write("=" * 60 + "\n")


def print_section_header(command: BaseCommand, title: str):
    """Imprimir encabezado de sección"""
    command.stdout.write(f"\n{ColoredOutput.header(f'▶ {title}')}")
    command.stdout.write("-" * 60)


def handle_error(command: BaseCommand, error: Exception, context: str = ""):
    """
    Manejar errores de forma consistente
    
    Args:
        command: Instancia del comando
        error: La excepción capturada
        context: Contexto adicional sobre el error
    """
    error_msg = f"Error {context}: {str(error)}" if context else f"Error: {str(error)}"
    command.stdout.write(ColoredOutput.error(error_msg))
    
    # En modo debug, mostrar traceback completo
    import traceback
    command.stdout.write(ColoredOutput.warning("\nTraceback:"))
    command.stdout.write(traceback.format_exc())


# Constantes útiles
PRESETS = {
    'small': {
        'departments': 3,
        'roles_per_dept': 3,
        'employees': 100,
        'orphan_users': 20,
        'team_leads_ratio': 0.1,  # 10% son team leads
        'terminated_ratio': 0.05,  # 5% empleados terminados
        'recent_hires_ratio': 0.15,  # 15% contratados recientemente
    },
    'medium': {
        'departments': 6,
        'roles_per_dept': 3,
        'employees': 300,
        'orphan_users': 50,
        'team_leads_ratio': 0.12,
        'terminated_ratio': 0.08,
        'recent_hires_ratio': 0.12,
    },
    'large': {
        'departments': 8,
        'roles_per_dept': 3,
        'employees': 500,
        'orphan_users': 100,
        'team_leads_ratio': 0.15,
        'terminated_ratio': 0.10,
        'recent_hires_ratio': 0.10,
    }
}

# Distribucion de seniority (porcentajes)
SENIORITY_DISTRIBUTION = {
    'JUNIOR': 0.60,
    'MID': 0.30,
    'SENIOR': 0.10,
}
