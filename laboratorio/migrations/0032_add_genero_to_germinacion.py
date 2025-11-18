# Generated manually to add genero field to Germinacion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0031_update_polinizacion_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='germinacion',
            name='genero',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='Género'
            ),
        ),
    ]
