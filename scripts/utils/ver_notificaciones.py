"""
Script para ver las notificaciones actuales en la base de datos
"""
import os
import sys
import django
from pathlib import Path

# Agregar el directorio raíz del backend al path
backend_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.models import Notification
from django.contrib.auth.models import User

def ver_notificaciones():
    """Muestra las notificaciones actuales"""
    print("\n" + "=" * 80)
    print("NOTIFICACIONES EN LA BASE DE DATOS")
    print("=" * 80)
    
    user = User.objects.first()
    if not user:
        print("❌ No hay usuarios en la base de datos")
        return
    
    print(f"\n👤 Usuario: {user.username} ({user.first_name} {user.last_name})")
    
    # Contar notificaciones
    total = Notification.objects.filter(usuario=user).count()
    print(f"\n📊 Total de notificaciones: {total}")
    
    if total == 0:
        print("\n✅ No hay notificaciones en la base de datos.")
        print("   Las notificaciones se crearán automáticamente cuando:")
        print("   - Crees una nueva germinación")
        print("   - Crees una nueva polinización")
        print("   - Cambies el estado de un registro")
        return
    
    # Mostrar últimas 10 notificaciones
    notifs = Notification.objects.filter(usuario=user).order_by('-fecha_creacion')[:10]
    
    print(f"\n📋 Últimas 10 notificaciones:")
    print("-" * 80)
    
    for i, n in enumerate(notifs, 1):
        print(f"\n{i}. [{n.tipo}] {n.titulo}")
        print(f"   📅 Fecha: {n.fecha_creacion.strftime('%d/%m/%Y %H:%M')}")
        print(f"   👁️ Leída: {'Sí' if n.leida else 'No'}")
        print(f"   ⭐ Favorita: {'Sí' if n.favorita else 'No'}")
        print(f"   📦 Archivada: {'Sí' if n.archivada else 'No'}")
        
        if n.germinacion_id:
            print(f"   🌱 Germinación ID: {n.germinacion_id}")
        if n.polinizacion_id:
            print(f"   🌸 Polinización ID: {n.polinizacion_id}")
        
        print(f"   💬 Mensaje: {n.mensaje[:100]}...")
    
    # Estadísticas
    print("\n" + "=" * 80)
    print("ESTADÍSTICAS")
    print("=" * 80)
    
    no_leidas = Notification.objects.filter(usuario=user, leida=False).count()
    favoritas = Notification.objects.filter(usuario=user, favorita=True).count()
    archivadas = Notification.objects.filter(usuario=user, archivada=True).count()
    
    print(f"\n📊 No leídas: {no_leidas}")
    print(f"⭐ Favoritas: {favoritas}")
    print(f"📦 Archivadas: {archivadas}")
    
    # Por tipo
    print(f"\n📋 Por tipo:")
    tipos = Notification.objects.filter(usuario=user).values_list('tipo', flat=True)
    from collections import Counter
    tipo_counts = Counter(tipos)
    for tipo, count in tipo_counts.most_common():
        print(f"   - {tipo}: {count}")
    
    print("\n" + "=" * 80)
    
    # Verificar si son de prueba o del sistema
    print("\n🔍 ANÁLISIS:")
    
    # Verificar si hay notificaciones con germinaciones/polinizaciones reales
    con_germinacion = Notification.objects.filter(usuario=user, germinacion__isnull=False).count()
    con_polinizacion = Notification.objects.filter(usuario=user, polinizacion__isnull=False).count()
    sin_registro = Notification.objects.filter(usuario=user, germinacion__isnull=True, polinizacion__isnull=True).count()
    
    print(f"\n   - Con germinación asociada: {con_germinacion}")
    print(f"   - Con polinización asociada: {con_polinizacion}")
    print(f"   - Sin registro asociado: {sin_registro}")
    
    if sin_registro > 0:
        print("\n   ⚠️ Hay notificaciones sin registro asociado.")
        print("   Estas pueden ser:")
        print("   - Notificaciones de prueba creadas manualmente")
        print("   - Notificaciones del sistema (mensajes, errores, actualizaciones)")
        print("   - Notificaciones de registros eliminados")
    
    if con_germinacion > 0 or con_polinizacion > 0:
        print("\n   ✅ Hay notificaciones del sistema asociadas a registros reales.")
        print("   Estas se crearon automáticamente al crear/actualizar registros.")

if __name__ == '__main__':
    ver_notificaciones()
