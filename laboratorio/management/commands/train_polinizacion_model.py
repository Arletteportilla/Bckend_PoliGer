"""
Comando Django para entrenar el modelo de predicción de polinizaciones
Basado en el modelo XGBoost con 94.91% de precisión
"""
from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from xgboost import XGBRegressor
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    from sklearn.ensemble import RandomForestRegressor


class Command(BaseCommand):
    help = 'Entrena el modelo de predicción de días hasta maduración de polinizaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='prediccion/polinizacion/datos_limpios.csv',
            help='Ruta al archivo CSV con datos de polinizaciones'
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default='laboratorio/modelos/polinizacion.pkl',
            help='Ruta donde guardar el modelo entrenado'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        output_path = options['output_path']

        self.stdout.write('=' * 80)
        self.stdout.write('   ENTRENAMIENTO MODELO POLINIZACIÓN')
        self.stdout.write('=' * 80)
        self.stdout.write('')

        if not XGBOOST_AVAILABLE:
            self.stdout.write(self.style.WARNING(
                '⚠ XGBoost no disponible, usando Random Forest como alternativa'
            ))

        # 1. Cargar datos
        self.stdout.write(f'Cargando datos desde {csv_path}...')
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            df['fechapol'] = pd.to_datetime(df['fechapol'])
            df['fechamad'] = pd.to_datetime(df['fechamad'])
            self.stdout.write(self.style.SUCCESS(f'✓ {len(df):,} registros cargados'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error cargando CSV: {e}'))
            return

        # 2. Feature Engineering Avanzado
        self.stdout.write('\nCreando features avanzadas...')

        # Features temporales básicas
        df['mes_pol'] = df['fechapol'].dt.month
        df['dia_anio_pol'] = df['fechapol'].dt.dayofyear
        df['semana_pol'] = df['fechapol'].dt.isocalendar().week

        # Features cíclicas (importantes para estacionalidad)
        df['mes_sin'] = np.sin(2 * np.pi * df['mes_pol'] / 12)
        df['mes_cos'] = np.cos(2 * np.pi * df['mes_pol'] / 12)
        df['dia_anio_sin'] = np.sin(2 * np.pi * df['dia_anio_pol'] / 365)
        df['dia_anio_cos'] = np.cos(2 * np.pi * df['dia_anio_pol'] / 365)
        df['semana_sin'] = np.sin(2 * np.pi * df['semana_pol'] / 52)
        df['semana_cos'] = np.cos(2 * np.pi * df['semana_pol'] / 52)

        # Estadísticas por especie
        species_stats = df.groupby(['genero', 'especie'])['dias_maduracion'].agg([
            ('especie_media', 'mean'),
            ('especie_mediana', 'median'),
            ('especie_std', 'std'),
            ('especie_min', 'min'),
            ('especie_max', 'max'),
            ('especie_count', 'count')
        ]).reset_index()
        df = df.merge(species_stats, on=['genero', 'especie'], how='left')

        # Estadísticas por género
        genus_stats = df.groupby('genero')['dias_maduracion'].agg([
            ('genero_media', 'mean'),
            ('genero_std', 'std'),
            ('genero_count', 'count')
        ]).reset_index()
        df = df.merge(genus_stats, on='genero', how='left')

        # Estadísticas por tipo
        tipo_stats = df.groupby('Tipo')['dias_maduracion'].agg([
            ('tipo_media', 'mean'),
            ('tipo_std', 'std')
        ]).reset_index()
        df = df.merge(tipo_stats, on='Tipo', how='left')

        # Rellenar valores faltantes
        for col in df.columns:
            if df[col].dtype in ['float64', 'int64'] and df[col].isnull().any():
                if 'std' in col:
                    df[col] = df[col].fillna(df['dias_maduracion'].std())
                elif 'count' in col:
                    df[col] = df[col].fillna(1)
                else:
                    df[col] = df[col].fillna(df['dias_maduracion'].mean())

        # Label Encoding
        le_genero = LabelEncoder()
        le_especie = LabelEncoder()
        le_tipo = LabelEncoder()

        df['genero_encoded'] = le_genero.fit_transform(df['genero'])
        df['especie_encoded'] = le_especie.fit_transform(df['genero'] + '_' + df['especie'])
        df['tipo_encoded'] = le_tipo.fit_transform(df['Tipo'])

        # Features de interacción
        df['genero_tipo_encoded'] = df['genero_encoded'] * 100 + df['tipo_encoded']

        self.stdout.write(self.style.SUCCESS('✓ Features creadas'))

        # 3. Preparar features y target
        feature_columns = [
            # Codificación categórica
            'genero_encoded', 'especie_encoded', 'tipo_encoded', 'genero_tipo_encoded',

            # Features temporales cíclicas
            'mes_sin', 'mes_cos', 'dia_anio_sin', 'dia_anio_cos',
            'semana_sin', 'semana_cos',

            # Estadísticas de especie
            'especie_media', 'especie_mediana', 'especie_std',
            'especie_min', 'especie_max', 'especie_count',

            # Estadísticas de género
            'genero_media', 'genero_std', 'genero_count',

            # Estadísticas de tipo
            'tipo_media', 'tipo_std',

            # Feature directa
            'cantidad'
        ]

        X = df[feature_columns].copy()
        y = df['dias_maduracion'].copy()

        # Escalar
        scaler = RobustScaler()
        X_scaled = scaler.fit_transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=feature_columns)

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y, test_size=0.15, random_state=42
        )

        self.stdout.write(f'\nFeatures totales: {len(feature_columns)}')
        self.stdout.write(f'Train: {len(X_train):,}, Test: {len(X_test):,}')

        # 4. Entrenar modelo
        self.stdout.write('\nEntrenando modelo...')

        if XGBOOST_AVAILABLE:
            modelo = XGBRegressor(
                n_estimators=300,
                learning_rate=0.1,
                max_depth=5,
                subsample=0.9,
                colsample_bytree=0.8,
                random_state=42,
                n_jobs=-1
            )
            model_name = 'XGBoost'
        else:
            modelo = RandomForestRegressor(
                n_estimators=400,
                max_depth=25,
                min_samples_split=2,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1
            )
            model_name = 'Random Forest'

        modelo.fit(X_train, y_train)
        self.stdout.write(self.style.SUCCESS(f'✓ Modelo {model_name} entrenado'))

        # 5. Evaluar modelo
        self.stdout.write('\nEvaluando modelo...')
        y_pred = modelo.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        self.stdout.write(f'  MAE: {mae:.2f} días')
        self.stdout.write(f'  RMSE: {rmse:.2f} días')
        self.stdout.write(f'  R²: {r2:.4f} ({r2*100:.2f}%)')

        # 6. Guardar modelo empaquetado
        self.stdout.write(f'\nGuardando modelo en {output_path}...')

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        model_package = {
            'model': modelo,
            'scaler': scaler,
            'label_encoders': {
                'genero': le_genero,
                'especie': le_especie,
                'tipo': le_tipo
            },
            'feature_columns': feature_columns,
            'species_stats': species_stats,
            'genus_stats': genus_stats,
            'tipo_stats': tipo_stats,
            'metadata': {
                'model_name': model_name,
                'test_mae': mae,
                'test_rmse': rmse,
                'test_r2': r2,
                'precision_percent': r2 * 100,
                'n_features': len(feature_columns),
                'n_samples': len(df),
                'fecha_entrenamiento': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }

        joblib.dump(model_package, output_path, compress=3)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)

        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write(self.style.SUCCESS('   ✓ ENTRENAMIENTO COMPLETADO'))
        self.stdout.write('=' * 80)
        self.stdout.write(f'\n  Modelo: {model_name}')
        self.stdout.write(f'  Registros: {len(df):,}')
        self.stdout.write(f'  Features: {len(feature_columns)}')
        self.stdout.write(f'  MAE: {mae:.2f} días')
        self.stdout.write(f'  RMSE: {rmse:.2f} días')
        self.stdout.write(f'  R²: {r2:.4f} ({r2*100:.2f}%)')
        self.stdout.write(f'\n  Archivo: {output_path}')
        self.stdout.write(f'  Tamaño: {size_mb:.2f} MB')
        self.stdout.write('')
