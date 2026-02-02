"""
Management command para verificar el estado del usuario admin y estadísticas de datos.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import models
from laboratorio.core.models import UserProfile, Germinacion, Polinizacion


class Command(BaseCommand):
    help = 'Verificar estado del usuario admin y estadísticas de datos'

    def handle(self, *args, **options):
        try:
            admin = User.objects.filter(username='admin').first()

            if admin:
                self.stdout.write(f"Admin user exists: {admin.username}")
                self.stdout.write(f"  Email: {admin.email}")
                self.stdout.write(f"  Is superuser: {admin.is_superuser}")
                self.stdout.write(f"  Is staff: {admin.is_staff}")

                if hasattr(admin, 'profile'):
                    self.stdout.write(f"Admin has profile")
                    self.stdout.write(f"  Rol: {admin.profile.rol} ({admin.profile.get_rol_display()})")
                    self.stdout.write(f"  Activo: {admin.profile.activo}")
                else:
                    self.stdout.write(self.style.ERROR("Admin has NO profile - THIS IS A PROBLEM"))
            else:
                self.stdout.write(self.style.ERROR("Admin user does NOT exist - THIS IS A PROBLEM"))

            self.stdout.write(f"\n--- DATA STATISTICS ---")
            total_germ = Germinacion.objects.count()
            total_poli = Polinizacion.objects.count()

            self.stdout.write(f"Total Germinaciones in DB: {total_germ}")
            self.stdout.write(f"Total Polinizaciones in DB: {total_poli}")

            if admin:
                germ_by_admin = Germinacion.objects.filter(creado_por=admin).count()
                poli_by_admin = Polinizacion.objects.filter(creado_por=admin).count()

                self.stdout.write(f"\nGerminaciones created by admin: {germ_by_admin}")
                self.stdout.write(f"Polinizaciones created by admin: {poli_by_admin}")

                if total_germ > 0:
                    self.stdout.write(f"\n--- GERMINACIONES BY USER ---")
                    users_germ = Germinacion.objects.values('creado_por__username').annotate(
                        count=models.Count('id')
                    ).order_by('-count')
                    for user_data in users_germ:
                        username = user_data['creado_por__username'] or 'None'
                        count = user_data['count']
                        self.stdout.write(f"  {username}: {count}")

                if total_poli > 0:
                    self.stdout.write(f"\n--- POLINIZACIONES BY USER ---")
                    users_poli = Polinizacion.objects.values('creado_por__username').annotate(
                        count=models.Count('id')
                    ).order_by('-count')
                    for user_data in users_poli:
                        username = user_data['creado_por__username'] or 'None'
                        count = user_data['count']
                        self.stdout.write(f"  {username}: {count}")

                self.stdout.write(f"\n--- CONCLUSION ---")
                if germ_by_admin == 0 and total_germ > 0:
                    self.stdout.write(self.style.WARNING(
                        "PROBLEM: Admin created 0 germinaciones but there are records in DB"
                    ))
                    self.stdout.write(
                        "Solution: Admin dashboard is filtering by creado_por=admin, so it shows 0"
                    )

                if poli_by_admin == 0 and total_poli > 0:
                    self.stdout.write(self.style.WARNING(
                        "PROBLEM: Admin created 0 polinizaciones but there are records in DB"
                    ))
                    self.stdout.write(
                        "Solution: Admin dashboard is filtering by creado_por=admin, so it shows 0"
                    )

            self.stdout.write(self.style.SUCCESS("\nCheck completed successfully"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
