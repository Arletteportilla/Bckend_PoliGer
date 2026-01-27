# Generated migration for automatic alerts system

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0056_add_cantidad_solicitada_disponible'),
    ]

    operations = [
        # Agregar campos de alertas a Polinización
        migrations.AddField(
            model_name='polinizacion',
            name='fecha_ultima_revision',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Fecha última revisión'),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='fecha_proxima_revision',
            field=models.DateField(blank=True, null=True, verbose_name='Fecha próxima revisión'),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='alerta_revision_enviada',
            field=models.BooleanField(default=False, verbose_name='Alerta de revisión enviada'),
        ),
        migrations.AddField(
            model_name='polinizacion',
            name='recordatorio_5_dias_enviado',
            field=models.BooleanField(default=False, help_text='Indica si ya se envió el recordatorio de 5 días después de la fecha de polinización', verbose_name='Recordatorio 5 días enviado'),
        ),
        # Agregar campo de recordatorio a Germinación
        migrations.AddField(
            model_name='germinacion',
            name='recordatorio_5_dias_enviado',
            field=models.BooleanField(default=False, help_text='Indica si ya se envió el recordatorio de 5 días después de la fecha de siembra', verbose_name='Recordatorio 5 días enviado'),
        ),
        # Actualizar choices del tipo de notificación para incluir RECORDATORIO_5_DIAS
        migrations.AlterField(
            model_name='notification',
            name='tipo',
            field=models.CharField(choices=[
                ('NUEVA_GERMINACION', 'Nueva Germinación'),
                ('RECORDATORIO_REVISION', 'Recordatorio de Revisión'),
                ('RECORDATORIO_5_DIAS', 'Recordatorio 5 Días'),
                ('ESTADO_ACTUALIZADO', 'Estado Actualizado'),
                ('NUEVA_POLINIZACION', 'Nueva Polinización'),
                ('ESTADO_POLINIZACION_ACTUALIZADO', 'Estado de Polinización Actualizado'),
                ('MENSAJE', 'Mensaje'),
                ('ERROR', 'Error'),
                ('ACTUALIZACION', 'Actualización'),
            ], max_length=35),
        ),
    ]
