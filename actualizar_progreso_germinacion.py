#!/usr/bin/env python
"""
Script para actualizar el progreso de germinación según el estado actual
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.models import Germinacion

def main():
    print("=" * 80)
    print("ACTUALIZANDO PROGRESO DE GERMINACIÓN")
    print("=" * 80)
    
    # Contar germinaciones
    total = Germinacion.objects.count()
    print(f"\n📊 Total de germinaciones: {total}")
    
    if total == 0:
        print("⚠️ No hay germinaciones para actualizar")
        return
    
    # Actualizar progreso según estado
    print("\n1. Actualizando progreso de germinaciones FINALIZADAS...")
    finalizadas = Germinacion.objects.filter(
        estado_germinacion='FINALIZADO'
    ).update(progreso_germinacion=100)
    print(f"   ✅ {finalizadas} germinaciones actualizadas a 100%")
    
    print("\n2. Actualizando progreso de germinaciones EN_PROCESO...")
    en_proceso = Germinacion.objects.filter(
        estado_germinacion='EN_PROCESO'
    ).update(progreso_germinacion=50)
    print(f"   ✅ {en_proceso} germinaciones actualizadas a 50%")
    
    print("\n3. Actualizando progreso de germinaciones INICIALES...")
    iniciales = Germinacion.objects.filter(
        estado_germinacion='INICIAL'
    ).update(progreso_germinacion=0)
    print(f"   ✅ {iniciales} germinaciones actualizadas a 0%")
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE ACTUALIZACIÓN")
    print("=" * 80)
    print(f"Total procesado: {finalizadas + en_proceso + iniciales}")
    print(f"  - FINALIZADO (100%): {finalizadas}")
    print(f"  - EN_PROCESO (50%): {en_proceso}")
    print(f"  - INICIAL (0%): {iniciales}")
    print("=" * 80)
    print("\n✅ Actualización completada exitosamente")
    print("\n📝 Nota: Ahora puedes actualizar el progreso manualmente y el estado")
    print("   se actualizará automáticamente:")
    print("   - 0% = INICIAL")
    print("   - 1-99% = EN_PROCESO")
    print("   - 100% = FINALIZADO")

if __name__ == '__main__':
    main()
