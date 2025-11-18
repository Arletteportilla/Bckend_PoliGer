"""
Archivo de compatibilidad para serializers
Importa desde la nueva ubicación en api/
"""

# Importar todo desde la nueva ubicación
from .api.serializers import *

# Mantener compatibilidad con importaciones existentes
__all__ = [
    'GeneroSerializer', 'EspecieSerializer', 'VariedadSerializer',
    'UbicacionSerializer', 'PolinizacionSerializer', 'GerminacionSerializer', 
    'SeguimientoGerminacionSerializer', 'CapsulaSerializer', 'SiembraSerializer', 
    'PersonalUsuarioSerializer', 'InventarioSerializer', 'NotificationSerializer',
    'UserProfileSerializer', 'UserWithProfileSerializer', 'CreateUserWithProfileSerializer',
    'UpdateUserProfileSerializer', 'UpdateUserMetasSerializer', 'PermissionsSerializer'
]