"""
Archivo de compatibilidad para modelos
Importa desde la nueva ubicación en core/
"""

# Importar todo desde la nueva ubicación
from .core.models import *

# Mantener compatibilidad con importaciones existentes
__all__ = [
    'Genero', 'Especie', 'Variedad', 'Ubicacion', 'Polinizacion', 
    'Germinacion', 'SeguimientoGerminacion', 'Capsula', 'Siembra', 
    'PersonalUsuario', 'Inventario', 'Notification', 'UserProfile',
    'CondicionesClimaticas', 'HistorialPredicciones'
]