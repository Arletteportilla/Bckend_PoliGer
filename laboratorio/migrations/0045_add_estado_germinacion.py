# Generated migration for adding estado_germinacion field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0044_add_ml_prediction_fields_polinizacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='germinacion',
            name='estado_germinacion',
            field=models.CharField(
                choices=[
                    ('INICIAL', 'Inicial'),
                    ('EN_PROCESO', 'En Proceso'),
                    ('FINALIZADO', 'Finalizado')
                ],
                default='INICIAL',
                help_text='Estado del proceso de germinación',
                max_length=20,
                verbose_name='Estado de Germinación'
            ),
        ),
    ]
