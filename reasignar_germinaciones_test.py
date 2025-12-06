#!/usr/bin/env python
"""
Script para reasignar algunas germinaciones a otros usuarios (para testing)
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

def main():
    print("=" * 80)
    print("REASIGNAR GERMINACIONES PARA TESTING")
    print("=" * 80)
    
    # Obtener usuarios
    usuarios = list(User.objects.all())
    print(f"\n👥 Usuarios disponibles: {len(usuarios)}")
    for u in usuarios:
        print(f"  - {u.username} (ID: {u.id})")
    
    if len(usuarios) < 2:
        print("\n⚠️ Se necesitan al menos 2 usuarios para reasignar germinaciones")
        print("Crea más usuarios primero")
        return
    
    # Reasignar las primeras 100 germinaciones a cada usuario
    print(f"\n🔄 Reasignando germinaciones...")
    
    germinaciones = Germinacion.objects.all().order_by('id')[:500]
    
    for i, germ in enumerate(germinaciones):
        # Asignar a diferentes usuarios de forma rotativa
        usuario_index = i % len(usuarios)
        germ.creado_por = usuarios[usuario_index]
        germ.save()
    
    print(f"✅ {len(germinaciones)} germinaciones reasignadas")
    
    # Mostrar nueva distribución
    print("\n📊 Nueva distribución:")
    from django.db.models import Count
    stats = Germinacion.objects.values('creado_por__username').annotate(
        total=Count('id')
    ).order_by('-total')
    
    for stat in stats:
        print(f"  {stat['creado_por__username']}: {stat['total']} germinaciones")

if __name__ == '__main__':
    main()
