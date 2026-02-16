import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.core.models import Germinacion
from laboratorio.services.ml_prediccion_service import MLPrediccionService

# Obtener el registro
g = Germinacion.objects.get(id=28645)

print(f'Calculando predicción para: {g.codigo}')
print(f'Fecha siembra: {g.fecha_siembra}')
print(f'Especie: {g.especie_variedad}')
print(f'Clima: {g.clima}')
print(f'Estado cápsula: {g.estado_capsula}')

# Calcular predicción
service = MLPrediccionService()
try:
    resultado = service.predecir(
        fecha_siembra=str(g.fecha_siembra),
        especie=g.especie_variedad or '',
        clima=g.clima or 'I',
        estado_capsula=g.estado_capsula or 'CERRADA',
        s_stock=g.cantidad_solicitada or 0,
        c_solic=g.no_capsulas or 0,
        dispone=0
    )

    print(f'\n✅ Predicción calculada:')
    print(f'Días estimados: {resultado.get("dias_estimados")}')
    print(f'Fecha estimada: {resultado.get("fecha_estimada_germinacion")}')
    print(f'Confianza: {resultado.get("confianza")}')

    # Guardar en el modelo
    g.prediccion_dias_estimados = resultado.get('dias_estimados')
    g.prediccion_fecha_estimada = resultado.get('fecha_estimada_germinacion')
    g.prediccion_confianza = resultado.get('confianza')
    g.prediccion_tipo = resultado.get('modelo', 'ML')
    g.save()

    print(f'\n✅ Predicción guardada en la base de datos')

except Exception as e:
    print(f'\n❌ Error: {e}')
    import traceback
    traceback.print_exc()
