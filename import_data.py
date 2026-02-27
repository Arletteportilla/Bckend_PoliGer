import os
import sys
import django
from django.core.management import call_command
from django.db.models.signals import post_save

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth.models import User
from laboratorio.core.models import crear_perfil_usuario

print("Deshabilitando signals...")
# Desconectar el signal que crea perfiles automáticamente
post_save.disconnect(crear_perfil_usuario, sender=User)

print("Importando datos...")
call_command('loaddata', 'full_db_backup.json')

print("Reconectando signals...")
# Reconectar el signal
post_save.connect(crear_perfil_usuario, sender=User)

print("✅ Importación completada exitosamente")
