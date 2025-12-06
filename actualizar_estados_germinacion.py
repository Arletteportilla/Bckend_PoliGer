#!/usr/bin/env python
"""
Script para actualizar los estados de germinación existentes
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
    print("ACTUALIZANDO ESTADOS DE GERMINACIÓN")
    print("=" * 80)
    
    # Contar germinaciones
    total = Germinacion.objects.count()
    print(f"\n📊 Total de germinaciones: {total}")
    
    if total == 0:
        print("⚠️ No hay germinaciones para actualizar")
        return
    
    # Actualizar según fecha_germinacion
    print("\n1. Actualizando germinaciones finalizadas...")
    finalizadas = Germinacion.objects.filter(
        fecha_germinacion__isnull=False
    ).update(estado_germinacion='FINALIZADO')
    print(f"   ✅ {finalizadas} germinaciones marcadas como FINALIZADO")
    
    # Las que tienen fecha de siembra pero no de germinación -> EN_PROCESO
    print("\n2. Actualizando germinaciones en proceso...")
    en_proceso = Germinacion.objects.filter(
        fecha_germinacion__isnull=True,
        fecha_siembra__isnull=False
    ).update(estado_germinacion='EN_PROCESO')
    print(f"   ✅ {en_proceso} germinaciones marcadas como EN_PROCESO")
    
    # Las demás -> INICIAL (ya tienen este valor por defecto)
    print("\n3. Contando germinaciones iniciales...")
    iniciales = Germinacion.objects.filter(
        estado_germinacion='INICIAL'
    ).count()
    print(f"   ✅ {iniciales} germinaciones quedaron como INICIAL")
    
    # Resumen
    print("\n" + "=" * 80)
    print("RESUMEN DE ACTUALIZACIÓN")
    print("=" * 80)
    print(f"Total procesado: {finalizadas + en_proceso + iniciales}")
    print(f"  - FINALIZADO: {finalizadas}")
    print(f"  - EN_PROCESO: {en_proceso}")
    print(f"  - INICIAL: {iniciales}")
    print("=" * 80)
    print("\n✅ Actualización completada exitosamente")

if __name__ == '__main__':
    main()
