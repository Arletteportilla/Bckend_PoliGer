from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from laboratorio.models import UserProfile


class Command(BaseCommand):
    help = 'Crear perfiles para usuarios existentes que no tengan perfil'

    def add_arguments(self, parser):
        parser.add_argument(
            '--default-role',
            type=str,
            default='TIPO_3',
            help='Rol por defecto para usuarios sin perfil (default: TIPO_3)'
        )

    def handle(self, *args, **options):
        default_role = options['default_role']
        
        # Verificar que el rol sea válido
        valid_roles = [choice[0] for choice in UserProfile.ROLES_CHOICES]
        if default_role not in valid_roles:
            self.stdout.write(
                self.style.ERROR(f'Rol inválido: {default_role}. Roles válidos: {valid_roles}')
            )
            return
        
        # Obtener usuarios sin perfil
        users_without_profile = User.objects.filter(profile__isnull=True)
        
        if not users_without_profile.exists():
            self.stdout.write(
                self.style.SUCCESS('Todos los usuarios ya tienen perfil asignado.')
            )
            return
        
        # Crear perfiles para usuarios sin perfil
        profiles_created = 0
        for user in users_without_profile:
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'rol': default_role,
                    'activo': True
                }
            )
            
            if created:
                profiles_created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Perfil creado para usuario: {user.username} (Rol: {default_role})'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Se crearon {profiles_created} perfiles de usuario con rol {default_role}'
            )
        )