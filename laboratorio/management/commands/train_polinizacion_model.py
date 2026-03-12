"""
Comando Django para entrenar el modelo de predicción de polinizaciones.

Genera exactamente los 3 archivos que carga XGBoostPolinizacionPredictor:
  - laboratorio/modelos/Polinizacion/polinizacion.joblib     → el modelo solo
  - laboratorio/modelos/Polinizacion/label_encoders.pkl      → dict de LabelEncoders
  - laboratorio/modelos/Polinizacion/features_metadata.json  → metadatos + feature_list

El feature engineering aplicado aquí es idéntico al del predictor en producción.
"""
import json
import os
import pickle
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import RandomForestRegressor


# Features en el orden exacto que usa el predictor
FEATURE_LIST = [
    'mes_pol', 'dia_año_pol', 'trimestre_pol', 'año_pol', 'semana_año',
    'mes_sin', 'mes_cos', 'dia_año_sin', 'dia_año_cos',
    'genero_encoded', 'especie_encoded', 'ubicacion_encoded',
    'responsable_encoded', 'Tipo_encoded', 'cantidad', 'disponible',
]


class Command(BaseCommand):
    help = 'Entrena el modelo XGBoost de predicción de días hasta maduración de polinizaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='prediccion/polinizacion/datos_limpios.csv',
            help='Ruta al archivo CSV con datos de polinizaciones',
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default='laboratorio/modelos/Polinizacion',
            help='Directorio donde guardar los 3 archivos del modelo',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        output_dir = options['output_path']

        self.stdout.write('=' * 80)
        self.stdout.write('   ENTRENAMIENTO MODELO POLINIZACION')
        self.stdout.write('=' * 80)
        self.stdout.write('')

        if not XGBOOST_AVAILABLE:
            self.stdout.write(self.style.WARNING(
                'XGBoost no disponible, usando Random Forest como alternativa'
            ))

        # ------------------------------------------------------------------
        # 1. Cargar datos
        # ------------------------------------------------------------------
        self.stdout.write(f'Cargando datos desde {csv_path}...')
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error cargando CSV: {e}'))
            return

        self.stdout.write(self.style.SUCCESS(f'  {len(df):,} registros cargados'))

        # ------------------------------------------------------------------
        # 2. Parsear fechas y calcular target
        # ------------------------------------------------------------------
        df['fechapol'] = pd.to_datetime(df['fechapol'], errors='coerce')
        df['fechamad'] = pd.to_datetime(df['fechamad'], errors='coerce')

        # Filtrar filas con fechas válidas
        df = df.dropna(subset=['fechapol', 'fechamad'])

        # Target: días de maduración
        df['dias_maduracion'] = (df['fechamad'] - df['fechapol']).dt.days

        # Filtrar outliers
        df = df[(df['dias_maduracion'] > 0) & (df['dias_maduracion'] < 600)]

        if len(df) < 50:
            self.stdout.write(self.style.ERROR(
                f'Datos insuficientes tras limpieza: {len(df)} registros (mínimo 50)'
            ))
            return

        self.stdout.write(self.style.SUCCESS(f'  {len(df):,} registros válidos tras filtrar outliers'))

        # ------------------------------------------------------------------
        # 3. Feature engineering temporal (igual que el predictor)
        # ------------------------------------------------------------------
        self.stdout.write('\nCreando features...')

        df['mes_pol'] = df['fechapol'].dt.month
        df['dia_año_pol'] = df['fechapol'].dt.dayofyear
        df['trimestre_pol'] = df['fechapol'].dt.quarter
        df['año_pol'] = df['fechapol'].dt.year
        df['semana_año'] = df['fechapol'].dt.isocalendar().week.astype(int)

        # Features cíclicas
        df['mes_sin'] = np.sin(2 * np.pi * df['mes_pol'] / 12)
        df['mes_cos'] = np.cos(2 * np.pi * df['mes_pol'] / 12)
        df['dia_año_sin'] = np.sin(2 * np.pi * df['dia_año_pol'] / 365)
        df['dia_año_cos'] = np.cos(2 * np.pi * df['dia_año_pol'] / 365)

        # ------------------------------------------------------------------
        # 4. Label Encoding — mismas claves que el predictor espera
        # ------------------------------------------------------------------
        le_genero = LabelEncoder()
        le_especie = LabelEncoder()
        le_ubicacion = LabelEncoder()
        le_responsable = LabelEncoder()
        le_tipo = LabelEncoder()

        df['genero_encoded'] = le_genero.fit_transform(df['genero'].astype(str))
        df['especie_encoded'] = le_especie.fit_transform(df['especie'].astype(str))
        df['ubicacion_encoded'] = le_ubicacion.fit_transform(df['ubicacion'].astype(str))
        df['responsable_encoded'] = le_responsable.fit_transform(df['responsable'].astype(str))
        df['Tipo_encoded'] = le_tipo.fit_transform(df['Tipo'].astype(str))

        # Columnas numéricas tal como el predictor las interpreta
        df['cantidad'] = df['cantidad'].astype(int)
        df['disponible'] = df['disponible'].astype(int)

        self.stdout.write(self.style.SUCCESS('  Features creadas'))

        # ------------------------------------------------------------------
        # 5. Preparar X / y y split
        # ------------------------------------------------------------------
        X = df[FEATURE_LIST].copy()
        y = df['dias_maduracion'].copy()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.15, random_state=42
        )

        self.stdout.write(f'\n  Features: {len(FEATURE_LIST)}')
        self.stdout.write(f'  Train: {len(X_train):,}   Test: {len(X_test):,}')

        # ------------------------------------------------------------------
        # 6. Entrenar modelo
        # ------------------------------------------------------------------
        self.stdout.write('\nEntrenando modelo...')

        if XGBOOST_AVAILABLE:
            modelo = XGBRegressor(
                n_estimators=300,
                learning_rate=0.1,
                max_depth=5,
                subsample=0.9,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1,
            )
            model_name = 'XGBoost'
        else:
            modelo = RandomForestRegressor(
                n_estimators=300,
                max_depth=None,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1,
            )
            model_name = 'Random Forest'

        modelo.fit(X_train, y_train)
        self.stdout.write(self.style.SUCCESS(f'  Modelo {model_name} entrenado'))

        # ------------------------------------------------------------------
        # 7. Evaluar
        # ------------------------------------------------------------------
        self.stdout.write('\nEvaluando modelo...')
        y_pred = modelo.predict(X_test)

        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        self.stdout.write(f'  MAE:  {mae:.2f} dias')
        self.stdout.write(f'  RMSE: {rmse:.2f} dias')
        self.stdout.write(f'  R2:   {r2:.4f} ({r2 * 100:.2f}%)')

        # ------------------------------------------------------------------
        # 8. Guardar los 3 archivos que necesita el predictor
        # ------------------------------------------------------------------
        self.stdout.write(f'\nGuardando archivos en {output_dir}...')
        os.makedirs(output_dir, exist_ok=True)

        # 8a. Modelo solo (XGBRegressor o RandomForestRegressor object)
        model_path = os.path.join(output_dir, 'polinizacion.joblib')
        joblib.dump(modelo, model_path, compress=3)
        self.stdout.write(f'  Guardado: {model_path}')

        # 8b. LabelEncoders — claves exactas que usa el predictor
        encoders = {
            'genero': le_genero,
            'especie': le_especie,
            'ubicacion': le_ubicacion,
            'responsable': le_responsable,
            'Tipo': le_tipo,
        }
        encoders_path = os.path.join(output_dir, 'label_encoders.pkl')
        with open(encoders_path, 'wb') as f:
            pickle.dump(encoders, f)
        self.stdout.write(f'  Guardado: {encoders_path}')

        # 8c. Metadatos con feature_list
        metadata = {
            'feature_list': FEATURE_LIST,
            'n_features': len(FEATURE_LIST),
            'model_name': model_name,
            'mae': mae,
            'r2': r2,
            'rmse': rmse,
            'n_samples': len(df),
            'fecha_entrenamiento': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        metadata_path = os.path.join(output_dir, 'features_metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        self.stdout.write(f'  Guardado: {metadata_path}')

        # ------------------------------------------------------------------
        # 9. Resumen
        # ------------------------------------------------------------------
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('   ENTRENAMIENTO COMPLETADO'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'\n  Modelo:     {model_name}')
        self.stdout.write(f'  Registros:  {len(df):,}')
        self.stdout.write(f'  Features:   {len(FEATURE_LIST)}')
        self.stdout.write(f'  MAE:        {mae:.2f} dias')
        self.stdout.write(f'  RMSE:       {rmse:.2f} dias')
        self.stdout.write(f'  R2:         {r2:.4f} ({r2 * 100:.2f}%)')
        self.stdout.write(f'\n  Archivos guardados en: {output_dir}')
        self.stdout.write('')
