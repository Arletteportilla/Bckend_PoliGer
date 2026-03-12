# -*- coding: utf-8 -*-
"""
Servicio de Reentrenamiento de Modelos ML
==========================================
Permite reentrenar los modelos XGBoost (Polinización) y Random Forest (Germinación)
usando los datos actuales de la base de datos.
"""

import os
import json
import pickle
import logging
from datetime import datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, RobustScaler

logger = logging.getLogger(__name__)

BASE_MODELOS = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'modelos'))

FEATURE_LIST = [
    'mes_pol', 'dia_año_pol', 'trimestre_pol', 'año_pol', 'semana_año',
    'mes_sin', 'mes_cos', 'dia_año_sin', 'dia_año_cos',
    'genero_encoded', 'especie_encoded', 'ubicacion_encoded',
    'responsable_encoded', 'Tipo_encoded', 'cantidad', 'disponible',
]


class ReentrenamientoService:
    MIN_REGISTROS = 1000

    # =========================================================================
    # CONTEOS
    # =========================================================================

    def contar_datos_polinizacion(self):
        """Cuenta registros de Polinizacion finalizados válidos para entrenamiento."""
        from django.db.models import Q
        from ..models import Polinizacion
        return Polinizacion.objects.filter(
            estado_polinizacion='FINALIZADO',
            fechapol__isnull=False,
            fechamad__isnull=False,
        ).filter(
            Q(archivo_origen__isnull=True) | Q(archivo_origen='')
        ).extra(
            where=["(fechamad - fechapol) > 0",
                   "(fechamad - fechapol) < 600"]
        ).count()

    def contar_datos_germinacion(self):
        """Cuenta registros de Germinacion finalizados válidos para entrenamiento."""
        from django.db.models import Q
        from ..models import Germinacion
        return Germinacion.objects.filter(
            estado_germinacion='FINALIZADO',
            fecha_siembra__isnull=False,
            fecha_germinacion__isnull=False,
        ).filter(
            Q(archivo_origen__isnull=True) | Q(archivo_origen='')
        ).extra(
            where=["(fecha_germinacion - fecha_siembra) > 0",
                   "(fecha_germinacion - fecha_siembra) < 800"]
        ).count()

    # =========================================================================
    # REENTRENAMIENTO: POLINIZACIÓN (XGBoost)
    # =========================================================================

    def reentrenar_polinizacion(self):
        """
        Entrena el modelo XGBoost de Polinización con datos actuales de la DB.

        Returns:
            dict con métricas: modelo, registros_usados, mae, rmse, r2, n_features, timestamp
        Raises:
            ValueError si hay menos de MIN_REGISTROS registros válidos.
        """
        try:
            import xgboost as xgb
        except ImportError:
            from sklearn.ensemble import GradientBoostingRegressor as xgb_fallback
            xgb = None

        from ..models import Polinizacion

        logger.info("Iniciando reentrenamiento del modelo de Polinización (XGBoost)...")

        # 1. Leer datos de la DB (solo registros creados en el sistema, no importados)
        from django.db.models import Q
        qs = Polinizacion.objects.filter(
            estado_polinizacion='FINALIZADO',
            fechapol__isnull=False,
            fechamad__isnull=False,
        ).filter(
            Q(archivo_origen__isnull=True) | Q(archivo_origen='')
        ).values(
            'fechapol', 'genero', 'especie', 'ubicacion', 'responsable',
            'Tipo', 'cantidad', 'disponible', 'fechamad'
        )

        registros = list(qs)
        if not registros:
            raise ValueError(f"Datos insuficientes: 0 registros (mínimo {self.MIN_REGISTROS})")

        df = pd.DataFrame(registros)

        # 2. Calcular target y filtrar
        df['fechapol'] = pd.to_datetime(df['fechapol'])
        df['fechamad'] = pd.to_datetime(df['fechamad'])
        df['dias'] = (df['fechamad'] - df['fechapol']).dt.days
        df = df[(df['dias'] > 0) & (df['dias'] < 600)].copy()

        count = len(df)
        if count < self.MIN_REGISTROS:
            raise ValueError(f"Datos insuficientes: {count} registros (mínimo {self.MIN_REGISTROS})")

        logger.info(f"Registros válidos para entrenamiento: {count}")

        # 3. Limpiar strings
        for col in ['genero', 'especie', 'ubicacion', 'responsable', 'Tipo']:
            df[col] = df[col].fillna('').astype(str).str.strip()

        df['responsable'] = df['responsable'].str.upper()
        df['Tipo'] = df['Tipo'].str.upper()

        # Normalizar Tipo
        mapeo_tipos = {
            'HYBRID': 'HYBRID', 'HIBRIDO': 'HYBRID', 'HÍBRIDO': 'HYBRID',
            'HIBRIDA': 'HYBRID', 'HÍBRIDA': 'HYBRID',
            'SELF': 'SELF',
            'SIBBLING': 'SIBBLING', 'SIBLING': 'SIBBLING',
        }
        df['Tipo'] = df['Tipo'].apply(lambda x: mapeo_tipos.get(x, x))

        # Normalizar especie (quitar género si viene incluido)
        def normalizar_especie(row):
            esp = row['especie']
            gen = row['genero']
            if esp.lower().startswith(gen.lower()):
                esp = esp[len(gen):].strip()
            return esp

        df['especie'] = df.apply(normalizar_especie, axis=1)

        # Normalizar ubicación
        def normalizar_ubicacion(ubicacion):
            u = ubicacion.replace(' - ', ' ')
            if 'P-' in u:
                partes = u.split()
                for i, p in enumerate(partes):
                    if p.startswith('P-') and len(p) == 3 and p[2].isdigit():
                        partes[i] = f'P-{chr(ord("A") + int(p[2]))}'
                u = ' '.join(partes)
            return u

        df['ubicacion'] = df['ubicacion'].apply(normalizar_ubicacion)

        # 4. Feature engineering temporal
        df['mes_pol'] = df['fechapol'].dt.month
        df['dia_año_pol'] = df['fechapol'].dt.dayofyear
        df['trimestre_pol'] = df['fechapol'].dt.quarter
        df['año_pol'] = df['fechapol'].dt.year
        df['semana_año'] = df['fechapol'].dt.isocalendar().week.astype(int)

        df['mes_sin'] = np.sin(2 * np.pi * df['mes_pol'] / 12)
        df['mes_cos'] = np.cos(2 * np.pi * df['mes_pol'] / 12)
        df['dia_año_sin'] = np.sin(2 * np.pi * df['dia_año_pol'] / 365)
        df['dia_año_cos'] = np.cos(2 * np.pi * df['dia_año_pol'] / 365)

        # 5. LabelEncoder para categóricas
        le_genero = LabelEncoder()
        le_especie = LabelEncoder()
        le_ubicacion = LabelEncoder()
        le_responsable = LabelEncoder()
        le_tipo = LabelEncoder()

        df['genero_encoded'] = le_genero.fit_transform(df['genero'])
        df['especie_encoded'] = le_especie.fit_transform(df['especie'])
        df['ubicacion_encoded'] = le_ubicacion.fit_transform(df['ubicacion'])
        df['responsable_encoded'] = le_responsable.fit_transform(df['responsable'])
        df['Tipo_encoded'] = le_tipo.fit_transform(df['Tipo'])

        df['cantidad'] = pd.to_numeric(df['cantidad'], errors='coerce').fillna(1).astype(int)
        df['disponible'] = df['disponible'].apply(lambda x: int(bool(x)))

        # 6. Preparar X, y
        X = df[FEATURE_LIST].astype(float)
        y = df['dias'].astype(float)

        # 7. Entrenar modelo
        if xgb is not None:
            modelo = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                tree_method='hist',
            )
        else:
            from sklearn.ensemble import GradientBoostingRegressor
            modelo = GradientBoostingRegressor(
                n_estimators=200,
                max_depth=5,
                learning_rate=0.05,
                random_state=42,
            )

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        modelo.fit(X_train, y_train)

        # 8. Calcular métricas en conjunto de test (no contaminado)
        y_pred = modelo.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        logger.info(f"Métricas Polinización — MAE: {mae:.2f}d, RMSE: {rmse:.2f}d, R²: {r2:.4f}")

        # 9. Guardar archivos
        output_dir = os.path.join(BASE_MODELOS, 'Polinizacion')
        os.makedirs(output_dir, exist_ok=True)

        joblib.dump(modelo, os.path.join(output_dir, 'polinizacion.joblib'), compress=3)

        with open(os.path.join(output_dir, 'label_encoders.pkl'), 'wb') as f:
            pickle.dump({
                'genero': le_genero,
                'especie': le_especie,
                'ubicacion': le_ubicacion,
                'responsable': le_responsable,
                'Tipo': le_tipo,
            }, f)

        timestamp = datetime.now().isoformat()
        metadata = {
            'feature_list': FEATURE_LIST,
            'n_features': len(FEATURE_LIST),
            'registros_usados': count,
            'mae': mae,
            'rmse': rmse,
            'r2': r2,
            'timestamp': timestamp,
            'modelo': 'XGBoost' if xgb is not None else 'GradientBoosting',
        }
        with open(os.path.join(output_dir, 'features_metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info("Modelo de Polinización guardado correctamente.")

        return {
            'modelo': 'XGBoost' if xgb is not None else 'GradientBoosting',
            'registros_usados': count,
            'mae': round(mae, 4),
            'rmse': round(rmse, 4),
            'r2': round(r2, 4),
            'n_features': len(FEATURE_LIST),
            'timestamp': timestamp,
        }

    # =========================================================================
    # REENTRENAMIENTO: GERMINACIÓN (Random Forest)
    # =========================================================================

    def reentrenar_germinacion(self):
        """
        Entrena el modelo Random Forest de Germinación con datos actuales de la DB.

        Returns:
            dict con métricas: modelo, registros_usados, mae, rmse, r2, n_features, timestamp
        Raises:
            ValueError si hay menos de MIN_REGISTROS registros válidos.
        """
        from sklearn.ensemble import RandomForestRegressor
        from ..models import Germinacion

        logger.info("Iniciando reentrenamiento del modelo de Germinación (Random Forest)...")

        categorical_features = ['ESPECIE_AGRUPADA', 'CLIMA', 'E.CAPSU']
        numerical_features = [
            'MES_SIEMBRA', 'DIA_AÑO_SIEMBRA', 'TRIMESTRE_SIEMBRA', 'SEMANA_AÑO',
            'MES_SIN', 'MES_COS', 'DIA_AÑO_SIN', 'DIA_AÑO_COS',
            'C.SOLIC_LOG', 'S.STOCK_LOG', 'RATIO_STOCK_SOLIC',
            'ESP_MEAN', 'ESP_MEDIAN', 'ESP_STD', 'ESP_COUNT',
            'CLIMA_MEAN', 'CLIMA_STD',
            'S.STOCK', 'C.SOLIC', 'DISPONE',
        ]

        # 1. Leer datos de la DB (solo registros creados en el sistema, no importados)
        from django.db.models import Q
        qs = Germinacion.objects.filter(
            estado_germinacion='FINALIZADO',
            fecha_siembra__isnull=False,
            fecha_germinacion__isnull=False,
        ).filter(
            Q(archivo_origen__isnull=True) | Q(archivo_origen='')
        ).values(
            'fecha_siembra', 'especie_variedad', 'clima', 'estado_capsula',
            'semillas_stock', 'cantidad_solicitada', 'disponibles', 'fecha_germinacion'
        )

        registros = list(qs)
        if not registros:
            raise ValueError(f"Datos insuficientes: 0 registros (mínimo {self.MIN_REGISTROS})")

        df = pd.DataFrame(registros)

        # 2. Calcular target y filtrar
        df['fecha_siembra'] = pd.to_datetime(df['fecha_siembra'])
        df['fecha_germinacion'] = pd.to_datetime(df['fecha_germinacion'])
        df['dias'] = (df['fecha_germinacion'] - df['fecha_siembra']).dt.days
        df = df[(df['dias'] > 0) & (df['dias'] < 800)].copy()

        count = len(df)
        if count < self.MIN_REGISTROS:
            raise ValueError(f"Datos insuficientes: {count} registros (mínimo {self.MIN_REGISTROS})")

        logger.info(f"Registros válidos para entrenamiento: {count}")

        # 3. Renombrar columnas al formato del modelo
        df = df.rename(columns={
            'fecha_siembra': 'F.SIEMBRA',
            'especie_variedad': 'ESPECIE',
            'clima': 'CLIMA',
            'estado_capsula': 'E.CAPSU',
            'semillas_stock': 'S.STOCK',
            'cantidad_solicitada': 'C.SOLIC',
            'disponibles': 'DISPONE',
        })

        # Limpiar
        for col in ['ESPECIE', 'CLIMA', 'E.CAPSU']:
            df[col] = df[col].fillna('').astype(str).str.strip()

        df['S.STOCK'] = pd.to_numeric(df['S.STOCK'], errors='coerce').fillna(0).astype(float)
        df['C.SOLIC'] = pd.to_numeric(df['C.SOLIC'], errors='coerce').fillna(0).astype(float)
        df['DISPONE'] = pd.to_numeric(df['DISPONE'], errors='coerce').fillna(0).astype(float)

        # 4. Feature engineering temporal
        df['MES_SIEMBRA'] = df['F.SIEMBRA'].dt.month
        df['DIA_AÑO_SIEMBRA'] = df['F.SIEMBRA'].dt.dayofyear
        df['TRIMESTRE_SIEMBRA'] = df['F.SIEMBRA'].dt.quarter
        df['SEMANA_AÑO'] = df['F.SIEMBRA'].dt.isocalendar().week.astype(int)

        df['MES_SIN'] = np.sin(2 * np.pi * df['MES_SIEMBRA'] / 12)
        df['MES_COS'] = np.cos(2 * np.pi * df['MES_SIEMBRA'] / 12)
        df['DIA_AÑO_SIN'] = np.sin(2 * np.pi * df['DIA_AÑO_SIEMBRA'] / 365)
        df['DIA_AÑO_COS'] = np.cos(2 * np.pi * df['DIA_AÑO_SIEMBRA'] / 365)

        # 5. Features derivadas numéricas
        df['C.SOLIC_LOG'] = np.log1p(df['C.SOLIC'])
        df['S.STOCK_LOG'] = np.log1p(df['S.STOCK'])
        df['RATIO_STOCK_SOLIC'] = np.where(
            df['C.SOLIC'] > 0,
            df['S.STOCK'] / (df['C.SOLIC'] + 1),
            0
        )

        # 6. Estadísticas hardcodeadas (iguales a las del predictor)
        df['ESP_MEAN'] = 90.0
        df['ESP_MEDIAN'] = 85.0
        df['ESP_STD'] = 50.0
        df['ESP_COUNT'] = 1.0
        df['CLIMA_MEAN'] = 90.0
        df['CLIMA_STD'] = 50.0

        # 7. Determinar top_especies (top 100 más frecuentes)
        top_especies = list(df['ESPECIE'].value_counts().head(100).index)

        # 8. Agrupar especie
        df['ESPECIE_AGRUPADA'] = df['ESPECIE'].apply(
            lambda x: x if x in top_especies else 'OTRAS'
        )

        # 9. One-Hot Encoding
        df_for_ohe = df[categorical_features + numerical_features].copy()
        df_encoded = pd.get_dummies(
            df_for_ohe,
            columns=categorical_features,
            drop_first=True,
            dtype=int
        )

        # 10. Determinar columnas numéricas para el scaler
        numeric_cols = [c for c in df_encoded.columns if c in numerical_features]

        # 11. Ajustar RobustScaler
        scaler = RobustScaler()
        df_encoded[numeric_cols] = scaler.fit_transform(df_encoded[numeric_cols])

        # 12. Feature order
        feature_order = list(df_encoded.columns)

        # 13. Preparar X, y
        X = df_encoded.astype(float)
        y = df['dias'].astype(float)

        # 14. Entrenar modelo
        modelo = RandomForestRegressor(
            n_estimators=200,
            max_depth=None,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1,
        )
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        modelo.fit(X_train, y_train)

        # 15. Calcular métricas en conjunto de test (no contaminado)
        y_pred = modelo.predict(X_test)
        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        logger.info(f"Métricas Germinación — MAE: {mae:.2f}d, RMSE: {rmse:.2f}d, R²: {r2:.4f}")

        # 16. Guardar archivos
        output_dir = os.path.join(BASE_MODELOS, 'Germinacion')
        os.makedirs(output_dir, exist_ok=True)

        joblib.dump(modelo, os.path.join(output_dir, 'random_forest_germinacion.joblib'), compress=3)

        with open(os.path.join(output_dir, 'germinacion_transformador.pkl'), 'wb') as f:
            pickle.dump({
                'scaler': scaler,
                'numeric_cols': numeric_cols,
                'top_especies': top_especies,
                'categorical_features': categorical_features,
                'numerical_features': numerical_features,
            }, f)

        timestamp = datetime.now().isoformat()
        with open(os.path.join(output_dir, 'feature_order_germinacion.json'), 'w', encoding='utf-8') as f:
            json.dump(feature_order, f, indent=2, ensure_ascii=False)

        logger.info("Modelo de Germinación guardado correctamente.")

        return {
            'modelo': 'Random Forest',
            'registros_usados': count,
            'mae': round(mae, 4),
            'rmse': round(rmse, 4),
            'r2': round(r2, 4),
            'n_features': len(feature_order),
            'timestamp': timestamp,
        }

    # =========================================================================
    # REENTRENAMIENTO: AMBOS
    # =========================================================================

    def reentrenar_ambos(self):
        """
        Reentrena ambos modelos (Polinización y Germinación).

        Returns:
            dict con claves 'polinizacion' y 'germinacion', cada una con sus métricas.
        Raises:
            ValueError si alguno de los modelos tiene datos insuficientes.
        """
        resultado_pol = self.reentrenar_polinizacion()
        resultado_germ = self.reentrenar_germinacion()
        return {
            'polinizacion': resultado_pol,
            'germinacion': resultado_germ,
        }


# Instancia global
reentrenamiento_service = ReentrenamientoService()
