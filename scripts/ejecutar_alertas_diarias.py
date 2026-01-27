#!/usr/bin/env python
"""
Script para ejecutar las alertas de revisión diariamente
Este script se puede configurar para ejecutarse automáticamente con cron o tareas programadas
"""
import os
import sys
import django
from datetime import datetime
import logging

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/alertas_revision.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def ejecutar_alertas_diarias():
    """Ejecuta el comando de generación de alertas diarias"""
    try:
        logger.info("🚀 Iniciando ejecución de alertas diarias")
        
        from django.core.management import call_command
        from io import StringIO
        
        # Capturar la salida del comando
        out = StringIO()
        call_command('generar_alertas_revision', stdout=out)
        output = out.getvalue()
        
        # Log de la salida
        logger.info("📋 Resultado de la ejecución:")
        for line in output.split('\n'):
            if line.strip():
                logger.info(f"   {line}")
        
        logger.info("✅ Ejecución de alertas diarias completada exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando alertas diarias: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    ejecutar_alertas_diarias()