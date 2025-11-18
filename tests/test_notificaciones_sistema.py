#!/usr/bin/env python
"""
Script para probar el sistema de notificaciones automáticas
"""
import os
import sys
import django
from datetime import date
from pathlib import Path

# Agregar el directorio raíz del backend al path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.models import Germinacion, Polinizacion, Notification, User

print("=" * 80)
print("PRUEBA DEL SISTEMA DE NOTIFICACIONES AUTOMÁTICAS")
print("=" * 80)

# Obtener usuario admin
try:
    user = User.objects.get(username='admin')
    print(f"\n✅ Usuario encontrado: {user.username}")
except User.DoesNotExist:
    print("\n❌ Usuario 'admin' no encontrado")
    exit(1)

# Contar notificaciones antes
notif_antes = Notification.objects.filter(usuario=user).count()
print(f"\n📊 Notificaciones antes: {notif_antes}")

# Crear una germinación de prueba
print("\n🌱 Creando germinación de prueba...")
germinacion = Germinacion.objects.create(
    codigo=f"TEST-GER-{date.today().strftime('%Y%m%d')}",
    fecha_siembra=date.today(),
    fecha_polinizacion=date.today(),
    genero="Cattleya",
    especie_variedad="Test Variedad",
    clima="I",
    cantidad_solicitada=10,
    no_capsulas=1,
    estado_capsula="CERRADA",
    observaciones="Germinación de prueba para notificaciones",
    creado_por=user
)
print(f"✅ Germinación creada: {germinacion.codigo}")

# Crear una polinización de prueba
print("\n🌸 Creando polinización de prueba...")
polinizacion = Polinizacion.objects.create(
    codigo=f"TEST-POL-{date.today().strftime('%Y%m%d')}",
    fechapol=date.today(),
    tipo_polinizacion="SELF",
    madre_genero="Cattleya",
    madre_especie="Test Especie",
    nueva_genero="Cattleya",
    nueva_especie="Test Híbrido",
    cantidad_capsulas=1,
    observaciones="Polinización de prueba para notificaciones",
    creado_por=user
)
print(f"✅ Polinización creada: {polinizacion.codigo}")

# Contar notificaciones después
notif_despues = Notification.objects.filter(usuario=user).count()
print(f"\n📊 Notificaciones después: {notif_despues}")
print(f"📈 Nuevas notificaciones: {notif_despues - notif_antes}")

# Mostrar las nuevas notificaciones
print("\n" + "=" * 80)
print("NUEVAS NOTIFICACIONES CREADAS")
print("=" * 80)

nuevas_notificaciones = Notification.objects.filter(
    usuario=user
).order_by('-fecha_creacion')[:2]

for i, notif in enumerate(nuevas_notificaciones, 1):
    print(f"\n{i}. [{notif.tipo}] {notif.titulo}")
    print(f"   📅 Fecha: {notif.fecha_creacion.strftime('%d/%m/%Y %H:%M')}")
    print(f"   💬 Mensaje: {notif.mensaje[:100]}...")
    if notif.germinacion:
        print(f"   🌱 Germinación: {notif.germinacion.codigo_germinacion}")
    if notif.polinizacion:
        print(f"   🌸 Polinización: {notif.polinizacion.codigo_polinizacion}")
    print(f"   🔗 Datos: {notif.datos}")

print("\n" + "=" * 80)
print("✅ PRUEBA COMPLETADA")
print("=" * 80)
print("\n🎯 Verifica en el frontend que aparezcan las notificaciones con:")
print("   - Botones de acción rápida")
print("   - Predicciones de fechas")
print("   - Enlaces a los registros")
