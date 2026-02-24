from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0059_increase_nueva_especie_max_length'),
    ]

    operations = [
        migrations.AlterField(
            model_name='polinizacion',
            name='estado_polinizacion',
            field=models.CharField(
                choices=[
                    ('INICIAL', 'Inicial'),
                    ('EN_PROCESO', 'En Proceso'),
                    ('EN_PROCESO_TEMPRANO', 'En Proceso - Temprano'),
                    ('EN_PROCESO_AVANZADO', 'En Proceso - Avanzado'),
                    ('FINALIZADO', 'Finalizado'),
                ],
                default='INICIAL',
                help_text='Estado del proceso de polinización',
                max_length=20,
                verbose_name='Estado de Polinización',
            ),
        ),
    ]
