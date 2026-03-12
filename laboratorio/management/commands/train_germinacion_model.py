"""
Comando Django para entrenar el modelo de predicción de germinaciones.

Genera exactamente los 3 archivos que carga GerminacionPredictor:
  - laboratorio/modelos/Germinacion/random_forest_germinacion.joblib
  - laboratorio/modelos/Germinacion/germinacion_transformador.pkl
  - laboratorio/modelos/Germinacion/feature_order_germinacion.json

El feature engineering aplicado aquí es idéntico al de _create_features()
y _apply_ohe_encoding() del predictor en producción.
"""
import json
import os
import pickle

import joblib
import numpy as np
import pandas as pd
from django.core.management.base import BaseCommand
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import RobustScaler


class Command(BaseCommand):
    help = 'Entrena el modelo Random Forest de predicción de días hasta germinación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='data/Germinacion_Consolidado - Consolidado.csv',
            help='Ruta al archivo CSV con datos de germinaciones',
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default='laboratorio/modelos/Germinacion',
            help='Directorio donde guardar los 3 archivos del modelo',
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        output_dir = options['output_path']

        self.stdout.write('=' * 80)
        self.stdout.write('   ENTRENAMIENTO MODELO GERMINACION')
        self.stdout.write('=' * 80)
        self.stdout.write('')

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
        # 2. Filtrar y validar target
        # ------------------------------------------------------------------
        df = df.dropna(subset=['DIAS_GERMINACION'])
        df = df[(df['DIAS_GERMINACION'] > 0) & (df['DIAS_GERMINACION'] < 800)]

        if len(df) < 50:
            self.stdout.write(self.style.ERROR(
                f'Datos insuficientes tras limpieza: {len(df)} registros (mínimo 50)'
            ))
            return

        self.stdout.write(self.style.SUCCESS(f'  {len(df):,} registros válidos tras filtrar outliers'))

        # ------------------------------------------------------------------
        # 3. Parsear fecha de siembra
        # ------------------------------------------------------------------
        df['F.SIEMBRA'] = pd.to_datetime(df['F.SIEMBRA'], errors='coerce')
        df = df.dropna(subset=['F.SIEMBRA'])

        # ------------------------------------------------------------------
        # 4. Calcular top_especies (top 100 más frecuentes)
        # ------------------------------------------------------------------
        top_especies = (
            df['ESPECIE']
            .value_counts()
            .head(100)
            .index
            .tolist()
        )
        self.stdout.write(f'\n  Top especies: {len(top_especies)}')

        # ------------------------------------------------------------------
        # 5. Feature engineering — idéntico a GerminacionPredictor._create_features()
        # ------------------------------------------------------------------
        self.stdout.write('\nCreando features...')

        # 5a. Features temporales
        df['MES_SIEMBRA'] = df['F.SIEMBRA'].dt.month
        df['DIA_AÑO_SIEMBRA'] = df['F.SIEMBRA'].dt.dayofyear
        df['TRIMESTRE_SIEMBRA'] = df['F.SIEMBRA'].dt.quarter
        df['SEMANA_AÑO'] = df['F.SIEMBRA'].dt.isocalendar().week.astype(int)

        # 5b. Features cíclicas
        df['MES_SIN'] = np.sin(2 * np.pi * df['MES_SIEMBRA'] / 12)
        df['MES_COS'] = np.cos(2 * np.pi * df['MES_SIEMBRA'] / 12)
        df['DIA_AÑO_SIN'] = np.sin(2 * np.pi * df['DIA_AÑO_SIEMBRA'] / 365)
        df['DIA_AÑO_COS'] = np.cos(2 * np.pi * df['DIA_AÑO_SIEMBRA'] / 365)

        # 5c. Features derivadas numéricas
        df['C.SOLIC_LOG'] = np.log1p(df['C.SOLIC'])
        df['S.STOCK_LOG'] = np.log1p(df['S.STOCK'])
        df['RATIO_STOCK_SOLIC'] = np.where(
            df['C.SOLIC'] > 0,
            df['S.STOCK'] / (df['C.SOLIC'] + 1),
            0,
        )

        # 5d. Estadísticas hardcodeadas — igual que en el predictor
        df['ESP_MEAN'] = 90
        df['ESP_MEDIAN'] = 85
        df['ESP_STD'] = 50
        df['ESP_COUNT'] = 1
        df['CLIMA_MEAN'] = 90
        df['CLIMA_STD'] = 50

        # 5e. Agrupación de especie
        df['ESPECIE_AGRUPADA'] = df['ESPECIE'].apply(
            lambda x: x if x in top_especies else 'OTRAS'
        )

        # ------------------------------------------------------------------
        # 6. Definir listas de features — igual que el predictor
        # ------------------------------------------------------------------
        categorical_features = ['ESPECIE_AGRUPADA', 'CLIMA', 'E.CAPSU']

        numerical_features = [
            'MES_SIEMBRA', 'DIA_AÑO_SIEMBRA', 'TRIMESTRE_SIEMBRA', 'SEMANA_AÑO',
            'MES_SIN', 'MES_COS', 'DIA_AÑO_SIN', 'DIA_AÑO_COS',
            'C.SOLIC_LOG', 'S.STOCK_LOG', 'RATIO_STOCK_SOLIC',
            'ESP_MEAN', 'ESP_MEDIAN', 'ESP_STD', 'ESP_COUNT',
            'CLIMA_MEAN', 'CLIMA_STD',
            'S.STOCK', 'C.SOLIC', 'DISPONE',
        ]

        self.stdout.write(self.style.SUCCESS('  Features creadas'))

        # ------------------------------------------------------------------
        # 7. One-Hot Encoding — idéntico a _apply_ohe_encoding()
        # ------------------------------------------------------------------
        df_for_ohe = df[categorical_features + numerical_features].copy()

        df_encoded = pd.get_dummies(
            df_for_ohe,
            columns=categorical_features,
            drop_first=True,
            dtype=int,
        )

        # numeric_cols = columnas numéricas tras OHE (las que NO son OHE dummies)
        ohe_columns = [c for c in df_encoded.columns if c not in numerical_features]
        numeric_cols = [c for c in df_encoded.columns if c not in ohe_columns]

        # feature_order = todas las columnas del DataFrame tras OHE
        feature_order = list(df_encoded.columns)

        self.stdout.write(f'\n  Features totales tras OHE:  {len(feature_order)}')
        self.stdout.write(f'  Columnas numericas (scaler): {len(numeric_cols)}')
        self.stdout.write(f'  Columnas OHE:                {len(ohe_columns)}')

        # ------------------------------------------------------------------
        # 8. Ajustar RobustScaler sobre numeric_cols
        # ------------------------------------------------------------------
        scaler = RobustScaler()
        df_encoded[numeric_cols] = scaler.fit_transform(df_encoded[numeric_cols])

        # ------------------------------------------------------------------
        # 9. Preparar X / y y split
        # ------------------------------------------------------------------
        X = df_encoded[feature_order].copy()
        y = df['DIAS_GERMINACION'].copy()

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        self.stdout.write(f'\n  Train: {len(X_train):,}   Test: {len(X_test):,}')

        # ------------------------------------------------------------------
        # 10. Entrenar RandomForestRegressor
        # ------------------------------------------------------------------
        self.stdout.write('\nEntrenando modelo Random Forest...')

        modelo = RandomForestRegressor(
            n_estimators=300,
            max_depth=None,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        modelo.fit(X_train, y_train)
        self.stdout.write(self.style.SUCCESS('  Modelo entrenado'))

        # ------------------------------------------------------------------
        # 11. Evaluar
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
        # 12. Guardar los 3 archivos que necesita el predictor
        # ------------------------------------------------------------------
        self.stdout.write(f'\nGuardando archivos en {output_dir}...')
        os.makedirs(output_dir, exist_ok=True)

        # 12a. Modelo solo (RandomForestRegressor object)
        model_path = os.path.join(output_dir, 'random_forest_germinacion.joblib')
        joblib.dump(modelo, model_path, compress=3)
        self.stdout.write(f'  Guardado: {model_path}')

        # 12b. Transformador — estructura exacta que usa pickle.load() en el predictor
        transformador = {
            'scaler': scaler,
            'numeric_cols': numeric_cols,
            'top_especies': top_especies,
            'categorical_features': categorical_features,
            'numerical_features': numerical_features,
        }
        transformador_path = os.path.join(output_dir, 'germinacion_transformador.pkl')
        with open(transformador_path, 'wb') as f:
            pickle.dump(transformador, f)
        self.stdout.write(f'  Guardado: {transformador_path}')

        # 12c. Orden de features
        feature_order_path = os.path.join(output_dir, 'feature_order_germinacion.json')
        with open(feature_order_path, 'w', encoding='utf-8') as f:
            json.dump(feature_order, f, indent=2, ensure_ascii=False)
        self.stdout.write(f'  Guardado: {feature_order_path}')

        # ------------------------------------------------------------------
        # 13. Resumen
        # ------------------------------------------------------------------
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('   ENTRENAMIENTO COMPLETADO'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'\n  Modelo:     Random Forest')
        self.stdout.write(f'  Registros:  {len(df):,}')
        self.stdout.write(f'  Features:   {len(feature_order)}')
        self.stdout.write(f'  MAE:        {mae:.2f} dias')
        self.stdout.write(f'  RMSE:       {rmse:.2f} dias')
        self.stdout.write(f'  R2:         {r2:.4f} ({r2 * 100:.2f}%)')
        self.stdout.write(f'\n  Archivos guardados en: {output_dir}')
        self.stdout.write('')
