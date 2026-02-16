import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.core.models import Germinacion

gs = Germinacion.objects.filter(codigo='PHE13954')
print(f'Total registros con codigo PHE13954: {gs.count()}')
print('-' * 80)

for g in gs:
    print(f'ID: {g.id}')
    print(f'Codigo: {g.codigo}')
    print(f'Especie: {g.especie_variedad}')
    print(f'fecha_siembra: {g.fecha_siembra}')
    print(f'prediccion_fecha_estimada: {g.prediccion_fecha_estimada}')
    print(f'prediccion_dias_estimados: {g.prediccion_dias_estimados}')
    print(f'prediccion_confianza: {g.prediccion_confianza}')
    print(f'estado_germinacion: {g.estado_germinacion}')
    print(f'etapa_actual: {g.etapa_actual}')
    print('-' * 80)
