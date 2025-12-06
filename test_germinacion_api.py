# -*- coding: utf-8 -*-
"""
Test de la API de Predicción de Germinación (Random Forest)
=============================================================
Verifica que el endpoint de predicción de germinación funcione correctamente
"""

import os
import sys
import django

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configurar Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from laboratorio.view_modules.prediccion_views import prediccion_germinacion_ml, germinacion_model_info

User = get_user_model()

print("="*80)
print("  TEST: API DE PREDICCIÓN DE GERMINACIÓN (Random Forest)")
print("="*80)

# Crear o obtener usuario de prueba
try:
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.create_superuser('admin', 'admin@test.com', 'admin')
        print("\nUsuario admin creado para pruebas")
    else:
        print(f"\nUsando usuario existente: {user.username}")
except Exception as e:
    print(f"\nError obteniendo usuario: {e}")
    sys.exit(1)

# Crear factory
factory = APIRequestFactory()

# =============================================================================
# TEST 1: Información del Modelo
# =============================================================================
print("\n" + "="*80)
print("  TEST 1: Información del Modelo")
print("="*80)

request = factory.get('/api/ml/germinacion/model-info/')
force_authenticate(request, user=user)

try:
    response = germinacion_model_info(request)
    print(f"\nEstatus: {response.status_code}")

    if response.status_code == 200:
        data = response.data
        print("\nINFORMACIÓN DEL MODELO:")
        print(f"  - Cargado: {data.get('loaded')}")
        print(f"  - Tipo: {data.get('model_type')}")
        print(f"  - Features: {data.get('n_features')}")
        print(f"  - Especies Top: {data.get('top_especies')}")
        print(f"  - Encoding: {data.get('encoding')}")
        print(f"  - Scaler: {data.get('scaler')}")

        print("\nPIPELINE:")
        for step in data.get('pipeline_steps', []):
            print(f"  {step}")

        print("\nMÉTRICAS:")
        metricas = data.get('metricas', {})
        for key, value in metricas.items():
            print(f"  - {key}: {value}")

        print("\n✅ TEST 1 PASADO: Modelo cargado correctamente")
    else:
        print(f"\n❌ TEST 1 FALLADO: Status {response.status_code}")
        print(f"Error: {response.data}")

except Exception as e:
    print(f"\n❌ TEST 1 FALLADO: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# TEST 2: Predicción con Datos Válidos
# =============================================================================
print("\n" + "="*80)
print("  TEST 2: Predicción con Datos Válidos")
print("="*80)

datos_prueba = {
    'fecha_siembra': '2024-12-04',
    'especie': 'Phragmipedium kovachii',
    'clima': 'IC',
    'estado_capsula': 'Cerrada',
    's_stock': 10,
    'c_solic': 2,
    'dispone': 1
}

print(f"\nDatos de entrada:")
for key, value in datos_prueba.items():
    print(f"  - {key}: {value}")

request = factory.post('/api/predicciones/germinacion/ml/', datos_prueba, format='json')
force_authenticate(request, user=user)

try:
    response = prediccion_germinacion_ml(request)
    print(f"\nEstatus: {response.status_code}")

    if response.status_code == 200:
        data = response.data
        print("\nRESULTADO DE LA PREDICCIÓN:")
        print(f"  - Días estimados: {data.get('dias_estimados')} días")
        print(f"  - Fecha estimada: {data.get('fecha_estimada_germinacion')}")
        print(f"  - Confianza: {data.get('confianza')}%")
        print(f"  - Nivel confianza: {data.get('nivel_confianza')}")
        print(f"  - Modelo: {data.get('modelo')}")

        detalles = data.get('detalles', {})
        print("\nDETALLES:")
        for key, value in detalles.items():
            print(f"  - {key}: {value}")

        print("\n✅ TEST 2 PASADO: Predicción exitosa")
    else:
        print(f"\n❌ TEST 2 FALLADO: Status {response.status_code}")
        print(f"Error: {response.data}")

except Exception as e:
    print(f"\n❌ TEST 2 FALLADO: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# TEST 3: Predicción con Especie Nueva
# =============================================================================
print("\n" + "="*80)
print("  TEST 3: Predicción con Especie Nueva (no en Top 100)")
print("="*80)

datos_especie_nueva = {
    'fecha_siembra': '2024-12-04',
    'especie': 'Especie Nueva No Vista',
    'clima': 'IC',
    'estado_capsula': 'Cerrada',
    's_stock': 5,
    'c_solic': 1,
    'dispone': 1
}

print(f"\nDatos de entrada:")
for key, value in datos_especie_nueva.items():
    print(f"  - {key}: {value}")

request = factory.post('/api/predicciones/germinacion/ml/', datos_especie_nueva, format='json')
force_authenticate(request, user=user)

try:
    response = prediccion_germinacion_ml(request)
    print(f"\nEstatus: {response.status_code}")

    if response.status_code == 200:
        data = response.data
        print("\nRESULTADO DE LA PREDICCIÓN:")
        print(f"  - Días estimados: {data.get('dias_estimados')} días")
        print(f"  - Fecha estimada: {data.get('fecha_estimada_germinacion')}")
        print(f"  - Confianza: {data.get('confianza')}%")
        print(f"  - Nivel confianza: {data.get('nivel_confianza')}")

        detalles = data.get('detalles', {})
        print(f"  - Especie agrupada: {detalles.get('especie_agrupada')}")
        print(f"  - Especie original: {detalles.get('especie_original')}")

        if detalles.get('especie_agrupada') == 'OTRAS':
            print("\n✅ TEST 3 PASADO: Especie nueva agrupada correctamente como 'OTRAS'")
        else:
            print("\n❌ TEST 3 FALLADO: Especie nueva NO agrupada como 'OTRAS'")
    else:
        print(f"\n❌ TEST 3 FALLADO: Status {response.status_code}")
        print(f"Error: {response.data}")

except Exception as e:
    print(f"\n❌ TEST 3 FALLADO: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# TEST 4: Validación de Campos Requeridos
# =============================================================================
print("\n" + "="*80)
print("  TEST 4: Validación de Campos Requeridos")
print("="*80)

datos_incompletos = {
    'fecha_siembra': '2024-12-04',
    # Falta: especie, clima, estado_capsula
}

print(f"\nDatos de entrada (incompletos):")
for key, value in datos_incompletos.items():
    print(f"  - {key}: {value}")

request = factory.post('/api/predicciones/germinacion/ml/', datos_incompletos, format='json')
force_authenticate(request, user=user)

try:
    response = prediccion_germinacion_ml(request)
    print(f"\nEstatus: {response.status_code}")

    if response.status_code == 400:
        print("\nERROR ESPERADO:")
        print(f"  - Error: {response.data.get('error')}")
        print(f"  - Detalles: {response.data.get('details')}")
        print("\n✅ TEST 4 PASADO: Validación de campos funciona correctamente")
    else:
        print(f"\n❌ TEST 4 FALLADO: Se esperaba status 400, recibido {response.status_code}")

except Exception as e:
    print(f"\n❌ TEST 4 FALLADO: {e}")
    import traceback
    traceback.print_exc()

# =============================================================================
# RESUMEN FINAL
# =============================================================================
print("\n" + "="*80)
print("  RESUMEN DE TESTS")
print("="*80)
print("\n✅ Todos los tests de la API completados")
print("\nEndpoints disponibles:")
print("  - POST /api/predicciones/germinacion/ml/")
print("  - GET  /api/ml/germinacion/model-info/")
print("\n" + "="*80)
