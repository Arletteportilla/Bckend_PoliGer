# Generated manually to update polinizacion types

from django.db import migrations, models


def update_existing_polinizaciones(apps, schema_editor):
    """
    Actualizar los tipos de polinización existentes en la base de datos
    para que coincidan con los nuevos valores simplificados
    """
    Polinizacion = apps.get_model('laboratorio', 'Polinizacion')
    
    # Mapeo de valores antiguos a nuevos
    type_mapping = {
        'HYBRID': 'HIBRIDA',
        'Sibbling': 'SIBLING', 
        'Híbrido': 'HIBRIDA',
        'Autopolinizados': 'SELF',
    }
    
    # Actualizar registros existentes
    for old_type, new_type in type_mapping.items():
        Polinizacion.objects.filter(tipo_polinizacion=old_type).update(tipo_polinizacion=new_type)

    print("Actualizados los tipos de polinizacion existentes")


def reverse_update_polinizaciones(apps, schema_editor):
    """
    Revertir los cambios (no es posible mapear de vuelta exactamente)
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('laboratorio', '0029_update_polinizacion_choices'),
    ]

    operations = [
        # Actualizar datos existentes primero
        migrations.RunPython(update_existing_polinizaciones, reverse_update_polinizaciones),
        
        # Actualizar el campo con las nuevas opciones
        migrations.AlterField(
            model_name='polinizacion',
            name='tipo_polinizacion',
            field=models.CharField(
                blank=True,
                choices=[
                    ('SELF', 'Self'),
                    ('SIBLING', 'Sibling'),
                    ('HIBRIDA', 'Híbrida'),
                ],
                default='SELF',
                max_length=20,
                verbose_name='Tipo de polinización',
            ),
        ),
    ]
