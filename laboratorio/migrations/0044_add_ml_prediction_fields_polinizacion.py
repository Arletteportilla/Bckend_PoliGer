# Generated migration for ML prediction fields in Polinizacion

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0043_alter_polinizacion_madre_clima_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='polinizacion',
            name='dias_maduracion_predichos',
            field=models.PositiveIntegerField(verbose_name='Días de maduración predichos', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='fecha_maduracion_predicha',
            field=models.DateField(verbose_name='Fecha de maduración predicha', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='metodo_prediccion',
            field=models.CharField(max_length=50, verbose_name='Método de predicción', blank=True),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='confianza_prediccion',
            field=models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Confianza de predicción (%)', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='Tipo',
            field=models.CharField(max_length=20, verbose_name='Tipo', default='SELF', blank=True),
        ),
    ]
