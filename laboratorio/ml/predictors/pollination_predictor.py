"""
PollinationPredictor - Predictor de DIAS_MADURACION usando XGBoost
Implementa patrón Singleton para carga única del modelo en memoria
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class PollinationPredictorError(Exception):
    """Excepción base para errores del predictor"""
    pass


class ModelNotLoadedError(PollinationPredictorError):
    """Error cuando el modelo no está cargado"""
    pass


class InvalidInputError(PollinationPredictorError):
    """Error cuando los datos de entrada son inválidos"""
    pass


class PollinationPredictor:
    """
    Predictor Singleton para polinización usando XGBoost
    Carga modelo, encoders y metadata una sola vez en memoria
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Implementación del patrón Singleton"""
        if cls._instance is None:
            cls._instance = super(PollinationPredictor, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Constructor - solo inicializa si no ha sido inicializado antes"""
        if not self._initialized:
            self.model = None
            self.label_encoders = None
            self.feature_list = None
            self.categorical_columns = None
            self.feature_info = None
            self._model_loaded = False

            # Intentar cargar el modelo automáticamente
            try:
                self.initialize()
            except Exception as e:
                logger.warning(f"No se pudo cargar el modelo automáticamente: {e}")

    def initialize(self) -> bool:
        """
        Carga el modelo, encoders y metadata desde disco
        Returns:
            bool: True si la carga fue exitosa
        """
        if self._initialized:
            logger.info("PollinationPredictor ya estaba inicializado")
            return True

        try:
            logger.info("Inicializando PollinationPredictor...")

            # Determinar ruta del modelo
            # settings.BASE_DIR apunta a 'backend', necesitamos ir a 'laboratorio/modelos/Polinizacion'
            model_dir = os.path.join(settings.BASE_DIR, 'laboratorio', 'modelos', 'Polinizacion')
            logger.info(f"Directorio del modelo: {model_dir}")

            if not os.path.exists(model_dir):
                raise PollinationPredictorError(f"Directorio del modelo no existe: {model_dir}")

            # Cargar modelo XGBoost
            model_path = os.path.join(model_dir, 'polinizacion.joblib')
            if not os.path.exists(model_path):
                raise PollinationPredictorError(f"Modelo no encontrado: {model_path}")

            logger.info(f"Cargando modelo desde: {model_path}")
            self.model = joblib.load(model_path)
            logger.info(f"Modelo cargado: {type(self.model)}")

            # Cargar label encoders
            encoders_path = os.path.join(model_dir, 'label_encoders.pkl')
            if not os.path.exists(encoders_path):
                raise PollinationPredictorError(f"Encoders no encontrados: {encoders_path}")

            logger.info(f"Cargando encoders desde: {encoders_path}")
            self.label_encoders = joblib.load(encoders_path)
            logger.info(f"Encoders cargados: {list(self.label_encoders.keys())}")

            # Cargar metadata de features
            metadata_path = os.path.join(model_dir, 'features_metadata.json')
            if not os.path.exists(metadata_path):
                raise PollinationPredictorError(f"Metadata no encontrada: {metadata_path}")

            logger.info(f"Cargando metadata desde: {metadata_path}")
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

            self.feature_list = metadata['feature_list']
            self.categorical_columns = metadata['categorical_columns']
            self.feature_info = metadata['feature_info']

            logger.info(f"Features cargadas: {len(self.feature_list)} features")
            logger.info(f"Columnas categóricas: {self.categorical_columns}")

            self._model_loaded = True
            self.__class__._initialized = True

            logger.info("[OK] PollinationPredictor inicializado correctamente")
            return True

        except Exception as e:
            logger.error(f"[ERROR] Error inicializando PollinationPredictor: {e}")
            self._model_loaded = False
            raise PollinationPredictorError(f"Error en inicialización: {e}")

    def is_loaded(self) -> bool:
        """Verifica si el modelo está cargado"""
        return self._model_loaded

    def _validate_input(self, data: Dict[str, Any]) -> None:
        """
        Valida que los datos de entrada contengan los campos requeridos

        Args:
            data: Diccionario con datos de entrada

        Raises:
            InvalidInputError: Si faltan campos requeridos
        """
        required_fields = self.feature_info['input_columns_required']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]

        if missing_fields:
            raise InvalidInputError(f"Campos requeridos faltantes: {', '.join(missing_fields)}")

        # Validar formato de fecha
        if 'fechapol' in data:
            try:
                if isinstance(data['fechapol'], str):
                    datetime.strptime(data['fechapol'], '%Y-%m-%d')
            except ValueError:
                raise InvalidInputError("Formato de fecha inválido. Use 'YYYY-MM-DD'")

    def _extract_temporal_features(self, fecha_pol: datetime) -> Dict[str, Any]:
        """
        Extrae features temporales de la fecha de polinización

        Args:
            fecha_pol: Fecha de polinización

        Returns:
            Diccionario con features temporales
        """
        mes_pol = fecha_pol.month
        dia_año_pol = fecha_pol.timetuple().tm_yday
        trimestre_pol = (mes_pol - 1) // 3 + 1
        año_pol = fecha_pol.year
        semana_año = fecha_pol.isocalendar()[1]

        # Features cíclicas para capturar naturaleza circular del tiempo
        mes_sin = np.sin(2 * np.pi * mes_pol / 12)
        mes_cos = np.cos(2 * np.pi * mes_pol / 12)
        dia_año_sin = np.sin(2 * np.pi * dia_año_pol / 365)
        dia_año_cos = np.cos(2 * np.pi * dia_año_pol / 365)

        return {
            'mes_pol': mes_pol,
            'dia_año_pol': dia_año_pol,
            'trimestre_pol': trimestre_pol,
            'año_pol': año_pol,
            'semana_año': semana_año,
            'mes_sin': mes_sin,
            'mes_cos': mes_cos,
            'dia_año_sin': dia_año_sin,
            'dia_año_cos': dia_año_cos
        }

    def _encode_categorical(self, value: str, column_name: str) -> int:
        """
        Codifica una variable categórica usando LabelEncoder

        MANEJO DE NUEVAS CATEGORÍAS:
        - Si la categoría existe en encoder.classes_: usa transform()
        - Si la categoría NO existe: asigna len(encoder.classes_) como fallback seguro

        Args:
            value: Valor a codificar
            column_name: Nombre de la columna categórica

        Returns:
            Valor codificado (int)
        """
        try:
            encoder = self.label_encoders[column_name]

            # Intentar transformar el valor
            try:
                encoded_value = encoder.transform([value])[0]
                logger.debug(f"✅ '{value}' codificado como {encoded_value} para '{column_name}'")
                return int(encoded_value)
            except (ValueError, KeyError):
                # Categoría no vista en entrenamiento - usar fallback seguro
                fallback_value = len(encoder.classes_)
                logger.warning(
                    f"[WARN] Categoria nueva: '{value}' no existe en '{column_name}'. "
                    f"Usando fallback={fallback_value} (total categorias conocidas: {len(encoder.classes_)})"
                )
                return fallback_value

        except KeyError:
            raise InvalidInputError(f"[ERROR] No hay encoder para columna: {column_name}")
        except Exception as e:
            logger.error(f"[ERROR] Error inesperado codificando '{value}' para '{column_name}': {e}")
            raise InvalidInputError(f"Error en encoding de {column_name}: {e}")

    def prepare_features(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        Prepara las features en el orden correcto para el modelo

        Args:
            data: Diccionario con datos de entrada

        Returns:
            DataFrame con features preparadas
        """
        if not self.is_loaded():
            raise ModelNotLoadedError("Modelo no está cargado. Llame a initialize() primero.")

        # Validar entrada
        self._validate_input(data)

        # Convertir fecha a datetime si es string
        fecha_pol = data['fechapol']
        if isinstance(fecha_pol, str):
            fecha_pol = datetime.strptime(fecha_pol, '%Y-%m-%d')

        # Extraer features temporales
        temporal_features = self._extract_temporal_features(fecha_pol)

        # Codificar variables categóricas
        categorical_encoded = {}
        for col in self.categorical_columns:
            value = str(data[col]) if data[col] is not None else ''
            encoded_col_name = f"{col}_encoded"
            categorical_encoded[encoded_col_name] = self._encode_categorical(value, col)

        # Combinar todas las features
        features = {}
        features.update(temporal_features)
        features.update(categorical_encoded)
        features['cantidad'] = int(data.get('cantidad', 0))
        features['disponible'] = int(data.get('disponible', 0))

        # Crear DataFrame con features en el orden exacto del entrenamiento
        feature_dict = {feature: [features[feature]] for feature in self.feature_list}
        X = pd.DataFrame(feature_dict)

        logger.debug(f"Features preparadas: {X.columns.tolist()}")
        logger.debug(f"Valores: {X.iloc[0].to_dict()}")

        return X

    def predict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Realiza predicción de DIAS_MADURACION siguiendo el pipeline exacto:

        PIPELINE:
        1. Entrada de datos (8 campos)
        2. Ingeniería de características (9 features temporales + cíclicas)
        3. Codificación categórica (5 features con LabelEncoder)
        4. Alineación según feature_order.json (17 features)
        5. Predicción con XGBoost
        6. Post-procesamiento y salida

        Args:
            data: Diccionario con 8 campos de entrada:
                - fechapol: Fecha de polinización (str 'YYYY-MM-DD' o datetime)
                - genero: Género de la planta (str)
                - especie: Especie de la planta (str)
                - ubicacion: Ubicación de la planta (str)
                - responsable: Responsable del registro (str)
                - Tipo: Tipo de polinización (str)
                - cantidad: Cantidad de cápsulas (int)
                - disponible: Disponibilidad 0 o 1 (int)

        Returns:
            Diccionario con resultados:
                - dias_estimados: int (días hasta maduración, mínimo 1)
                - fecha_polinizacion: str (YYYY-MM-DD)
                - fecha_estimada_maduracion: str (YYYY-MM-DD)
                - confianza: float (0-100)
                - nivel_confianza: str ('alta', 'media', 'baja')
                - metodo: str ('XGBoost')
                - modelo: str ('polinizacion.joblib')
                - input_data: dict (datos de entrada)
                - features_count: int (17)
                - timestamp: str (ISO format)
        """
        if not self.is_loaded():
            raise ModelNotLoadedError("Modelo no está cargado. Llame a initialize() primero.")

        try:
            logger.info("=" * 80)
            logger.info("[PREDICCION] INICIANDO PIPELINE DE PREDICCION DE POLINIZACION")
            logger.info("=" * 80)
            logger.info(f"[INPUT] Datos recibidos: {data}")

            # =========================================================================
            # PASO 1: VALIDACIÓN Y PREPARACIÓN DE ENTRADA (8 campos)
            # =========================================================================
            logger.info("[PASO 1] Validando entrada (8 campos requeridos)...")
            self._validate_input(data)
            logger.info("[OK] Validacion exitosa")

            # =========================================================================
            # PASO 2: INGENIERÍA DE CARACTERÍSTICAS TEMPORALES (9 features)
            # =========================================================================
            logger.info("[PASO 2] Creando 9 features temporales y ciclicas...")

            # Convertir fecha
            fecha_pol = data['fechapol']
            if isinstance(fecha_pol, str):
                fecha_pol = datetime.strptime(fecha_pol, '%Y-%m-%d')

            logger.info(f"   Fecha de polinizacion: {fecha_pol.strftime('%Y-%m-%d')}")

            # Crear features temporales
            temporal_features = self._extract_temporal_features(fecha_pol)
            logger.info(f"   [OK] Features temporales creadas:")
            logger.info(f"      - Basicas: mes={temporal_features['mes_pol']}, dia_anio={temporal_features['dia_año_pol']}, "
                       f"trimestre={temporal_features['trimestre_pol']}, anio={temporal_features['año_pol']}, "
                       f"semana={temporal_features['semana_año']}")
            logger.info(f"      - Ciclicas: mes_sin={temporal_features['mes_sin']:.4f}, mes_cos={temporal_features['mes_cos']:.4f}, "
                       f"dia_anio_sin={temporal_features['dia_año_sin']:.4f}, dia_anio_cos={temporal_features['dia_año_cos']:.4f}")

            # =========================================================================
            # PASO 3: CODIFICACIÓN CATEGÓRICA (5 features)
            # =========================================================================
            logger.info("[PASO 3] Codificando 5 variables categoricas...")

            categorical_encoded = {}
            categorias_nuevas = 0

            for col in self.categorical_columns:
                value = str(data[col]) if data[col] is not None else ''
                encoded_col_name = f"{col}_encoded"

                # Codificar con manejo de categorías nuevas
                encoder = self.label_encoders[col]
                try:
                    encoded_value = encoder.transform([value])[0]
                    categorical_encoded[encoded_col_name] = int(encoded_value)
                    logger.info(f"   [OK] {col}='{value}' -> {encoded_value}")
                except (ValueError, KeyError):
                    # Categoría nueva: usar len(encoder.classes_) como fallback
                    fallback_value = len(encoder.classes_)
                    categorical_encoded[encoded_col_name] = fallback_value
                    categorias_nuevas += 1
                    logger.warning(f"   [WARN] {col}='{value}' NO VISTA -> fallback={fallback_value}")

            logger.info(f"   Categorias nuevas detectadas: {categorias_nuevas}")

            # =========================================================================
            # PASO 4: ENSAMBLAJE Y ALINEACIÓN (16 features)
            # =========================================================================
            logger.info("[PASO 4] Ensamblando y alineando 16 features...")

            # Combinar todas las features
            features = {}
            features.update(temporal_features)  # 9 features
            features.update(categorical_encoded)  # 5 features
            features['cantidad'] = int(data.get('cantidad', 0))  # 1 feature
            features['disponible'] = int(data.get('disponible', 0))  # 1 feature

            # Crear DataFrame con features en el orden EXACTO de feature_list
            feature_dict = {feature: [features[feature]] for feature in self.feature_list}
            X_aligned = pd.DataFrame(feature_dict)

            logger.info(f"   [OK] DataFrame creado con {len(X_aligned.columns)} features")
            logger.info(f"   [INFO] Orden de features: {self.feature_list}")
            logger.info(f"   [INFO] Valores: {X_aligned.iloc[0].to_dict()}")

            # =========================================================================
            # PASO 5: PREDICCIÓN CON XGBOOST
            # =========================================================================
            logger.info("[PASO 5] Realizando prediccion con XGBoost...")

            # Hacer predicción
            prediccion_raw = self.model.predict(X_aligned)[0]
            logger.info(f"   [INFO] Prediccion raw del modelo: {prediccion_raw:.2f} dias")

            # Post-procesamiento: max(1, int(np.round(predicción)))
            dias_estimados = max(1, int(np.round(prediccion_raw)))
            logger.info(f"   [OK] Dias estimados (post-procesado): {dias_estimados} dias")

            # =========================================================================
            # PASO 6: CÁLCULO DE RESULTADOS FINALES
            # =========================================================================
            logger.info("[PASO 6] Calculando fecha estimada y confianza...")

            # Calcular fecha estimada de maduración
            fecha_estimada = fecha_pol + timedelta(days=dias_estimados)
            logger.info(f"   [INFO] Fecha estimada de maduracion: {fecha_estimada.strftime('%Y-%m-%d')}")

            # Calcular confianza basada en categorías conocidas
            confianza_base = 85.0  # Confianza base del modelo XGBoost
            penalizacion_categorias_nuevas = categorias_nuevas * 5  # -5% por cada categoría nueva
            confianza = max(40.0, min(95.0, confianza_base - penalizacion_categorias_nuevas))

            logger.info(f"   [INFO] Confianza calculada: {confianza:.1f}% "
                       f"(base: {confianza_base}%, penalizacion: -{penalizacion_categorias_nuevas}%)")

            nivel_confianza = self._get_confidence_level(confianza)

            # =========================================================================
            # RESULTADO FINAL
            # =========================================================================
            resultado = {
                'dias_estimados': dias_estimados,
                'fecha_polinizacion': fecha_pol.strftime('%Y-%m-%d'),
                'fecha_estimada_maduracion': fecha_estimada.strftime('%Y-%m-%d'),
                'confianza': round(confianza, 1),
                'nivel_confianza': nivel_confianza,
                'metodo': 'XGBoost',
                'modelo': 'polinizacion.joblib',
                'input_data': {
                    'genero': data['genero'],
                    'especie': data['especie'],
                    'ubicacion': data['ubicacion'],
                    'responsable': data['responsable'],
                    'tipo': data['Tipo'],
                    'cantidad': data['cantidad'],
                    'disponible': data['disponible']
                },
                'features_count': len(self.feature_list),
                'categorias_nuevas': categorias_nuevas,
                'timestamp': datetime.now().isoformat()
            }

            logger.info("=" * 80)
            logger.info("[OK] PREDICCION COMPLETADA EXITOSAMENTE")
            logger.info("=" * 80)
            logger.info(f"[RESULTADO]:")
            logger.info(f"   Dias estimados: {dias_estimados} dias")
            logger.info(f"   Fecha polinizacion: {fecha_pol.strftime('%Y-%m-%d')}")
            logger.info(f"   Fecha estimada maduracion: {fecha_estimada.strftime('%Y-%m-%d')}")
            logger.info(f"   Confianza: {confianza:.1f}% ({nivel_confianza})")
            logger.info(f"   Metodo: XGBoost")
            logger.info(f"   Categorias nuevas: {categorias_nuevas}/5")
            logger.info("=" * 80)

            return resultado

        except InvalidInputError:
            raise
        except Exception as e:
            logger.error(f"[ERROR] Error en prediccion: {e}")
            raise PollinationPredictorError(f"Error realizando predicción: {e}")

    def _get_confidence_level(self, confianza: float) -> str:
        """Convierte confianza numérica a nivel textual"""
        if confianza >= 85:
            return 'alta'
        elif confianza >= 70:
            return 'media'
        else:
            return 'baja'

    def predict_batch(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Realiza predicciones en lote para múltiples registros

        Args:
            data_list: Lista de diccionarios con datos de entrada

        Returns:
            Lista de resultados de predicción
        """
        if not self.is_loaded():
            raise ModelNotLoadedError("Modelo no está cargado")

        logger.info(f"Realizando predicción en lote para {len(data_list)} registros")

        results = []
        for i, data in enumerate(data_list):
            try:
                result = self.predict(data)
                results.append(result)
            except Exception as e:
                logger.error(f"Error en registro {i+1}: {e}")
                results.append({
                    'error': str(e),
                    'registro': i+1
                })

        return results

    def get_model_info(self) -> Dict[str, Any]:
        """
        Retorna información sobre el modelo cargado

        Returns:
            Diccionario con información del modelo
        """
        if not self.is_loaded():
            return {
                'loaded': False,
                'error': 'Modelo no cargado'
            }

        return {
            'loaded': True,
            'model_type': type(self.model).__name__,
            'n_features': len(self.feature_list),
            'features': self.feature_list,
            'categorical_columns': self.categorical_columns,
            'encoders': list(self.label_encoders.keys()),
            'preprocessing': self.feature_info.get('preprocessing', {}),
            'input_required': self.feature_info['input_columns_required']
        }


# Instancia global del predictor (Singleton)
pollination_predictor = PollinationPredictor()
