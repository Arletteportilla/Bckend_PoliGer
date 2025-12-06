#!/usr/bin/env python
"""
Script para aplicar la migración del nuevo campo estado_germinacion
y actualizar los registros existentes
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.core.management import call_command
from laboratorio.models import Germinacion

def main():
    print("=" * 80)
    print("APLICANDO MIGRACIÓN: estado_germinacion")
    print("=" * 80)
    
    # 1. Crear y aplicar migración
    print("\n1. Creando migración...")
    try:
        call_command('makemigrations', 'laboratorio')
        print("✅ Migración creada exitosamente")
    except Exception as e:
        print(f"⚠️ Advertencia al crear migración: {e}")
    
    print("\n2. Aplicando migración...")
    try:
        call_command('migrate', 'laboratorio')
        print("✅ Migración aplicada exitosamente")
    except Exception as e:
        print(f"❌ Error al aplicar migración: {e}")
        return
    
    # 2. Actualizar registros existentes
    print("\n3. Actualizando registros existentes...")
    try:
        # Contar germinaciones
        total = Germinacion.objects.count()
        print(f"   Total de germinaciones: {total}")
        
        # Actualizar según fecha_germinacion
        finalizadas = Germinacion.objects.filter(
            fecha_germinacion__isnull=False
        ).update(estado_germinacion='FINALIZADO')
        print(f"   ✅ {finalizadas} germinaciones marcadas como FINALIZADO")
        
        # Las que tienen fecha de siembra pero no de germinación -> EN_PROCESO
        en_proceso = Germinacion.objects.filter(
            fecha_germinacion__isnull=True,
            fecha_siembra__isnull=False
        ).update(estado_germinacion='EN_PROCESO')
        print(f"   ✅ {en_proceso} germinaciones marcadas como EN_PROCESO")
        
        # Las demás -> INICIAL
        iniciales = Germinacion.objects.filter(
            estado_germinacion='INICIAL'
        ).count()
        print(f"   ✅ {iniciales} germinaciones quedaron como INICIAL")
        
        print(f"\n✅ Actualización completada: {finalizadas + en_proceso + iniciales} registros procesados")
        
    except Exception as e:
        print(f"❌ Error actualizando registros: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("MIGRACIÓN COMPLETADA")
    print("=" * 80)
    print("\nPróximos pasos:")
    print("1. Reiniciar el servidor Django")
    print("2. Verificar que el campo estado_germinacion aparece en el admin")
    print("3. Probar el endpoint: POST /api/germinaciones/{id}/cambiar-estado/")
    print("=" * 80)

if __name__ == '__main__':
    main()
