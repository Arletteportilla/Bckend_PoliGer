#!/usr/bin/env python
"""Script para verificar notificaciones de recordatorio"""
import os
import sys
import django

project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.models import Notification

# Obtener notificaciones de recordatorio
notificaciones = Notification.objects.filter(
    tipo='RECORDATORIO_REVISION'
).order_by('-fecha_creacion')[:10]

print("="*70)
print(f"NOTIFICACIONES DE RECORDATORIO")
print("="*70)
print(f"\nTotal: {Notification.objects.filter(tipo='RECORDATORIO_REVISION').count()}")
print("\nÚltimas 10 notificaciones:")
print("-"*70)

for n in notificaciones:
    print(f"\n📬 {n.titulo}")
    print(f"   Usuario: {n.usuario.username}")
    print(f"   Fecha: {n.fecha_creacion.strftime('%d/%m/%Y %H:%M')}")
    print(f"   Leída: {'✅ Sí' if n.leida else '❌ No'}")
    if n.germinacion:
        print(f"   Germinación: {n.germinacion.codigo}")
    if n.polinizacion:
        print(f"   Polinización: {n.polinizacion.codigo}")

print("\n" + "="*70)
