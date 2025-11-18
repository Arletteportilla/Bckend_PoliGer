from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from laboratorio.models import UserProfile


class Command(BaseCommand):
    help = 'Crear un usuario administrador con permisos completos del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Nombre de usuario para el administrador (default: admin)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Contraseña para el administrador (default: admin123)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@poliger.com',
            help='Email para el administrador (default: admin@poliger.com)'
        )
        parser.add_argument(
            '--first-name',
            type=str,
            default='Administrador',
            help='Nombre del administrador (default: Administrador)'
        )
        parser.add_argument(
            '--last-name',
            type=str,
            default='Sistema',
            help='Apellido del administrador (default: Sistema)'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']
        first_name = options['first_name']
        last_name = options['last_name']
        
        try:
            # Verificar si ya existe el usuario
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                self.stdout.write(
                    self.style.WARNING(f'El usuario "{username}" ya existe.')
                )
                
                # Preguntar si se quiere actualizar
                confirm = input('¿Desea actualizar este usuario con permisos de administrador? (s/N): ')
                if confirm.lower() != 's':
                    self.stdout.write(
                        self.style.SUCCESS('Operación cancelada.')
                    )
                    return
                
                # Actualizar usuario existente
                user.email = email
                user.first_name = first_name
                user.last_name = last_name
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Usuario "{username}" actualizado exitosamente.')
                )
            else:
                # Crear nuevo usuario administrador
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    email=email,
                    first_name=first_name,
                    last_name=last_name
                )
                
                # Hacer al usuario staff y superuser
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Usuario administrador "{username}" creado exitosamente.')
                )
            
            # Verificar o crear perfil de usuario con rol de Gestor del Sistema (TIPO_4)
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'rol': 'TIPO_4',  # Gestor del Sistema - Acceso total
                    'activo': True,
                    'departamento': 'Administración',
                    'telefono': '000-000-0000',
                    # Configurar metas altas para el administrador
                    'meta_polinizaciones': 50,
                    'meta_germinaciones': 50,
                    'tasa_exito_objetivo': 95
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Perfil de usuario creado con rol: {profile.get_rol_display()}')
                )
            else:
                # Actualizar el perfil existente para asegurar permisos completos
                profile.rol = 'TIPO_4'
                profile.activo = True
                if not profile.departamento:
                    profile.departamento = 'Administración'
                profile.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'Perfil de usuario actualizado con rol: {profile.get_rol_display()}')
                )
            
            # Mostrar información del usuario creado/actualizado
            self.stdout.write(
                self.style.SUCCESS('\n' + '='*50)
            )
            self.stdout.write(
                self.style.SUCCESS('INFORMACIÓN DEL USUARIO ADMINISTRADOR:')
            )
            self.stdout.write(
                self.style.SUCCESS('='*50)
            )
            self.stdout.write(f'Username: {user.username}')
            self.stdout.write(f'Email: {user.email}')
            self.stdout.write(f'Nombre: {user.first_name} {user.last_name}')
            self.stdout.write(f'Password: {password}')
            self.stdout.write(f'Es Staff: {user.is_staff}')
            self.stdout.write(f'Es Superuser: {user.is_superuser}')
            self.stdout.write(f'Rol del Sistema: {profile.get_rol_display()}')
            
            # Mostrar permisos específicos
            self.stdout.write(
                self.style.SUCCESS('\nPERMISOS DEL USUARIO:')
            )
            self.stdout.write(
                self.style.SUCCESS('-' * 30)
            )
            permisos = profile.get_permisos_detallados()
            
            for modulo, permisos_modulo in permisos.items():
                self.stdout.write(f'\n{modulo.upper()}:')
                for accion, tiene_permiso in permisos_modulo.items():
                    status = "✓" if tiene_permiso else "✗"
                    self.stdout.write(f'  {status} {accion}')
            
            self.stdout.write(
                self.style.SUCCESS('\n' + '='*50)
            )
            self.stdout.write(
                self.style.SUCCESS('Usuario administrador listo para usar!')
            )
            self.stdout.write(
                self.style.SUCCESS('Puede acceder al panel de administración Django y a todas las funciones del sistema.')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al crear/actualizar usuario administrador: {e}')
            )