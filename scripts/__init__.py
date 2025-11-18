"""
Scripts de utilidad para el proyecto
Configuración de paths para que funcionen desde cualquier ubicación
"""
import sys
from pathlib import Path

# Agregar el directorio raíz del backend al path
backend_root = Path(__file__).parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))
