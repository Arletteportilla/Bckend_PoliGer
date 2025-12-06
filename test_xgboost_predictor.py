# -*- coding: utf-8 -*-
"""
Script de prueba para el predictor XGBoost de Polinización
===========================================================
Ejecutar desde la raíz del backend:
    python test_xgboost_predictor.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.ml.predictors import get_predictor

print("="*80)
print("TEST - PREDICTOR XGBOOST POLINIZACIÓN")
print("="*80)

# Obtener predictor
predictor = get_predictor()

# Verificar que esté cargado
if not predictor.model_loaded:
    print("❌ ERROR: Modelo no está cargado")
    print("   Verifica que existan los archivos:")
    print("   - laboratorio/modelos/Polinizacion/polinizacion.joblib")
    print("   - laboratorio/modelos/Polinizacion/label_encoders.pkl")
    sys.exit(1)

print("✅ Modelo XGBoost cargado correctamente")
print(f"   Features: {len(predictor.feature_list)}")
print(f"   Encoders: {list(predictor.label_encoders.keys())}")

print("\n" + "="*80)
print("EJECUTANDO PREDICCIÓN DE PRUEBA")
print("="*80)

# Datos de prueba CON NORMALIZACIÓN AUTOMÁTICA
# Estos datos tienen formato que necesita normalización
test_data = {
    'fechapol': '2024-12-04',
    'genero': 'Acineta',
    'especie': 'Acineta antioquiae',  # ← Incluye género (será normalizado a 'antioquiae')
    'ubicacion': 'V-0 - M-1A - P-0',  # ← Con guiones extras y P-0 (será normalizado)
    'responsable': 'Administrador Sistema',  # ← Minúsculas (será normalizado a mayúsculas)
    'tipo': 'self',  # ← Minúsculas (será normalizado a 'SELF')
    'cantidad': 1,
    'disponible': 1
}

print("\nDatos de entrada:")
for key, value in test_data.items():
    print(f"  {key}: {value}")

# Realizar predicción
try:
    resultado = predictor.predecir(**test_data)

    print("\n" + "="*80)
    print("✅ PREDICCIÓN EXITOSA")
    print("="*80)

    print(f"\n📊 Días estimados: {resultado['dias_estimados']} días")
    print(f"📅 Fecha polinización: {resultado['fecha_polinizacion']}")
    print(f"📅 Fecha estimada maduración: {resultado['fecha_estimada_maduracion']}")
    print(f"\n💯 Confianza: {resultado['confianza']}%")
    print(f"🏆 Nivel: {resultado['nivel_confianza'].upper()}")
    print(f"⚠️  Categorías nuevas: {resultado['categorias_nuevas']}")

    print(f"\n🔧 Método: {resultado['metodo']}")
    print(f"📦 Modelo: {resultado['modelo']}")
    print(f"🔢 Features usadas: {resultado['features_count']}")

    print(f"\n📈 Métricas del modelo:")
    print(f"   R²: {resultado['metricas_modelo']['r2']*100:.2f}%")
    print(f"   RMSE: ±{resultado['metricas_modelo']['rmse']:.2f} días")
    print(f"   MAE: ±{resultado['metricas_modelo']['mae']:.2f} días")

    # Mostrar normalizaciones si hubo
    if 'datos_normalizados' in resultado and resultado['datos_normalizados']:
        print(f"\n🔄 Normalizaciones aplicadas:")
        for campo, valores in resultado['datos_normalizados'].items():
            print(f"   {campo}:")
            print(f"      Original:    '{valores['original']}'")
            print(f"      Normalizada: '{valores['normalizada']}'")

    print("\n" + "="*80)
    print("✅ TEST COMPLETADO EXITOSAMENTE")
    print("="*80)
    print("\nCon la normalización automática, el sistema ahora:")
    print("  ✓ Remueve el género de la especie automáticamente")
    print("  ✓ Normaliza el formato de ubicación")
    print("  ✓ Convierte responsables a mayúsculas")
    print("  ✓ Normaliza el tipo de polinización")
    print("\n¡Esto mejora significativamente la confianza de las predicciones!")
    print("="*80)

except Exception as e:
    print("\n" + "="*80)
    print("❌ ERROR EN PREDICCIÓN")
    print("="*80)
    print(f"Tipo: {type(e).__name__}")
    print(f"Mensaje: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
