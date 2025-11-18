# -*- coding: utf-8 -*-
"""
MODELO MEJORADO DE PREDICCIÓN DE GERMINACIÓN (Compatible)
=========================================================
Objetivo: Alcanzar >85-90% de precisión con librerías estándar

Técnicas:
- Feature Engineering Avanzado
- Ensemble de Random Forest + Gradient Boosting + XGBoost
- Optimización de hiperparámetros
- Sin dependencias problemáticas (LightGBM/CatBoost)

Autor: Claude Code
Fecha: 2025-11-10
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
import joblib
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, cross_val_score, KFold, GridSearchCV
from sklearn.preprocessing import LabelEncoder, RobustScaler
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
    VotingRegressor
)
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# XGBoost (si está disponible)
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
    print("[OK] XGBoost disponible")
except:
    XGBOOST_AVAILABLE = False
    print("[INFO] XGBoost no disponible, usando solo RF y GB")

print("="*80)
print(" MODELO MEJORADO - PREDICCIÓN DE GERMINACIÓN")
print("="*80)
print()

# ============================================================================
# 1. CARGA DE DATOS
# ============================================================================
print("[PASO 1] Cargando datos...")

df = pd.read_csv('GERMINACION_FILLED_GENUS.csv', sep=';', encoding='latin-1')
df_clean = df.copy()
df_clean.columns = df_clean.columns.str.lower()

# Filtrar válidos
df_clean = df_clean[df_clean['f.germi'].notna() & (df_clean['f.germi'] != '')]
df_clean = df_clean[df_clean['f.siembra'].notna() & (df_clean['f.siembra'] != '')]

# Convertir fechas
def parse_date(date_str):
    try:
        return pd.to_datetime(date_str, format='%d/%m/%Y')
    except:
        try:
            return pd.to_datetime(date_str)
        except:
            return pd.NaT

df_clean['f.siembra'] = df_clean['f.siembra'].apply(parse_date)
df_clean['f.germi'] = df_clean['f.germi'].apply(parse_date)
df_clean = df_clean.dropna(subset=['f.siembra', 'f.germi'])

# Días de germinación
df_clean['dias_germinacion'] = (df_clean['f.germi'] - df_clean['f.siembra']).dt.days
df_clean = df_clean[(df_clean['dias_germinacion'] > 0) & (df_clean['dias_germinacion'] <= 365)]

print(f"[OK] Registros válidos: {len(df_clean)}")

# Rellenar faltantes
if df_clean['c.solic'].dtype == 'object':
    df_clean['c.solic'] = pd.to_numeric(df_clean['c.solic'], errors='coerce')
df_clean['c.solic'].fillna(df_clean['c.solic'].median(), inplace=True)
df_clean['clima'].fillna('Intermedio', inplace=True)
df_clean['especie'].fillna('Desconocido', inplace=True)

# ============================================================================
# 2. FEATURE ENGINEERING AVANZADO
# ============================================================================
print("\n[PASO 2] Feature Engineering Avanzado...")

# Temporales básicas
df_clean['mes_siembra'] = df_clean['f.siembra'].dt.month
df_clean['dia_mes_siembra'] = df_clean['f.siembra'].dt.day
df_clean['dia_anio_siembra'] = df_clean['f.siembra'].dt.dayofyear
df_clean['anio_siembra'] = df_clean['f.siembra'].dt.year
df_clean['trimestre_siembra'] = df_clean['f.siembra'].dt.quarter
df_clean['semana_siembra'] = df_clean['f.siembra'].dt.isocalendar().week
df_clean['dia_semana'] = df_clean['f.siembra'].dt.dayofweek

# Cíclicas
df_clean['mes_sin'] = np.sin(2 * np.pi * df_clean['mes_siembra'] / 12)
df_clean['mes_cos'] = np.cos(2 * np.pi * df_clean['mes_siembra'] / 12)
df_clean['dia_anio_sin'] = np.sin(2 * np.pi * df_clean['dia_anio_siembra'] / 365)
df_clean['dia_anio_cos'] = np.cos(2 * np.pi * df_clean['dia_anio_siembra'] / 365)
df_clean['semana_sin'] = np.sin(2 * np.pi * df_clean['semana_siembra'] / 52)
df_clean['semana_cos'] = np.cos(2 * np.pi * df_clean['semana_siembra'] / 52)

# Estadísticas por especie
species_stats = df_clean.groupby('especie')['dias_germinacion'].agg([
    ('especie_media', 'mean'),
    ('especie_mediana', 'median'),
    ('especie_std', 'std'),
    ('especie_min', 'min'),
    ('especie_max', 'max'),
    ('especie_count', 'count'),
    ('especie_q25', lambda x: x.quantile(0.25)),
    ('especie_q75', lambda x: x.quantile(0.75))
]).reset_index()

df_clean = df_clean.merge(species_stats, on='especie', how='left')
df_clean['especie_std'].fillna(0, inplace=True)
df_clean['especie_iqr'] = df_clean['especie_q75'] - df_clean['especie_q25']

# Estadísticas por clima
climate_stats = df_clean.groupby('clima')['dias_germinacion'].agg([
    ('clima_media', 'mean'),
    ('clima_mediana', 'median'),
    ('clima_std', 'std')
]).reset_index()

df_clean = df_clean.merge(climate_stats, on='clima', how='left')
df_clean['clima_std'].fillna(0, inplace=True)

# Estadísticas por mes
month_stats = df_clean.groupby('mes_siembra')['dias_germinacion'].agg([
    ('mes_media', 'mean'),
    ('mes_std', 'std')
]).reset_index()

df_clean = df_clean.merge(month_stats, on='mes_siembra', how='left')
df_clean['mes_std'].fillna(0, inplace=True)

# Género
df_clean['genero'] = df_clean['especie'].str.split().str[0]

genus_stats = df_clean.groupby('genero')['dias_germinacion'].agg([
    ('genero_media', 'mean'),
    ('genero_std', 'std'),
    ('genero_count', 'count')
]).reset_index()

df_clean = df_clean.merge(genus_stats, on='genero', how='left')
df_clean['genero_std'].fillna(0, inplace=True)

# Interacciones
df_clean['especie_clima'] = df_clean['especie'].astype(str) + '_' + df_clean['clima'].astype(str)
df_clean['especie_frecuencia'] = df_clean['especie'].map(df_clean['especie'].value_counts())
df_clean['clima_frecuencia'] = df_clean['clima'].map(df_clean['clima'].value_counts())

# Codificar categóricas
le_especie = LabelEncoder()
le_clima = LabelEncoder()
le_genero = LabelEncoder()
le_especie_clima = LabelEncoder()

df_clean['especie_encoded'] = le_especie.fit_transform(df_clean['especie'].astype(str))
df_clean['clima_encoded'] = le_clima.fit_transform(df_clean['clima'].astype(str))
df_clean['genero_encoded'] = le_genero.fit_transform(df_clean['genero'].astype(str))
df_clean['especie_clima_encoded'] = le_especie_clima.fit_transform(df_clean['especie_clima'].astype(str))

if 's.stock' in df_clean.columns:
    if df_clean['s.stock'].dtype == 'object':
        df_clean['s.stock'] = pd.to_numeric(df_clean['s.stock'], errors='coerce')
    df_clean['s.stock'].fillna(0, inplace=True)

print(f"[OK] Features creadas: {len(df_clean.columns)} columnas totales")

# ============================================================================
# 3. PREPARACIÓN DE FEATURES
# ============================================================================
print("\n[PASO 3] Preparación de features...")

feature_columns = [
    'especie_encoded', 'clima_encoded', 'genero_encoded', 'especie_clima_encoded',
    'c.solic',
    'mes_siembra', 'dia_mes_siembra', 'dia_anio_siembra', 'anio_siembra',
    'trimestre_siembra', 'semana_siembra', 'dia_semana',
    'mes_sin', 'mes_cos', 'dia_anio_sin', 'dia_anio_cos', 'semana_sin', 'semana_cos',
    'especie_media', 'especie_mediana', 'especie_std', 'especie_min', 'especie_max',
    'especie_count', 'especie_q25', 'especie_q75', 'especie_iqr',
    'clima_media', 'clima_mediana', 'clima_std',
    'mes_media', 'mes_std',
    'genero_media', 'genero_std', 'genero_count',
    'especie_frecuencia', 'clima_frecuencia'
]

if 's.stock' in df_clean.columns:
    feature_columns.append('s.stock')

X = df_clean[feature_columns].copy()
y = df_clean['dias_germinacion'].copy()

print(f"[OK] Features: {len(feature_columns)}")

# División estratificada
y_bins = pd.qcut(y, q=5, labels=False, duplicates='drop')
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.15, random_state=42, stratify=y_bins
)

print(f"[OK] Train: {len(X_train)}, Test: {len(X_test)}")

# ============================================================================
# 4. OPTIMIZACIÓN DE RANDOM FOREST
# ============================================================================
print("\n[PASO 4] Optimización de Random Forest con GridSearchCV...")

param_grid_rf = {
    'n_estimators': [200, 300, 400],
    'max_depth': [15, 20, 25],
    'min_samples_split': [2, 3, 5],
    'min_samples_leaf': [1, 2],
    'max_features': ['sqrt', 'log2']
}

rf_base = RandomForestRegressor(random_state=42, n_jobs=-1)

grid_rf = GridSearchCV(
    rf_base, param_grid_rf, cv=5,
    scoring='neg_mean_absolute_error',
    n_jobs=-1, verbose=1
)

print("[INFO] Entrenando Random Forest...")
grid_rf.fit(X_train, y_train)
best_rf = grid_rf.best_estimator_

print(f"[OK] Mejores parámetros: {grid_rf.best_params_}")

# Evaluar
y_pred_rf = best_rf.predict(X_test)
rf_mae = mean_absolute_error(y_test, y_pred_rf)
rf_rmse = np.sqrt(mean_squared_error(y_test, y_pred_rf))
rf_r2 = r2_score(y_test, y_pred_rf)

print(f"[RANDOM FOREST]")
print(f"  MAE: {rf_mae:.2f}, RMSE: {rf_rmse:.2f}, R²: {rf_r2:.4f} ({rf_r2*100:.2f}%)")

# ============================================================================
# 5. OPTIMIZACIÓN DE GRADIENT BOOSTING
# ============================================================================
print("\n[PASO 5] Optimización de Gradient Boosting...")

param_grid_gb = {
    'n_estimators': [200, 300],
    'learning_rate': [0.05, 0.1],
    'max_depth': [5, 7],
    'min_samples_split': [2, 3],
    'subsample': [0.8, 0.9]
}

gb_base = GradientBoostingRegressor(random_state=42)

grid_gb = GridSearchCV(
    gb_base, param_grid_gb, cv=5,
    scoring='neg_mean_absolute_error',
    n_jobs=-1, verbose=1
)

print("[INFO] Entrenando Gradient Boosting...")
grid_gb.fit(X_train, y_train)
best_gb = grid_gb.best_estimator_

print(f"[OK] Mejores parámetros: {grid_gb.best_params_}")

y_pred_gb = best_gb.predict(X_test)
gb_mae = mean_absolute_error(y_test, y_pred_gb)
gb_rmse = np.sqrt(mean_squared_error(y_test, y_pred_gb))
gb_r2 = r2_score(y_test, y_pred_gb)

print(f"[GRADIENT BOOSTING]")
print(f"  MAE: {gb_mae:.2f}, RMSE: {gb_rmse:.2f}, R²: {gb_r2:.4f} ({gb_r2*100:.2f}%)")

# ============================================================================
# 6. XGBoost (si está disponible)
# ============================================================================
if XGBOOST_AVAILABLE:
    print("\n[PASO 6] Optimización de XGBoost...")

    param_grid_xgb = {
        'n_estimators': [200, 300],
        'learning_rate': [0.05, 0.1],
        'max_depth': [5, 7],
        'min_child_weight': [1, 3],
        'subsample': [0.8],
        'colsample_bytree': [0.8]
    }

    xgb_base = xgb.XGBRegressor(random_state=42, n_jobs=-1)

    grid_xgb = GridSearchCV(
        xgb_base, param_grid_xgb, cv=5,
        scoring='neg_mean_absolute_error',
        n_jobs=-1, verbose=1
    )

    print("[INFO] Entrenando XGBoost...")
    grid_xgb.fit(X_train, y_train)
    best_xgb = grid_xgb.best_estimator_

    print(f"[OK] Mejores parámetros: {grid_xgb.best_params_}")

    y_pred_xgb = best_xgb.predict(X_test)
    xgb_mae = mean_absolute_error(y_test, y_pred_xgb)
    xgb_rmse = np.sqrt(mean_squared_error(y_test, y_pred_xgb))
    xgb_r2 = r2_score(y_test, y_pred_xgb)

    print(f"[XGBOOST]")
    print(f"  MAE: {xgb_mae:.2f}, RMSE: {xgb_rmse:.2f}, R²: {xgb_r2:.4f} ({xgb_r2*100:.2f}%)")

# ============================================================================
# 7. VOTING ENSEMBLE
# ============================================================================
print("\n[PASO 7] Creando Voting Ensemble...")

estimators = [
    ('rf', best_rf),
    ('gb', best_gb)
]

if XGBOOST_AVAILABLE:
    estimators.append(('xgb', best_xgb))

voting = VotingRegressor(estimators=estimators, n_jobs=-1)

print(f"[INFO] Entrenando Voting Ensemble con {len(estimators)} modelos...")
voting.fit(X_train, y_train)

y_pred_voting = voting.predict(X_test)
voting_mae = mean_absolute_error(y_test, y_pred_voting)
voting_rmse = np.sqrt(mean_squared_error(y_test, y_pred_voting))
voting_r2 = r2_score(y_test, y_pred_voting)

print(f"[VOTING ENSEMBLE]")
print(f"  MAE: {voting_mae:.2f}, RMSE: {voting_rmse:.2f}, R²: {voting_r2:.4f} ({voting_r2*100:.2f}%)")

# ============================================================================
# 8. SELECCIÓN DEL MEJOR
# ============================================================================
print("\n" + "="*80)
print("[COMPARACIÓN FINAL]")
print("="*80)

results = {
    'Random Forest': {'mae': rf_mae, 'rmse': rf_rmse, 'r2': rf_r2, 'model': best_rf},
    'Gradient Boosting': {'mae': gb_mae, 'rmse': gb_rmse, 'r2': gb_r2, 'model': best_gb},
    'Voting Ensemble': {'mae': voting_mae, 'rmse': voting_rmse, 'r2': voting_r2, 'model': voting}
}

if XGBOOST_AVAILABLE:
    results['XGBoost'] = {'mae': xgb_mae, 'rmse': xgb_rmse, 'r2': xgb_r2, 'model': best_xgb}

df_results = pd.DataFrame({
    'Modelo': list(results.keys()),
    'MAE': [results[k]['mae'] for k in results.keys()],
    'RMSE': [results[k]['rmse'] for k in results.keys()],
    'R²': [results[k]['r2'] for k in results.keys()],
    'R²_%': [results[k]['r2']*100 for k in results.keys()]
}).sort_values('R²', ascending=False)

print(df_results.to_string(index=False))

best_name = df_results.iloc[0]['Modelo']
best_result = results[best_name]

print(f"\n{'='*80}")
print(f"[MEJOR MODELO]: {best_name}")
print(f"{'='*80}")
print(f"  MAE: {best_result['mae']:.2f} dias")
print(f"  RMSE: {best_result['rmse']:.2f} dias")
print(f"  R2: {best_result['r2']:.4f} ({best_result['r2']*100:.2f}%)")

if best_result['r2'] >= 0.90:
    print(f"\n[OK] OBJETIVO ALCANZADO! R2 >= 90%")
elif best_result['r2'] >= 0.85:
    print(f"\n[OK] Excelente precision! R2 >= 85%")
    print(f"   Faltan {(0.90 - best_result['r2'])*100:.2f}% para llegar a 90%")
else:
    print(f"\n[INFO] Buena precision. Mejora vs original: +{(best_result['r2'] - 0.6237)*100:.2f}%")

# ============================================================================
# 9. GUARDAR MODELO
# ============================================================================
print("\n[PASO 8] Guardando modelo...")

model_package = {
    'model': best_result['model'],
    'label_encoders': {
        'especie': le_especie,
        'clima': le_clima,
        'genero': le_genero,
        'especie_clima': le_especie_clima
    },
    'feature_columns': feature_columns,
    'species_stats': species_stats,
    'climate_stats': climate_stats,
    'month_stats': month_stats,
    'genus_stats': genus_stats,
    'metadata': {
        'model_name': best_name,
        'test_mae': float(best_result['mae']),
        'test_rmse': float(best_result['rmse']),
        'test_r2': float(best_result['r2']),
        'n_features': len(feature_columns)
    }
}

joblib.dump(model_package, 'germination_model_improved.pkl', compress=3)
print("[OK] Modelo guardado en 'germination_model_improved.pkl'")

df_results.to_csv('improved_model_comparison.csv', index=False)
print("[OK] Comparación guardada en 'improved_model_comparison.csv'")

# ============================================================================
# 10. VISUALIZACIÓN
# ============================================================================
print("\n[PASO 9] Generando visualizaciones...")

fig = plt.figure(figsize=(16, 10))

# 1. Comparación R²
ax1 = plt.subplot(2, 3, 1)
colors = ['green' if r >= 90 else 'orange' if r >= 85 else 'lightblue'
          for r in df_results['R²_%']]
ax1.barh(df_results['Modelo'], df_results['R²_%'], color=colors)
ax1.axvline(x=90, color='red', linestyle='--', linewidth=2, label='Objetivo 90%')
ax1.set_xlabel('R² (%)')
ax1.set_title('Comparación de Modelos - R²')
ax1.legend()
ax1.grid(axis='x', alpha=0.3)

# 2. Predicciones vs Reales
ax2 = plt.subplot(2, 3, 2)
ax2.scatter(y_test, y_pred_voting, alpha=0.5, s=20)
ax2.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--', lw=2)
ax2.set_xlabel('Días Reales')
ax2.set_ylabel('Días Predichos')
ax2.set_title(f'{best_name} - R²={best_result["r2"]:.3f}')
ax2.grid(alpha=0.3)

# 3. Distribución de errores
ax3 = plt.subplot(2, 3, 3)
errors = y_test.values - y_pred_voting
ax3.hist(errors, bins=50, color='skyblue', edgecolor='black')
ax3.axvline(x=0, color='red', linestyle='--', linewidth=2)
ax3.set_xlabel('Error (días)')
ax3.set_ylabel('Frecuencia')
ax3.set_title(f'Errores - MAE={voting_mae:.2f}')
ax3.grid(alpha=0.3)

# 4. Comparación MAE
ax4 = plt.subplot(2, 3, 4)
ax4.barh(df_results['Modelo'], df_results['MAE'], color='lightcoral')
ax4.set_xlabel('MAE (días)')
ax4.set_title('Comparación - Error Absoluto Medio')
ax4.grid(axis='x', alpha=0.3)

# 5. Feature Importance (del mejor Random Forest)
ax5 = plt.subplot(2, 3, 5)
if hasattr(best_rf, 'feature_importances_'):
    importances = pd.DataFrame({
        'feature': feature_columns,
        'importance': best_rf.feature_importances_
    }).sort_values('importance', ascending=False).head(15)

    ax5.barh(range(len(importances)), importances['importance'], color='plum')
    ax5.set_yticks(range(len(importances)))
    ax5.set_yticklabels(importances['feature'], fontsize=8)
    ax5.set_xlabel('Importancia')
    ax5.set_title('Top 15 Features Más Importantes')
    ax5.grid(axis='x', alpha=0.3)

# 6. Mejora vs Original
ax6 = plt.subplot(2, 3, 6)
models_comp = ['Original\n(62.37%)', f'Mejorado\n({best_result["r2"]*100:.2f}%)']
r2_comp = [62.37, best_result['r2']*100]
colors_comp = ['lightblue', 'green' if best_result['r2'] >= 0.9 else 'orange']
ax6.bar(models_comp, r2_comp, color=colors_comp, edgecolor='black')
ax6.axhline(y=90, color='red', linestyle='--', linewidth=2, label='Objetivo 90%')
ax6.set_ylabel('R² (%)')
ax6.set_title('Comparación: Original vs Mejorado')
ax6.legend()
ax6.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('improved_model_visualization.png', dpi=300, bbox_inches='tight')
print("[OK] Visualización guardada en 'improved_model_visualization.png'")
plt.close()

print("\n" + "="*80)
print("[COMPLETADO]")
print("="*80)
