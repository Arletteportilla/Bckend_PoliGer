# Generated migration for adding progreso_germinacion field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0045_add_estado_germinacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='germinacion',
            name='progreso_germinacion',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Porcentaje de progreso de la germinación (0-100%)',
                verbose_name='Progreso de Germinación (%)'
            ),
        ),
    ]
