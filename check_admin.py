from django.contrib.auth.models import User
from django.db import models
from laboratorio.core.models import UserProfile, Germinacion, Polinizacion

try:
    admin = User.objects.filter(username='admin').first()

    if admin:
        print(f"Admin user exists: {admin.username}")
        print(f"  Email: {admin.email}")
        print(f"  Is superuser: {admin.is_superuser}")
        print(f"  Is staff: {admin.is_staff}")

        if hasattr(admin, 'profile'):
            print(f"Admin has profile")
            print(f"  Rol: {admin.profile.rol} ({admin.profile.get_rol_display()})")
            print(f"  Activo: {admin.profile.activo}")
        else:
            print("Admin has NO profile - THIS IS A PROBLEM")
    else:
        print("Admin user does NOT exist - THIS IS A PROBLEM")

    print(f"\n--- DATA STATISTICS ---")
    total_germ = Germinacion.objects.count()
    total_poli = Polinizacion.objects.count()

    print(f"Total Germinaciones in DB: {total_germ}")
    print(f"Total Polinizaciones in DB: {total_poli}")

    if admin:
        germ_by_admin = Germinacion.objects.filter(creado_por=admin).count()
        poli_by_admin = Polinizacion.objects.filter(creado_por=admin).count()

        print(f"\nGerminaciones created by admin: {germ_by_admin}")
        print(f"Polinizaciones created by admin: {poli_by_admin}")

        if total_germ > 0:
            print(f"\n--- GERMINACIONES BY USER ---")
            users_germ = Germinacion.objects.values('creado_por__username').annotate(
                count=models.Count('id')
            ).order_by('-count')
            for user_data in users_germ:
                username = user_data['creado_por__username'] or 'None'
                count = user_data['count']
                print(f"  {username}: {count}")

        if total_poli > 0:
            print(f"\n--- POLINIZACIONES BY USER ---")
            users_poli = Polinizacion.objects.values('creado_por__username').annotate(
                count=models.Count('id')
            ).order_by('-count')
            for user_data in users_poli:
                username = user_data['creado_por__username'] or 'None'
                count = user_data['count']
                print(f"  {username}: {count}")

        print(f"\n--- CONCLUSION ---")
        if germ_by_admin == 0 and total_germ > 0:
            print("PROBLEM: Admin created 0 germinaciones but there are records in DB")
            print("Solution: Admin dashboard is filtering by creado_por=admin, so it shows 0")

        if poli_by_admin == 0 and total_poli > 0:
            print("PROBLEM: Admin created 0 polinizaciones but there are records in DB")
            print("Solution: Admin dashboard is filtering by creado_por=admin, so it shows 0")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
