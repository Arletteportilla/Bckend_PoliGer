#!/usr/bin/env python
"""
Script simple para ejecutar el comando de generación de notificaciones
Útil para testing y ejecución manual
"""
import os
import sys
import django

# Agregar el directorio del proyecto al path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

# Importar y ejecutar el comando
from django.core.management import call_command

if __name__ == '__main__':
    print("="*70)
    print("Ejecutando generación de notificaciones de recordatorio")
    print("="*70)
    print()
    
    # Parsear argumentos
    import argparse
    parser = argparse.ArgumentParser(description='Generar notificaciones de recordatorio')
    parser.add_argument('--dias', type=int, default=5, help='Días límite (default: 5)')
    parser.add_argument('--dry-run', action='store_true', help='Modo simulación')
    
    args = parser.parse_args()
    
    # Ejecutar comando
    try:
        if args.dry_run:
            call_command('generar_notificaciones_recordatorio', dias=args.dias, dry_run=True)
        else:
            call_command('generar_notificaciones_recordatorio', dias=args.dias)
        
        print()
        print("="*70)
        print("✅ Ejecución completada exitosamente")
        print("="*70)
        
    except Exception as e:
        print()
        print("="*70)
        print(f"❌ Error durante la ejecución: {e}")
        print("="*70)
        sys.exit(1)
