#!/usr/bin/env python
"""
Script para verificar la distribución de germinaciones por usuario
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
from django.db.models import Count

def main():
    print("=" * 80)
    print("DISTRIBUCIÓN DE GERMINACIONES POR USUARIO")
    print("=" * 80)
    
    # Total de germinaciones
    total = Germinacion.objects.count()
    print(f"\n📊 Total de germinaciones: {total}")
    
    # Total de usuarios
    total_usuarios = User.objects.count()
    print(f"👥 Total de usuarios: {total_usuarios}")
    
    # Germinaciones por usuario
    print("\n📋 Top 10 usuarios con más germinaciones:")
    stats = Germinacion.objects.values('creado_por__username').annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    for i, stat in enumerate(stats, 1):
        username = stat['creado_por__username']
        count = stat['total']
        percentage = (count / total) * 100
        print(f"  {i}. {username}: {count} germinaciones ({percentage:.1f}%)")
    
    # Verificar si hay germinaciones sin creador
    sin_creador = Germinacion.objects.filter(creado_por__isnull=True).count()
    if sin_creador > 0:
        print(f"\n⚠️ Hay {sin_creador} germinaciones sin creador asignado")
    else:
        print(f"\n✅ Todas las germinaciones tienen un creador asignado")

if __name__ == '__main__':
    main()
