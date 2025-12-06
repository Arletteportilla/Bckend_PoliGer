# -*- coding: utf-8 -*-
"""
Script de prueba para GerminacionPredictor
===========================================
Verifica que el modelo Random Forest de germinación cargue correctamente
y realice predicciones
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

from laboratorio.ml.predictors import get_germinacion_predictor

print("="*80)
print("  TEST: PREDICTOR RANDOM FOREST DE GERMINACIÓN")
print("="*80)

# Obtener predictor (Singleton)
print("\n[1/3] Obteniendo instancia del predictor...")
predictor = get_germinacion_predictor()

if not predictor.model_loaded:
    print("❌ ERROR: El modelo no se cargó correctamente")
    sys.exit(1)

print("✅ Predictor cargado correctamente")
print(f"   - Features totales: {len(predictor.feature_order)}")
print(f"   - Top especies: {len(predictor.top_especies)}")
print(f"   - Numeric cols: {len(predictor.numeric_cols)}")

# Datos de prueba
print("\n[2/3] Preparando datos de prueba...")

test_data = {
    'fecha_siembra': '2024-12-04',
    'especie': 'Phragmipedium kovachii',
    'clima': 'IC',
    'estado_capsula': 'Cerrada',
    's_stock': 10,
    'c_solic': 2,
    'dispone': 1
}

print(f"   - Fecha siembra: {test_data['fecha_siembra']}")
print(f"   - Especie: {test_data['especie']}")
print(f"   - Clima: {test_data['clima']}")
print(f"   - Estado cápsula: {test_data['estado_capsula']}")

# Realizar predicción
print("\n[3/3] Realizando predicción...")
print("-"*80)

try:
    resultado = predictor.predecir(
        fecha_siembra=test_data['fecha_siembra'],
        especie=test_data['especie'],
        clima=test_data['clima'],
        estado_capsula=test_data['estado_capsula'],
        s_stock=test_data['s_stock'],
        c_solic=test_data['c_solic'],
        dispone=test_data['dispone']
    )

    print("\n" + "="*80)
    print("  RESULTADO DE LA PREDICCIÓN")
    print("="*80)
    print(f"\n📅 Fecha de siembra: {test_data['fecha_siembra']}")
    print(f"🌱 Especie: {test_data['especie']}")
    print(f"🌡️  Clima: {test_data['clima']}")
    print(f"\n⏱️  Días estimados de germinación: {resultado['dias_estimados']} días")
    print(f"📆 Fecha estimada de germinación: {resultado['fecha_estimada_germinacion']}")
    print(f"🎯 Confianza: {resultado['confianza']}% ({resultado['nivel_confianza'].upper()})")
    print(f"🤖 Modelo: {resultado['modelo']}")

    print(f"\n📊 Detalles:")
    for key, value in resultado['detalles'].items():
        print(f"   - {key}: {value}")

    print("\n" + "="*80)
    print("  ✅ TEST COMPLETADO EXITOSAMENTE")
    print("="*80)

except Exception as e:
    print(f"\n❌ ERROR en predicción: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 2: Verificar Singleton
print("\n" + "="*80)
print("  TEST SINGLETON")
print("="*80)

predictor2 = get_germinacion_predictor()
if predictor is predictor2:
    print("✅ Patrón Singleton funcionando correctamente (misma instancia)")
else:
    print("❌ ERROR: Se crearon múltiples instancias del predictor")

print("\n" + "="*80)
print("  TODOS LOS TESTS PASARON")
print("="*80)
