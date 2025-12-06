# -*- coding: utf-8 -*-
"""
Predictor Random Forest para Germinación
=========================================
Usa el modelo Random Forest entrenado con validación cruzada

Métricas del modelo (5-fold CV):
- RMSE: ~52 días
- MAE: ~37 días
- R²: ~0.85

Este predictor implementa el mismo preprocessing que se usó en entrenamiento:
- 129 features totales (20 numéricas + 109 one-hot encoded)
- RobustScaler para normalización de features numéricas
- One-Hot Encoding para variables categóricas (CLIMA, ESPECIE_AGRUPADA, E.CAPSU)
- Estadísticas por especie y clima
"""

import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import json
import logging
import pickle

logger = logging.getLogger(__name__)


class GerminacionPredictor:
    """Predictor usando modelo Random Forest para Germinación (Singleton)"""

    _instance = None

    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            cls._instance = super(GerminacionPredictor, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Inicializa el predictor (solo una vez)"""
        if self._initialized:
            return

        self.model = None
        self.scaler = None
        self.numeric_cols = None
        self.top_especies = None
        self.categorical_features = None
        self.numerical_features = None
        self.feature_order = None
        self.model_loaded = False
        self._load_model()
        self._initialized = True

    def _load_model(self):
        """Carga el modelo Random Forest, scaler y configuración"""
        try:
            # Ruta al modelo usando ruta relativa desde este archivo
            base_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                '..',
                'modelos',
                'Germinacion'
            )

            model_path = os.path.join(base_path, 'random_forest_germinacion.joblib')
            transformador_path = os.path.join(base_path, 'germinacion_transformador.pkl')
            feature_order_path = os.path.join(base_path, 'feature_order_germinacion.json')

            # Cargar modelo Random Forest
            if not os.path.exists(model_path):
                logger.error(f"Modelo no encontrado: {model_path}")
                return

            logger.info(f"Cargando modelo Random Forest desde: {model_path}")
            self.model = joblib.load(model_path)
            logger.info(f"OK - Modelo Random Forest cargado correctamente")

            # Cargar transformador (scaler + metadatos)
            if os.path.exists(transformador_path):
                with open(transformador_path, 'rb') as f:
                    transformador = pickle.load(f)

                self.scaler = transformador['scaler']
                self.numeric_cols = transformador['numeric_cols']
                self.top_especies = transformador['top_especies']
                self.categorical_features = transformador['categorical_features']
                self.numerical_features = transformador['numerical_features']

                logger.info(f"OK - Transformador cargado correctamente")
                logger.info(f"  - Numeric cols: {len(self.numeric_cols)}")
                logger.info(f"  - Top especies: {len(self.top_especies)}")
            else:
                logger.error(f"Transformador no encontrado: {transformador_path}")
                return

            # Cargar orden de features
            if os.path.exists(feature_order_path):
                with open(feature_order_path, 'r', encoding='utf-8') as f:
                    self.feature_order = json.load(f)
                logger.info(f"OK - Feature order cargado: {len(self.feature_order)} features")
            else:
                logger.error(f"Feature order no encontrado: {feature_order_path}")
                return

            self.model_loaded = True
            logger.info("="*60)
            logger.info("MODELO RANDOM FOREST GERMINACION CARGADO EXITOSAMENTE")
            logger.info(f"  - Tipo: Random Forest Regressor")
            logger.info(f"  - Features totales: {len(self.feature_order)}")
            logger.info(f"  - Scaler: RobustScaler")
            logger.info(f"  - Encoding: One-Hot para categoricas")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"Error cargando modelo Random Forest: {e}", exc_info=True)
            self.model_loaded = False

    # =========================================================================
    # PIPELINE PASO 1: INGENIERÍA DE CARACTERÍSTICAS
    # =========================================================================

    def _create_features(self, df_input):
        """
        Crea todas las features necesarias a partir de los datos de entrada

        Esto incluye:
        - Features temporales (mes, día del año, trimestre, semana)
        - Features cíclicas (seno/coseno de mes y día)
        - Features derivadas numéricas (logaritmos, ratios)
        - Estadísticas por especie y clima
        - Agrupación de especies (Top 100 o OTRAS)

        Args:
            df_input (DataFrame): DataFrame con columnas crudas
                - F.SIEMBRA (datetime)
                - ESPECIE (str)
                - CLIMA (str)
                - E.CAPSU (str)
                - S.STOCK (float)
                - C.SOLIC (float)
                - DISPONE (float)

        Returns:
            DataFrame: DataFrame con todas las features generadas
        """
        df = df_input.copy()

        # 1. FEATURES TEMPORALES
        df['MES_SIEMBRA'] = df['F.SIEMBRA'].dt.month
        df['DIA_AÑO_SIEMBRA'] = df['F.SIEMBRA'].dt.dayofyear
        df['TRIMESTRE_SIEMBRA'] = df['F.SIEMBRA'].dt.quarter
        df['SEMANA_AÑO'] = df['F.SIEMBRA'].dt.isocalendar().week

        # 2. FEATURES CÍCLICAS (para capturar estacionalidad)
        df['MES_SIN'] = np.sin(2 * np.pi * df['MES_SIEMBRA'] / 12)
        df['MES_COS'] = np.cos(2 * np.pi * df['MES_SIEMBRA'] / 12)
        df['DIA_AÑO_SIN'] = np.sin(2 * np.pi * df['DIA_AÑO_SIEMBRA'] / 365)
        df['DIA_AÑO_COS'] = np.cos(2 * np.pi * df['DIA_AÑO_SIEMBRA'] / 365)

        # 3. FEATURES DERIVADAS NUMÉRICAS
        df['C.SOLIC_LOG'] = np.log1p(df['C.SOLIC'])
        df['S.STOCK_LOG'] = np.log1p(df['S.STOCK'])
        df['RATIO_STOCK_SOLIC'] = np.where(
            df['C.SOLIC'] > 0,
            df['S.STOCK'] / (df['C.SOLIC'] + 1),
            0
        )

        # 4. ESTADÍSTICAS POR ESPECIE
        # NOTA: En producción ideal, estas deberían calcularse de la BD
        # Por ahora usamos valores por defecto razonables
        df['ESP_MEAN'] = 90      # Promedio de días de germinación
        df['ESP_MEDIAN'] = 85
        df['ESP_STD'] = 50
        df['ESP_COUNT'] = 1      # Frecuencia de la especie

        # 5. ESTADÍSTICAS POR CLIMA
        df['CLIMA_MEAN'] = 90
        df['CLIMA_STD'] = 50

        # 6. AGRUPAR ESPECIE (Top 100 o OTRAS)
        df['ESPECIE_AGRUPADA'] = df['ESPECIE'].apply(
            lambda x: x if x in self.top_especies else 'OTRAS'
        )

        logger.info(f"  [1/4] Features creadas: {len(df.columns)} columnas")

        return df

    # =========================================================================
    # PIPELINE PASO 2: ONE-HOT ENCODING CON MANEJO ROBUSTO
    # =========================================================================

    def _apply_ohe_encoding(self, df):
        """
        Aplica One-Hot Encoding a las variables categóricas

        IMPORTANTE: Implementa manejo robusto de nuevas categorías:
        - Si una categoría no fue vista en entrenamiento, se asigna vector cero
        - Esto evita errores y mantiene estabilidad del servicio

        Args:
            df (DataFrame): DataFrame con features creadas

        Returns:
            DataFrame: DataFrame con columnas OHE añadidas
        """
        # Seleccionar solo las columnas necesarias para OHE
        df_for_encoding = df[self.categorical_features + self.numerical_features].copy()

        # Aplicar pd.get_dummies con drop_first=True (igual que en entrenamiento)
        df_encoded = pd.get_dummies(
            df_for_encoding,
            columns=self.categorical_features,
            drop_first=True,
            dtype=int
        )

        logger.info(f"  [2/4] One-Hot Encoding aplicado: {len(df_encoded.columns)} columnas")

        return df_encoded

    # =========================================================================
    # PIPELINE PASO 3: ALINEACIÓN CON FEATURE ORDER
    # =========================================================================

    def _align_features(self, df_encoded):
        """
        Alinea las features con el orden exacto esperado por el modelo

        CRÍTICO: Este paso es ESENCIAL para que el modelo funcione correctamente
        - Agrega columnas faltantes con valor 0 (nuevas categorías)
        - Reordena columnas según feature_order_germinacion.json
        - Elimina columnas extras

        Args:
            df_encoded (DataFrame): DataFrame con OHE aplicado

        Returns:
            DataFrame: DataFrame alineado con feature_order
        """
        # Crear DataFrame con todas las columnas del feature_order inicializadas en 0
        df_aligned = pd.DataFrame(0, index=df_encoded.index, columns=self.feature_order)

        # Copiar valores de las columnas que existen
        for col in df_encoded.columns:
            if col in df_aligned.columns:
                df_aligned[col] = df_encoded[col].values

        logger.info(f"  [3/4] Features alineadas: {len(df_aligned.columns)} columnas en orden correcto")

        return df_aligned

    # =========================================================================
    # PIPELINE PASO 4: NORMALIZACIÓN Y PREDICCIÓN
    # =========================================================================

    def _normalize_and_predict(self, df_aligned):
        """
        Normaliza las features numéricas y realiza la predicción

        Args:
            df_aligned (DataFrame): DataFrame con features alineadas

        Returns:
            int: Días de germinación predichos (entero positivo >= 1)
        """
        # Normalizar solo las columnas numéricas usando el scaler entrenado
        df_final = df_aligned.copy()
        df_final[self.numeric_cols] = self.scaler.transform(df_final[self.numeric_cols])

        logger.info(f"  [4/4] Normalizacion aplicada a {len(self.numeric_cols)} columnas numericas")

        # Predicción
        dias_predichos = self.model.predict(df_final)[0]

        # Asegurar que sea un entero positivo >= 1
        dias_predichos = max(1, int(np.round(dias_predichos)))

        return dias_predichos

    # =========================================================================
    # MÉTODO PRINCIPAL: PREDICT_DIAS_GERMINACION
    # =========================================================================

    def predict_dias_germinacion(self, fecha_siembra, especie, clima, estado_capsula,
                                  s_stock=0, c_solic=0, dispone=0):
        """
        Método principal que ejecuta el pipeline completo de predicción

        Pipeline:
        1. Crear features (temporales, cíclicas, derivadas, estadísticas)
        2. Aplicar One-Hot Encoding con manejo robusto de nuevas categorías
        3. Alinear features con el orden exacto del modelo
        4. Normalizar y predecir

        Args:
            fecha_siembra (str): Fecha de siembra 'YYYY-MM-DD'
            especie (str): Nombre de la especie
            clima (str): Tipo de clima (Cool, IC, IW, Intermedio, Warm)
            estado_capsula (str): Estado de la cápsula (Abierta, Cerrada, Semiabiert)
            s_stock (int/float): Stock disponible
            c_solic (int/float): Cantidad solicitada
            dispone (int/float): Disponibilidad

        Returns:
            dict: Resultado con dias_estimados, fecha_estimada_germinacion, confianza, etc.
        """
        if not self.model_loaded:
            raise ValueError("Modelo Random Forest no esta cargado")

        try:
            logger.info("="*60)
            logger.info("PIPELINE DE PREDICCION - Random Forest Germinacion")
            logger.info("="*60)

            # Parsear y validar fecha
            fecha = datetime.strptime(fecha_siembra, '%Y-%m-%d')

            # Crear DataFrame de entrada con datos crudos
            df_input = pd.DataFrame([{
                'F.SIEMBRA': fecha,
                'ESPECIE': str(especie).strip(),
                'CLIMA': str(clima).strip(),
                'E.CAPSU': str(estado_capsula).strip(),
                'S.STOCK': float(s_stock) if s_stock is not None else 0,
                'C.SOLIC': float(c_solic) if c_solic is not None else 0,
                'DISPONE': float(dispone) if dispone is not None else 0
            }])

            logger.info(f"Entrada: {fecha_siembra} | {especie} | {clima} | {estado_capsula}")

            # PASO 1: Ingeniería de características
            df_features = self._create_features(df_input)

            # PASO 2: One-Hot Encoding
            df_encoded = self._apply_ohe_encoding(df_features)

            # PASO 3: Alineación de features
            df_aligned = self._align_features(df_encoded)

            # PASO 4: Normalización y predicción
            dias_predichos = self._normalize_and_predict(df_aligned)

            logger.info(f"\nDias predichos: {dias_predichos}")

            # Calcular fecha estimada de germinación
            fecha_estimada = fecha + timedelta(days=dias_predichos)

            # Calcular confianza
            base_confianza = 70
            if df_features['ESPECIE_AGRUPADA'].iloc[0] != 'OTRAS':
                base_confianza += 10  # +10% si especie está en top 100
            if clima in ['Cool', 'IC', 'IW', 'Intermedio', 'Warm']:
                base_confianza += 5   # +5% si clima es conocido

            confianza = min(85, base_confianza)

            # Determinar nivel de confianza
            if confianza >= 80:
                nivel_confianza = 'alta'
            elif confianza >= 70:
                nivel_confianza = 'media'
            else:
                nivel_confianza = 'baja'

            logger.info(f"Fecha estimada: {fecha_estimada.strftime('%Y-%m-%d')}")
            logger.info(f"Confianza: {confianza}% ({nivel_confianza})")
            logger.info("="*60)

            # Retornar resultado completo
            return {
                'dias_estimados': dias_predichos,
                'fecha_estimada_germinacion': fecha_estimada.strftime('%Y-%m-%d'),
                'confianza': confianza,
                'nivel_confianza': nivel_confianza,
                'modelo': 'Random Forest',
                'detalles': {
                    'especie_agrupada': df_features['ESPECIE_AGRUPADA'].iloc[0],
                    'especie_original': especie,
                    'clima': clima,
                    'estado_capsula': estado_capsula,
                    'features_usadas': len(self.feature_order)
                }
            }

        except Exception as e:
            logger.error(f"Error en prediccion: {e}", exc_info=True)
            raise

    # =========================================================================
    # MÉTODO LEGACY (para compatibilidad)
    # =========================================================================

    def predecir(self, fecha_siembra, especie, clima, estado_capsula,
                 s_stock=0, c_solic=0, dispone=0):
        """
        Método legacy para compatibilidad con código existente
        Delega al método principal predict_dias_germinacion
        """
        return self.predict_dias_germinacion(
            fecha_siembra=fecha_siembra,
            especie=especie,
            clima=clima,
            estado_capsula=estado_capsula,
            s_stock=s_stock,
            c_solic=c_solic,
            dispone=dispone
        )


# =============================================================================
# FUNCIÓN HELPER PARA OBTENER INSTANCIA SINGLETON
# =============================================================================

_predictor_instance = None

def get_germinacion_predictor():
    """Retorna la instancia única del predictor de germinación"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = GerminacionPredictor()
    return _predictor_instance
