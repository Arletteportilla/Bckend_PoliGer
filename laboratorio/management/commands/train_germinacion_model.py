"""
Comando Django para entrenar el modelo de predicción de germinaciones
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
    help = 'Entrena el modelo de predicción de días hasta germinación'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            type=str,
            default='data/Germinacion_Consolidado - Consolidado.csv',
            help='Ruta al archivo CSV con datos de germinaciones'
        )
        parser.add_argument(
            '--output-path',
            type=str,
            default='laboratorio/modelos/germinacion.pkl',
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
        self.stdout.write('   ENTRENAMIENTO MODELO GERMINACIÓN')
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

        # La columna 'No_dias_pol' ya contiene los días
        df = df[df['No_dias_pol'].notna()]

        # Filtrar outliers (días muy altos parecen errores)
        df = df[(df['No_dias_pol'] >= 0) & (df['No_dias_pol'] <= 500)]

        if len(df) < 50:
            self.stdout.write(self.style.ERROR(
                f'✗ Datos insuficientes después de limpieza: {len(df)} registros'
            ))
            return

        self.stdout.write(self.style.SUCCESS(f'✓ {len(df)} registros válidos'))

        # 3. Feature engineering
        self.stdout.write('\nCreando features...')

        # Features categóricas
        features = pd.DataFrame()
        features['nombre'] = df['NOMBRE'].fillna('desconocido').astype(str)
        features['tipo_poliniz'] = df['TIPO POLINIZ'].fillna('desconocido').astype(str)
        features['finca'] = df['FINCA'].fillna('desconocida').astype(str)
        features['estado_capsulas'] = df['ESTADO DE CAPSULAS'].fillna('desconocido').astype(str)
        features['etapa'] = df['Etapa'].fillna('desconocida').astype(str)

        # Features numéricas
        features['no_capsulas'] = df['No_CAPSULAS'].fillna(0)

        # Features de fecha
        df['FECHA DE INGRESO'] = pd.to_datetime(df['FECHA DE INGRESO'], errors='coerce')
        features['mes_ingreso'] = df['FECHA DE INGRESO'].dt.month.fillna(0).astype(int)
        features['trimestre'] = df['FECHA DE INGRESO'].dt.quarter.fillna(0).astype(int)

        # Target
        y = df['No_dias_pol']

        # Encoding de variables categóricas
        from sklearn.preprocessing import LabelEncoder

        le_nombre = LabelEncoder()
        le_tipo = LabelEncoder()
        le_finca = LabelEncoder()
        le_estado = LabelEncoder()
        le_etapa = LabelEncoder()

        features['nombre_encoded'] = le_nombre.fit_transform(features['nombre'])
        features['tipo_encoded'] = le_tipo.fit_transform(features['tipo_poliniz'])
        features['finca_encoded'] = le_finca.fit_transform(features['finca'])
        features['estado_encoded'] = le_estado.fit_transform(features['estado_capsulas'])
        features['etapa_encoded'] = le_etapa.fit_transform(features['etapa'])

        # Seleccionar solo features numéricas para el modelo
        X = features[[
            'nombre_encoded', 'tipo_encoded', 'finca_encoded',
            'estado_encoded', 'etapa_encoded', 'no_capsulas',
            'mes_ingreso', 'trimestre'
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
                n_estimators=100,           # Modelo pequeño
                max_depth=10,               # Profundidad limitada
                learning_rate=0.05,
                num_leaves=25,
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
                n_estimators=50,            # Pocos árboles para dataset pequeño
                max_depth=12,
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
        encoders_path = output_path.replace('.pkl', '_encoders.pkl')
        joblib.dump({
            'nombre': le_nombre,
            'tipo': le_tipo,
            'finca': le_finca,
            'estado': le_estado,
            'etapa': le_etapa
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
