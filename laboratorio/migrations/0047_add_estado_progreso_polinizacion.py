# Generated migration for adding estado_polinizacion and progreso_polinizacion fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0046_add_progreso_germinacion'),
    ]

    operations = [
        migrations.AddField(
            model_name='polinizacion',
            name='estado_polinizacion',
            field=models.CharField(
                choices=[
                    ('INICIAL', 'Inicial'),
                    ('EN_PROCESO', 'En Proceso'),
                    ('FINALIZADO', 'Finalizado'),
                ],
                default='INICIAL',
                help_text='Estado del proceso de polinización',
                max_length=20,
                verbose_name='Estado de Polinización'
            ),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='progreso_polinizacion',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Porcentaje de progreso de la polinización (0-100%)',
                verbose_name='Progreso de Polinización (%)'
            ),
        ),
    ]
