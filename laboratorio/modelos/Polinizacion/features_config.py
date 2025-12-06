# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

"""
CONFIGURACIÓN DE FEATURES - XGBOOST POLINIZACIÓN
=================================================
Este archivo define la lista exacta de features y su orden que debe usarse
para hacer predicciones con el modelo XGBoost entrenado.

IMPORTANTE: El orden de las features DEBE ser exactamente el mismo que durante
el entrenamiento, de lo contrario las predicciones serán incorrectas.
"""

import joblib
import json

# ============================================================================
# LISTA DE FEATURES EN ORDEN EXACTO DE ENTRENAMIENTO
# ============================================================================

FEATURE_LIST = [
    # TEMPORALES (5)
    'mes_pol',           # Mes de polinización (1-12)
    'dia_año_pol',       # Día del año (1-365)
    'trimestre_pol',     # Trimestre (1-4)
    'año_pol',           # Año
    'semana_año',        # Semana del año (1-52)

    # TEMPORALES CÍCLICAS (4)
    'mes_sin',           # sin(2π * mes / 12)
    'mes_cos',           # cos(2π * mes / 12)
    'dia_año_sin',       # sin(2π * día / 365)
    'dia_año_cos',       # cos(2π * día / 365)

    # CATEGÓRICAS CODIFICADAS (5)
    'genero_encoded',      # Género (0, 1, 2, ...)
    'especie_encoded',     # Especie (0, 1, 2, ...)
    'ubicacion_encoded',   # Ubicación (0, 1, 2, ...)
    'responsable_encoded', # Responsable (0, 1, 2, ...)
    'Tipo_encoded',        # Tipo (0, 1, 2, ...)

    # NUMÉRICAS (2)
    'cantidad',          # Cantidad polinizada
    'disponible'         # Cantidad disponible
]

# ============================================================================
# VARIABLES CATEGÓRICAS QUE NECESITAN LABEL ENCODING
# ============================================================================

CATEGORICAL_COLUMNS = ['genero', 'especie', 'ubicacion', 'responsable', 'Tipo']

# ============================================================================
# INFORMACIÓN ADICIONAL
# ============================================================================

FEATURE_INFO = {
    'total_features': 17,
    'temporales_basicas': 5,
    'temporales_ciclicas': 4,
    'categoricas_encoded': 5,
    'numericas': 2,

    'preprocessing': {
        'scaling': False,  # NO se usa escalado
        'target_encoding': False,  # NO se usa target encoding
        'frequency_encoding': False,  # NO se usa frequency encoding
        'label_encoding': True  # SÍ se usa label encoding
    },

    'input_columns_required': [
        'fechapol',      # Fecha de polinización (datetime)
        'genero',        # Género (string)
        'especie',       # Especie (string)
        'ubicacion',     # Ubicación (string)
        'responsable',   # Responsable (string)
        'Tipo',          # Tipo (string)
        'cantidad',      # Cantidad (int/float)
        'disponible'     # Disponible (int/float)
    ],

    'feature_creation_steps': [
        '1. Convertir fechapol a datetime',
        '2. Extraer mes_pol, dia_año_pol, trimestre_pol, año_pol, semana_año',
        '3. Crear features cíclicas: mes_sin/cos, dia_año_sin/cos',
        '4. Aplicar LabelEncoder a variables categóricas',
        '5. Agregar cantidad y disponible',
        '6. Seleccionar features en orden exacto de FEATURE_LIST'
    ]
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_feature_list():
    """
    Retorna la lista de features en el orden correcto.

    Returns:
        list: Lista de nombres de features en orden
    """
    return FEATURE_LIST.copy()

def get_categorical_columns():
    """
    Retorna la lista de variables categóricas que necesitan encoding.

    Returns:
        list: Lista de nombres de columnas categóricas
    """
    return CATEGORICAL_COLUMNS.copy()

def get_feature_info():
    """
    Retorna información completa sobre las features.

    Returns:
        dict: Diccionario con información de features
    """
    return FEATURE_INFO.copy()

def validate_features(df, feature_list=None):
    """
    Valida que un DataFrame tenga todas las features necesarias en el orden correcto.

    Args:
        df: DataFrame a validar
        feature_list: Lista de features esperadas (opcional, usa FEATURE_LIST por defecto)

    Returns:
        tuple: (bool, list) - (es_válido, features_faltantes)
    """
    if feature_list is None:
        feature_list = FEATURE_LIST

    missing_features = [f for f in feature_list if f not in df.columns]

    if missing_features:
        return False, missing_features

    return True, []

def save_feature_config(filepath='features_metadata.json'):
    """
    Guarda la configuración de features en formato JSON.

    Args:
        filepath: Ruta donde guardar el archivo JSON
    """
    config = {
        'feature_list': FEATURE_LIST,
        'categorical_columns': CATEGORICAL_COLUMNS,
        'feature_info': FEATURE_INFO
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print(f"✓ Configuración guardada en: {filepath}")

def load_feature_config(filepath='features_metadata.json'):
    """
    Carga la configuración de features desde JSON.

    Args:
        filepath: Ruta del archivo JSON

    Returns:
        dict: Configuración de features
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        config = json.load(f)

    return config

def print_feature_summary():
    """
    Imprime un resumen de las features configuradas.
    """
    print("="*80)
    print("RESUMEN DE FEATURES - XGBOOST POLINIZACIÓN")
    print("="*80)

    print(f"\nTotal de features: {len(FEATURE_LIST)}")

    print("\n[1] TEMPORALES BÁSICAS (5):")
    for i, feat in enumerate(FEATURE_LIST[:5], 1):
        print(f"  {i}. {feat}")

    print("\n[2] TEMPORALES CÍCLICAS (4):")
    for i, feat in enumerate(FEATURE_LIST[5:9], 1):
        print(f"  {i}. {feat}")

    print("\n[3] CATEGÓRICAS CODIFICADAS (5):")
    for i, feat in enumerate(FEATURE_LIST[9:14], 1):
        print(f"  {i}. {feat}")

    print("\n[4] NUMÉRICAS (2):")
    for i, feat in enumerate(FEATURE_LIST[14:16], 1):
        print(f"  {i}. {feat}")

    print("\n" + "="*80)
    print("PREPROCESSING:")
    print("="*80)
    for key, value in FEATURE_INFO['preprocessing'].items():
        status = "✅ SÍ" if value else "❌ NO"
        print(f"  {status} - {key}")

    print("\n" + "="*80)
    print("COLUMNAS DE ENTRADA REQUERIDAS:")
    print("="*80)
    for i, col in enumerate(FEATURE_INFO['input_columns_required'], 1):
        print(f"  {i}. {col}")

    print("\n" + "="*80)

# ============================================================================
# EJECUCIÓN DIRECTA
# ============================================================================

if __name__ == "__main__":
    # Mostrar resumen
    print_feature_summary()

    # Guardar configuración en JSON
    save_feature_config('Polinizacion/Xgboost/features_metadata.json')

    print("\n✅ Configuración de features lista para usar")
