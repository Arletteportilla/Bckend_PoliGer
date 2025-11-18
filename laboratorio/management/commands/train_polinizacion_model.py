"""
Comando Django para entrenar el modelo de predicción de polinizaciones
Usa LightGBM para modelos más pequeños y rápidos
"""
from django.core.management.base import BaseCommand
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


class Command(BaseCommand):
    help = 'Entrena el modelo de predicción de días de maduración de polinizaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='data/datos_combinados_limpios.csv',
            help='Ruta al archivo CSV con datos de polinizaciones'
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default='laboratorio/modelos/Polinizacion_fallback.bin',
            help='Ruta donde guardar el modelo entrenado'
        )
        parser.add_argument(
            '--model-type',
            type=str,
            default='lightgbm',
            choices=['lightgbm', 'randomforest'],
            help='Tipo de modelo a entrenar'
        )

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        output_path = options['output_path']
        model_type = options['model_type']

        self.stdout.write('=' * 60)
        self.stdout.write('   ENTRENAMIENTO MODELO POLINIZACIÓN')
        self.stdout.write('=' * 60)
        self.stdout.write('')

        # 1. Cargar datos
        self.stdout.write(f'Cargando datos desde {csv_path}...')
        try:
            df = pd.read_csv(csv_path)
            self.stdout.write(self.style.SUCCESS(f'✓ {len(df)} registros cargados'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error cargando CSV: {e}'))
            return

        # 2. Preparar datos
        self.stdout.write('\nPreparando datos...')

        # Convertir fechas y calcular target
        df['fechapol'] = pd.to_datetime(df['fechapol'], errors='coerce')
        df['fechamad'] = pd.to_datetime(df['fechamad'], errors='coerce')
        df['dias_maduracion'] = (df['fechamad'] - df['fechapol']).dt.days

        # Filtrar datos válidos
        df = df[df['dias_maduracion'].notna()]

        # Filtrar outliers (días negativos o muy altos)
        df = df[(df['dias_maduracion'] >= 0) & (df['dias_maduracion'] <= 1000)]

        if len(df) < 100:
            self.stdout.write(self.style.ERROR(
                f'✗ Datos insuficientes después de limpieza: {len(df)} registros'
            ))
            return

        self.stdout.write(self.style.SUCCESS(f'✓ {len(df)} registros válidos'))

        # 3. Feature engineering
        self.stdout.write('\nCreando features...')

        # Features categóricas
        features = pd.DataFrame()
        features['genero'] = df['genero'].astype(str)
        features['especie'] = df['especie'].astype(str)
        features['ubicacion'] = df['ubicacion'].fillna('desconocida').astype(str)
        features['responsable'] = df['responsable'].fillna('desconocido').astype(str)

        # Features numéricas
        features['cantidad'] = df['cantidad'].fillna(0)
        features['disponible'] = df['disponible'].fillna(0)

        # Features de tiempo
        features['mes_polinizacion'] = df['fechapol'].dt.month
        features['trimestre'] = df['fechapol'].dt.quarter

        # Target
        y = df['dias_maduracion']

        # Encoding de variables categóricas (LabelEncoding para reducir tamaño)
        from sklearn.preprocessing import LabelEncoder

        le_genero = LabelEncoder()
        le_especie = LabelEncoder()
        le_ubicacion = LabelEncoder()
        le_responsable = LabelEncoder()

        features['genero_encoded'] = le_genero.fit_transform(features['genero'])
        features['especie_encoded'] = le_especie.fit_transform(features['especie'])
        features['ubicacion_encoded'] = le_ubicacion.fit_transform(features['ubicacion'])
        features['responsable_encoded'] = le_responsable.fit_transform(features['responsable'])

        # Seleccionar solo features numéricas para el modelo
        X = features[[
            'genero_encoded', 'especie_encoded', 'ubicacion_encoded',
            'responsable_encoded', 'cantidad', 'disponible',
            'mes_polinizacion', 'trimestre'
        ]]

        self.stdout.write(self.style.SUCCESS(f'✓ {X.shape[1]} features creadas'))

        # 4. Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        self.stdout.write(f'\nDatos de entrenamiento: {len(X_train)}')
        self.stdout.write(f'Datos de prueba: {len(X_test)}')

        # 5. Entrenar modelo
        self.stdout.write(f'\nEntrenando modelo {model_type}...')

        if model_type == 'lightgbm':
            modelo = lgb.LGBMRegressor(
                n_estimators=150,           # Reducido para menor tamaño
                max_depth=12,               # Profundidad limitada
                learning_rate=0.05,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                n_jobs=-1,
                random_state=42,
                verbose=-1
            )
        else:  # randomforest
            from sklearn.ensemble import RandomForestRegressor
            modelo = RandomForestRegressor(
                n_estimators=100,
                max_depth=15,
                min_samples_split=10,
                min_samples_leaf=5,
                max_features='sqrt',
                n_jobs=-1,
                random_state=42
            )

        modelo.fit(X_train, y_train)
        self.stdout.write(self.style.SUCCESS('✓ Modelo entrenado'))

        # 6. Evaluar modelo
        self.stdout.write('\nEvaluando modelo...')
        y_pred = modelo.predict(X_test)

        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        self.stdout.write(f'  MAE (Error Absoluto Medio): {mae:.2f} días')
        self.stdout.write(f'  R² Score: {r2:.4f}')

        # 7. Guardar modelo con compresión máxima
        self.stdout.write(f'\nGuardando modelo en {output_path}...')

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Guardar con compresión máxima
        joblib.dump(modelo, output_path, compress=9)

        # Guardar también los encoders
        encoders_path = output_path.replace('.bin', '_encoders.bin')
        joblib.dump({
            'genero': le_genero,
            'especie': le_especie,
            'ubicacion': le_ubicacion,
            'responsable': le_responsable
        }, encoders_path, compress=9)

        # Verificar tamaño
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        encoders_size_mb = os.path.getsize(encoders_path) / (1024 * 1024)

        self.stdout.write('')
        self.stdout.write('=' * 60)
        self.stdout.write(self.style.SUCCESS('   ✓ ENTRENAMIENTO COMPLETADO'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\n  Registros usados: {len(df)}')
        self.stdout.write(f'  Tipo de modelo: {model_type}')
        self.stdout.write(f'  Features: {X.shape[1]}')
        self.stdout.write(f'  MAE: {mae:.2f} días')
        self.stdout.write(f'  R²: {r2:.4f}')
        self.stdout.write(f'\n  Modelo guardado: {output_path}')
        self.stdout.write(f'  Tamaño modelo: {size_mb:.2f} MB')
        self.stdout.write(f'  Encoders guardados: {encoders_path}')
        self.stdout.write(f'  Tamaño encoders: {encoders_size_mb:.2f} MB')
        self.stdout.write(f'\n  Tamaño total: {size_mb + encoders_size_mb:.2f} MB')
        self.stdout.write('')
