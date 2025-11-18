"""
Script para gestionar usuarios del sistema
Uso: python gestionar_usuarios.py [opciones]
"""
import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from laboratorio.core.models import UserProfile

def listar_usuarios():
    """Lista todos los usuarios del sistema"""
    usuarios = User.objects.all()

    print("\n" + "="*80)
    print("USUARIOS DEL SISTEMA")
    print("="*80)

    for u in usuarios:
        perfil = getattr(u, 'profile', None)
        rol = perfil.rol if perfil else 'Sin perfil'
        rol_display = perfil.get_rol_display() if perfil else 'Sin perfil'
        activo = 'SI' if u.is_active else 'NO'

        print(f"\nID: {u.id}")
        print(f"  Usuario: {u.username}")
        print(f"  Email: {u.email}")
        print(f"  Nombre: {u.first_name} {u.last_name}".strip())
        print(f"  Rol: {rol} ({rol_display})")
        print(f"  Activo: {activo}")
        print(f"  Superusuario: {'SI' if u.is_superuser else 'NO'}")
        print(f"  Fecha registro: {u.date_joined}")

    print("\n" + "="*80)
    print(f"Total de usuarios: {usuarios.count()}")
    print("="*80 + "\n")

def crear_usuario(username, password, email, rol='TIPO_3', is_superuser=False):
    """Crea un nuevo usuario"""

    if User.objects.filter(username=username).exists():
        print(f"[ERROR] El usuario '{username}' ya existe")
        return False

    try:
        # Crear usuario
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_superuser=is_superuser,
            is_staff=is_superuser
        )

        # Crear perfil
        profile = UserProfile.objects.create(
            usuario=user,
            rol=rol,
            activo=True
        )

        print(f"[OK] Usuario '{username}' creado exitosamente")
        print(f"     Email: {email}")
        print(f"     Rol: {rol} ({profile.get_rol_display()})")
        print(f"     Superusuario: {'SI' if is_superuser else 'NO'}")

        return True
    except Exception as e:
        print(f"[ERROR] Error creando usuario: {e}")
        return False

def resetear_password(username, nueva_password):
    """Resetea la contraseña de un usuario"""

    try:
        user = User.objects.get(username=username)
        user.set_password(nueva_password)
        user.save()

        print(f"[OK] Contraseña actualizada para usuario '{username}'")
        return True
    except User.DoesNotExist:
        print(f"[ERROR] Usuario '{username}' no existe")
        return False
    except Exception as e:
        print(f"[ERROR] Error actualizando contraseña: {e}")
        return False

def cambiar_rol(username, nuevo_rol):
    """Cambia el rol de un usuario"""

    roles_validos = ['TIPO_1', 'TIPO_2', 'TIPO_3', 'TIPO_4']

    if nuevo_rol not in roles_validos:
        print(f"[ERROR] Rol inválido. Roles válidos: {', '.join(roles_validos)}")
        return False

    try:
        user = User.objects.get(username=username)
        profile, created = UserProfile.objects.get_or_create(usuario=user)

        rol_anterior = profile.rol
        profile.rol = nuevo_rol
        profile.save()

        print(f"[OK] Rol actualizado para usuario '{username}'")
        print(f"     Rol anterior: {rol_anterior}")
        print(f"     Rol nuevo: {nuevo_rol} ({profile.get_rol_display()})")

        return True
    except User.DoesNotExist:
        print(f"[ERROR] Usuario '{username}' no existe")
        return False
    except Exception as e:
        print(f"[ERROR] Error cambiando rol: {e}")
        return False

def activar_desactivar_usuario(username, activar=True):
    """Activa o desactiva un usuario"""

    try:
        user = User.objects.get(username=username)
        user.is_active = activar
        user.save()

        accion = "activado" if activar else "desactivado"
        print(f"[OK] Usuario '{username}' {accion}")

        return True
    except User.DoesNotExist:
        print(f"[ERROR] Usuario '{username}' no existe")
        return False
    except Exception as e:
        print(f"[ERROR] Error activando/desactivando usuario: {e}")
        return False

def menu_interactivo():
    """Menú interactivo para gestionar usuarios"""

    while True:
        print("\n" + "="*80)
        print("GESTIÓN DE USUARIOS - POLIGER")
        print("="*80)
        print("1. Listar usuarios")
        print("2. Crear usuario")
        print("3. Resetear contraseña")
        print("4. Cambiar rol")
        print("5. Activar/Desactivar usuario")
        print("6. Salir")
        print("="*80)

        opcion = input("\nSeleccione una opción: ").strip()

        if opcion == '1':
            listar_usuarios()

        elif opcion == '2':
            print("\n--- CREAR USUARIO ---")
            username = input("Usuario: ").strip()
            password = input("Contraseña: ").strip()
            email = input("Email: ").strip()

            print("\nRoles disponibles:")
            print("  TIPO_1 - Usuario con permisos limitados")
            print("  TIPO_2 - Usuario con permisos intermedios")
            print("  TIPO_3 - Usuario con permisos avanzados")
            print("  TIPO_4 - Administrador (todos los permisos)")

            rol = input("Rol (default: TIPO_3): ").strip() or 'TIPO_3'
            is_superuser = input("¿Es superusuario? (s/n): ").strip().lower() == 's'

            crear_usuario(username, password, email, rol, is_superuser)

        elif opcion == '3':
            print("\n--- RESETEAR CONTRASEÑA ---")
            username = input("Usuario: ").strip()
            nueva_password = input("Nueva contraseña: ").strip()

            resetear_password(username, nueva_password)

        elif opcion == '4':
            print("\n--- CAMBIAR ROL ---")
            username = input("Usuario: ").strip()

            print("\nRoles disponibles:")
            print("  TIPO_1 - Usuario con permisos limitados")
            print("  TIPO_2 - Usuario con permisos intermedios")
            print("  TIPO_3 - Usuario con permisos avanzados")
            print("  TIPO_4 - Administrador (todos los permisos)")

            nuevo_rol = input("Nuevo rol: ").strip()

            cambiar_rol(username, nuevo_rol)

        elif opcion == '5':
            print("\n--- ACTIVAR/DESACTIVAR USUARIO ---")
            username = input("Usuario: ").strip()
            activar = input("¿Activar? (s/n): ").strip().lower() == 's'

            activar_desactivar_usuario(username, activar)

        elif opcion == '6':
            print("\n¡Hasta luego!")
            break

        else:
            print("\n[ERROR] Opción inválida")

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Gestionar usuarios del sistema')
    parser.add_argument('--listar', action='store_true', help='Listar todos los usuarios')
    parser.add_argument('--crear', metavar='USERNAME', help='Crear un nuevo usuario')
    parser.add_argument('--password', metavar='PASSWORD', help='Contraseña para el nuevo usuario')
    parser.add_argument('--email', metavar='EMAIL', help='Email para el nuevo usuario')
    parser.add_argument('--rol', metavar='ROL', default='TIPO_3', help='Rol del usuario (TIPO_1, TIPO_2, TIPO_3, TIPO_4)')
    parser.add_argument('--superuser', action='store_true', help='Crear como superusuario')
    parser.add_argument('--resetear-password', metavar='USERNAME', help='Resetear contraseña de un usuario')
    parser.add_argument('--nueva-password', metavar='PASSWORD', help='Nueva contraseña')
    parser.add_argument('--cambiar-rol', metavar='USERNAME', help='Cambiar rol de un usuario')
    parser.add_argument('--nuevo-rol', metavar='ROL', help='Nuevo rol para el usuario')

    args = parser.parse_args()

    # Si no hay argumentos, mostrar menú interactivo
    if len(sys.argv) == 1:
        menu_interactivo()
    else:
        if args.listar:
            listar_usuarios()

        if args.crear:
            if not args.password or not args.email:
                print("[ERROR] Se requiere --password y --email para crear un usuario")
            else:
                crear_usuario(args.crear, args.password, args.email, args.rol, args.superuser)

        if args.resetear_password:
            if not args.nueva_password:
                print("[ERROR] Se requiere --nueva-password")
            else:
                resetear_password(args.resetear_password, args.nueva_password)

        if args.cambiar_rol:
            if not args.nuevo_rol:
                print("[ERROR] Se requiere --nuevo-rol")
            else:
                cambiar_rol(args.cambiar_rol, args.nuevo_rol)
