import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.core.management import call_command

# Forzar UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Exportar con UTF-8
with open('full_db_backup.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata',
                 '--natural-foreign',
                 '--natural-primary',
                 '--indent', '2',
                 stdout=f)

print("✅ Base de datos exportada correctamente a full_db_backup.json")
