# Generated migration to rename usuario field to user in UserProfile

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0001_initial'),  # Ajustar según tu última migración
    ]

    operations = [
        migrations.RenameField(
            model_name='userprofile',
            old_name='usuario',
            new_name='user',
        ),
    ]
