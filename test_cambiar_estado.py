#!/usr/bin/env python
"""
Script para probar el endpoint de cambiar estado
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.models import Germinacion
from django.contrib.auth.models import User

def test_cambiar_estado():
    print("=" * 80)
    print("PROBANDO CAMBIO DE ESTADO")
    print("=" * 80)
    
    # Obtener una germinación de prueba
    germinacion = Germinacion.objects.filter(estado_germinacion='EN_PROCESO').first()
    
    if not germinacion:
        print("❌ No se encontró ninguna germinación EN_PROCESO")
        return
    
    print(f"\n📊 Germinación de prueba:")
    print(f"   ID: {germinacion.id}")
    print(f"   Código: {germinacion.codigo}")
    print(f"   Estado actual: {germinacion.estado_germinacion}")
    print(f"   Progreso actual: {germinacion.progreso_germinacion}%")
    
    # Probar cambio de estado
    print(f"\n🔄 Cambiando estado a FINALIZADO...")
    try:
        germinacion.estado_germinacion = 'FINALIZADO'
        germinacion.progreso_germinacion = 100
        germinacion.save()
        print(f"✅ Estado cambiado exitosamente")
        print(f"   Nuevo estado: {germinacion.estado_germinacion}")
        print(f"   Nuevo progreso: {germinacion.progreso_germinacion}%")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Probar método actualizar_estado_por_progreso
    print(f"\n🔄 Probando actualizar_estado_por_progreso con 60%...")
    try:
        germinacion.progreso_germinacion = 60
        germinacion.actualizar_estado_por_progreso()
        germinacion.save()
        print(f"✅ Método ejecutado exitosamente")
        print(f"   Nuevo estado: {germinacion.estado_germinacion}")
        print(f"   Nuevo progreso: {germinacion.progreso_germinacion}%")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_cambiar_estado()
