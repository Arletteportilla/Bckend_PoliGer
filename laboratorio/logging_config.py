"""
Configuración de logging para el sistema de laboratorio
"""
import logging
import os
from pathlib import Path

# Configuración de logging mejorada para el backend
def setup_logging():
    """Configura el sistema de logging para la aplicación"""
    
    # Crear directorio de logs si no existe
    log_dir = Path(__file__).resolve().parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Configurar logger principal
    logger = logging.getLogger('laboratorio')
    logger.setLevel(logging.DEBUG if os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true' else logging.INFO)
    
    # Evitar duplicación de handlers
    if not logger.handlers:
        # Handler para archivo
        file_handler = logging.FileHandler(log_dir / 'laboratorio.log')
        file_handler.setLevel(logging.INFO)
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG if os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true' else logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Agregar handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# Logger para predicciones
def get_prediction_logger():
    """Logger específico para predicciones"""
    logger = logging.getLogger('laboratorio.predicciones')
    logger.setLevel(logging.DEBUG if os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true' else logging.INFO)
    return logger

# Logger para autenticación
def get_auth_logger():
    """Logger específico para autenticación"""
    logger = logging.getLogger('laboratorio.auth')
    logger.setLevel(logging.INFO)
    return logger

# Logger para API
def get_api_logger():
    """Logger específico para API"""
    logger = logging.getLogger('laboratorio.api')
    logger.setLevel(logging.INFO)
    return logger

# Función para reemplazar print statements
def log_info(message, *args, **kwargs):
    """Reemplaza print() con logging.info()"""
    logger = logging.getLogger('laboratorio')
    logger.info(message, *args, **kwargs)

def log_debug(message, *args, **kwargs):
    """Reemplaza print() con logging.debug()"""
    logger = logging.getLogger('laboratorio')
    logger.debug(message, *args, **kwargs)

def log_error(message, *args, **kwargs):
    """Reemplaza print() con logging.error()"""
    logger = logging.getLogger('laboratorio')
    logger.error(message, *args, **kwargs)

def log_warning(message, *args, **kwargs):
    """Reemplaza print() con logging.warning()"""
    logger = logging.getLogger('laboratorio')
    logger.warning(message, *args, **kwargs)