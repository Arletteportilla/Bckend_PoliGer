"""
Servicio de Machine Learning para predicción de germinación
Utiliza el modelo entrenado para predecir días de germinación
"""

import joblib
import os
import json
from datetime import datetime, timedelta
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class MLPrediccionService:
    """Servicio para hacer predicciones usando el modelo de ML"""

    def __init__(self):
        self.model = None
        self.encoders = None
        self.metadata = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Carga el modelo y los encoders desde disco"""
        try:
            # Ruta al modelo en laboratorio/modelos/
            base_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                'modelos'
            )

            # Intentar cargar el modelo principal germinacion.pkl
            model_path = os.path.join(base_path, 'germinacion.pkl')

            if os.path.exists(model_path):
                logger.info(f"Cargando modelo desde: {model_path}")
                model_package = joblib.load(model_path)

                # Verificar si es un modelo empaquetado (con metadata)
                if isinstance(model_package, dict) and 'model' in model_package:
                    self.model = model_package['model']
                    self.encoders = model_package.get('label_encoders', {})
                    self.feature_columns = model_package.get('feature_columns', [])
                    self.species_stats = model_package.get('species_stats', pd.DataFrame())
                    self.climate_stats = model_package.get('climate_stats', pd.DataFrame())
                    self.month_stats = model_package.get('month_stats', pd.DataFrame())
                    self.genus_stats = model_package.get('genus_stats', pd.DataFrame())
                    self.metadata = model_package.get('metadata', {})
                    self.is_improved_model = True
                    self.model_loaded = True

                    logger.info(f"Modelo cargado exitosamente: {self.metadata.get('model_name', 'N/A')}")
                    logger.info(f"MAE: {self.metadata.get('test_mae', 'N/A')} dias, R2: {self.metadata.get('test_r2', 'N/A')}")
                else:
                    # Modelo simple sin empaquetado
                    self.model = model_package
                    self.encoders = {}
                    self.is_improved_model = False
                    self.model_loaded = True
                    logger.info("Modelo simple cargado (sin metadata)")
                
                return

            # FALLBACK: Buscar en ml_models/germinacion/ (ubicación antigua)
            old_base_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                '..',
                'ml_models',
                'germinacion'
            )

            # Intentar cargar modelo mejorado
            improved_model_path = os.path.join(old_base_path, 'germination_model_improved.pkl')

            if os.path.exists(improved_model_path):
                logger.info("Cargando modelo MEJORADO desde ubicación antigua...")
                model_package = joblib.load(improved_model_path)

                self.model = model_package['model']
                self.encoders = model_package['label_encoders']
                self.feature_columns = model_package['feature_columns']
                self.species_stats = model_package['species_stats']
                self.climate_stats = model_package['climate_stats']
                self.month_stats = model_package['month_stats']
                self.genus_stats = model_package['genus_stats']
                self.metadata = model_package['metadata']
                self.is_improved_model = True
                self.model_loaded = True

                logger.info(f"Modelo MEJORADO cargado exitosamente: {self.metadata['model_name']}")
                logger.info(f"MAE: {self.metadata['test_mae']:.2f} dias, R2: {self.metadata['test_r2']:.4f}")
                return

            # Modelo antiguo
            old_model_path = os.path.join(old_base_path, 'germinacion_model.pkl')
            old_encoders_path = os.path.join(old_base_path, 'encoders.pkl')
            old_metadata_path = os.path.join(old_base_path, 'model_metadata.json')

            if os.path.exists(old_model_path):
                self.model = joblib.load(old_model_path)
                self.encoders = joblib.load(old_encoders_path) if os.path.exists(old_encoders_path) else {}
                self.is_improved_model = False

                if os.path.exists(old_metadata_path):
                    with open(old_metadata_path, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)

                self.model_loaded = True
                logger.info(f"Modelo ANTIGUO cargado desde {old_model_path}")

                if self.metadata:
                    logger.info(f"Modelo: {self.metadata.get('modelo', 'N/A')}")
                    logger.info(f"MAE: {self.metadata.get('metricas', {}).get('mae_test', 'N/A')} dias")
                return

            logger.warning(f"No se encontró ningún modelo de ML en: {model_path} ni en {old_model_path}")

        except Exception as e:
            logger.error(f"Error cargando modelo de ML: {e}")
            self.model_loaded = False
            self.is_improved_model = False

    def predecir_dias_germinacion(self, especie, genero, clima, fecha_siembra):
        """
        Predice los días de germinación usando el modelo de ML

        Args:
            especie: Nombre completo de la especie
            genero: Género de la planta
            clima: Clima (IC, IW, Warm, Cool, Intermedio)
            fecha_siembra: Fecha de siembra (datetime.date o str 'YYYY-MM-DD')

        Returns:
            dict con la predicción o None si no se pudo predecir
        """
        if not self.model_loaded:
            logger.warning("Modelo de ML no está cargado. Usando predicción heurística.")
            return None

        try:
            # Convertir fecha si es string
            if isinstance(fecha_siembra, str):
                fecha_siembra = datetime.strptime(fecha_siembra, '%Y-%m-%d').date()

            logger.info(f"ML Predicción - Fecha siembra: {fecha_siembra}, tipo: {type(fecha_siembra)}")

            # Usar modelo mejorado si está disponible
            if hasattr(self, 'is_improved_model') and self.is_improved_model:
                return self._predecir_con_modelo_mejorado(especie, genero, clima, fecha_siembra)
            else:
                return self._predecir_con_modelo_antiguo(especie, genero, clima, fecha_siembra)

        except Exception as e:
            logger.error(f"Error en predicción ML: {e}")
            return None

    def _predecir_con_modelo_antiguo(self, especie, genero, clima, fecha_siembra):
        """Predicción usando modelo antiguo (simple)"""
        mes_siembra = fecha_siembra.month

        # Determinar estación
        if mes_siembra in [12, 1, 2]:
            estacion = 'verano'
        elif mes_siembra in [3, 4, 5]:
            estacion = 'otoño'
        elif mes_siembra in [6, 7, 8]:
            estacion = 'invierno'
        else:
            estacion = 'primavera'

        # Codificar características
        especie_encoded = self._encode_safe('ESPECIE', especie)
        clima_encoded = self._encode_safe('CLIMA', clima)
        genero_encoded = self._encode_safe('genero', genero)
        estacion_encoded = self._encode_safe('estacion', estacion)

        # Crear DataFrame
        X = pd.DataFrame({
            'ESPECIE_encoded': [especie_encoded],
            'CLIMA_encoded': [clima_encoded],
            'genero_encoded': [genero_encoded],
            'mes_siembra': [mes_siembra],
            'estacion_encoded': [estacion_encoded]
        })

        # Predicción
        dias_predichos = self.model.predict(X)[0]
        dias_predichos = max(10, int(round(dias_predichos)))

        fecha_estimada = fecha_siembra + timedelta(days=dias_predichos)
        confianza = self._calcular_confianza(especie, clima, genero)

        logger.info(f"Predicción ANTIGUA: {dias_predichos} días (confianza: {confianza:.1f}%)")

        return {
            'dias_estimados': dias_predichos,
            'fecha_estimada': fecha_estimada.strftime('%Y-%m-%d'),
            'metodo': 'ML',
            'modelo': self.metadata.get('modelo', 'N/A') if self.metadata else 'ML',
            'confianza': confianza,
            'nivel_confianza': self._get_nivel_confianza(confianza)
        }

    def _predecir_con_modelo_mejorado(self, especie, genero, clima, fecha_siembra):
        """Predicción usando modelo mejorado con feature engineering avanzado"""
        import numpy as np

        # Extraer features temporales
        mes_siembra = fecha_siembra.month
        dia_mes_siembra = fecha_siembra.day
        dia_anio_siembra = fecha_siembra.timetuple().tm_yday
        anio_siembra = fecha_siembra.year
        trimestre_siembra = (mes_siembra - 1) // 3 + 1
        semana_siembra = fecha_siembra.isocalendar()[1]
        dia_semana = fecha_siembra.weekday()

        # Features cíclicas
        mes_sin = np.sin(2 * np.pi * mes_siembra / 12)
        mes_cos = np.cos(2 * np.pi * mes_siembra / 12)
        dia_anio_sin = np.sin(2 * np.pi * dia_anio_siembra / 365)
        dia_anio_cos = np.cos(2 * np.pi * dia_anio_siembra / 365)
        semana_sin = np.sin(2 * np.pi * semana_siembra / 52)
        semana_cos = np.cos(2 * np.pi * semana_siembra / 52)

        # Obtener estadísticas de la especie
        species_row = self.species_stats[self.species_stats['especie'] == especie]
        if len(species_row) > 0:
            especie_media = float(species_row['especie_media'].iloc[0])
            especie_mediana = float(species_row['especie_mediana'].iloc[0])
            especie_std = float(species_row['especie_std'].iloc[0])
            especie_min = float(species_row['especie_min'].iloc[0])
            especie_max = float(species_row['especie_max'].iloc[0])
            especie_count = int(species_row['especie_count'].iloc[0])
            especie_q25 = float(species_row['especie_q25'].iloc[0])
            especie_q75 = float(species_row['especie_q75'].iloc[0])
            especie_iqr = especie_q75 - especie_q25
        else:
            # Valores default si la especie no está en stats
            especie_media = especie_mediana = 50.0
            especie_std = especie_min = especie_max = especie_iqr = 0.0
            especie_count = especie_q25 = especie_q75 = 0

        # Estadísticas de clima
        climate_row = self.climate_stats[self.climate_stats['clima'] == clima]
        if len(climate_row) > 0:
            clima_media = float(climate_row['clima_media'].iloc[0])
            clima_mediana = float(climate_row['clima_mediana'].iloc[0])
            clima_std = float(climate_row['clima_std'].iloc[0])
        else:
            clima_media = clima_mediana = 50.0
            clima_std = 0.0

        # Estadísticas de mes
        month_row = self.month_stats[self.month_stats['mes_siembra'] == mes_siembra]
        if len(month_row) > 0:
            mes_media = float(month_row['mes_media'].iloc[0])
            mes_std = float(month_row['mes_std'].iloc[0])
        else:
            mes_media = 50.0
            mes_std = 0.0

        # Estadísticas de género
        genus_row = self.genus_stats[self.genus_stats['genero'] == genero]
        if len(genus_row) > 0:
            genero_media = float(genus_row['genero_media'].iloc[0])
            genero_std = float(genus_row['genero_std'].iloc[0])
            genero_count = int(genus_row['genero_count'].iloc[0])
        else:
            genero_media = 50.0
            genero_std = 0.0
            genero_count = 0

        # Interacciones
        especie_clima = f"{especie}_{clima}"

        # Frecuencias (estimadas)
        especie_frecuencia = especie_count if especie_count > 0 else 1
        clima_frecuencia = 1000  # Valor estimado

        # Codificar categóricas
        especie_encoded = self._encode_safe_improved('especie', especie)
        clima_encoded = self._encode_safe_improved('clima', clima)
        genero_encoded = self._encode_safe_improved('genero', genero)
        especie_clima_encoded = self._encode_safe_improved('especie_clima', especie_clima)

        # Crear DataFrame con TODAS las features
        features_data = {
            'especie_encoded': [especie_encoded],
            'clima_encoded': [clima_encoded],
            'genero_encoded': [genero_encoded],
            'especie_clima_encoded': [especie_clima_encoded],
            'c.solic': [0],  # Default
            'mes_siembra': [mes_siembra],
            'dia_mes_siembra': [dia_mes_siembra],
            'dia_anio_siembra': [dia_anio_siembra],
            'anio_siembra': [anio_siembra],
            'trimestre_siembra': [trimestre_siembra],
            'semana_siembra': [semana_siembra],
            'dia_semana': [dia_semana],
            'mes_sin': [mes_sin],
            'mes_cos': [mes_cos],
            'dia_anio_sin': [dia_anio_sin],
            'dia_anio_cos': [dia_anio_cos],
            'semana_sin': [semana_sin],
            'semana_cos': [semana_cos],
            'especie_media': [especie_media],
            'especie_mediana': [especie_mediana],
            'especie_std': [especie_std],
            'especie_min': [especie_min],
            'especie_max': [especie_max],
            'especie_count': [especie_count],
            'especie_q25': [especie_q25],
            'especie_q75': [especie_q75],
            'especie_iqr': [especie_iqr],
            'clima_media': [clima_media],
            'clima_mediana': [clima_mediana],
            'clima_std': [clima_std],
            'mes_media': [mes_media],
            'mes_std': [mes_std],
            'genero_media': [genero_media],
            'genero_std': [genero_std],
            'genero_count': [genero_count],
            'especie_frecuencia': [especie_frecuencia],
            'clima_frecuencia': [clima_frecuencia]
        }

        # Agregar s.stock si está en las features
        if 's.stock' in self.feature_columns:
            features_data['s.stock'] = [0]

        X = pd.DataFrame(features_data)

        # Asegurar orden correcto de columnas
        X = X[self.feature_columns]

        # Hacer predicción
        dias_predichos = self.model.predict(X)[0]
        dias_predichos = max(10, int(round(dias_predichos)))

        fecha_estimada = fecha_siembra + timedelta(days=dias_predichos)

        # Calcular confianza mejorada
        confianza = self._calcular_confianza_mejorada(especie, clima, genero, especie_count)

        logger.info(f"Predicción MEJORADA: {dias_predichos} días (confianza: {confianza:.1f}%)")

        return {
            'dias_estimados': dias_predichos,
            'fecha_estimada': fecha_estimada.strftime('%Y-%m-%d'),
            'metodo': 'ML',
            'modelo': self.metadata['model_name'],
            'confianza': confianza,
            'nivel_confianza': self._get_nivel_confianza(confianza)
        }

    def _encode_safe(self, feature_name, value):
        """
        Codifica un valor usando el encoder correspondiente.
        Si el valor no existe en el encoder, retorna 0.
        """
        try:
            encoder = self.encoders[feature_name]
            return encoder.transform([value])[0]
        except:
            logger.debug(f"Valor '{value}' no encontrado en encoder '{feature_name}'. Usando default.")
            return 0

    def _calcular_confianza(self, especie, clima, genero):
        """
        Calcula el nivel de confianza de la predicción basado en:
        - Si la especie está en los datos de entrenamiento
        - Si el género está en los datos de entrenamiento
        - Si el clima es válido
        """
        confianza = 50.0  # Confianza base

        # Incrementar confianza si la especie fue vista en el entrenamiento
        if self._valor_en_encoder('ESPECIE', especie):
            confianza += 30.0

        # Incrementar confianza si el género fue visto
        if self._valor_en_encoder('genero', genero):
            confianza += 10.0

        # Incrementar confianza si el clima es válido
        if self._valor_en_encoder('CLIMA', clima):
            confianza += 10.0

        return min(confianza, 100.0)

    def _valor_en_encoder(self, feature_name, value):
        """Verifica si un valor existe en el encoder"""
        try:
            encoder = self.encoders[feature_name]
            encoder.transform([value])
            return True
        except:
            return False

    def _get_nivel_confianza(self, confianza):
        """Retorna el nivel de confianza como texto"""
        if confianza >= 80:
            return 'alta'
        elif confianza >= 60:
            return 'media'
        else:
            return 'baja'

    def _encode_safe_improved(self, feature_name, value):
        """
        Codifica un valor usando el encoder del modelo mejorado.
        Si el valor no existe en el encoder, retorna 0.
        """
        try:
            encoder = self.encoders[feature_name]
            return encoder.transform([value])[0]
        except:
            logger.debug(f"Valor '{value}' no encontrado en encoder '{feature_name}' (mejorado). Usando default.")
            return 0

    def _calcular_confianza_mejorada(self, especie, clima, genero, especie_count):
        """
        Calcula confianza mejorada basada en datos históricos y encoder
        """
        confianza = 60.0  # Base más alta para modelo mejorado

        # Si la especie tiene datos históricos significativos
        if especie_count > 10:
            confianza += 25.0
        elif especie_count > 5:
            confianza += 15.0
        elif especie_count > 0:
            confianza += 10.0

        # Si la especie está en el encoder
        if self._valor_en_encoder_improved('especie', especie):
            confianza += 10.0

        # Si el género está en el encoder
        if self._valor_en_encoder_improved('genero', genero):
            confianza += 5.0

        # Si el clima está en el encoder
        if self._valor_en_encoder_improved('clima', clima):
            confianza += 5.0

        return min(confianza, 99.0)

    def _valor_en_encoder_improved(self, feature_name, value):
        """Verifica si un valor existe en el encoder mejorado"""
        try:
            encoder = self.encoders[feature_name]
            encoder.transform([value])
            return True
        except:
            return False

    def get_model_info(self):
        """Retorna información sobre el modelo cargado"""
        if not self.model_loaded:
            return {
                'loaded': False,
                'error': 'Modelo no cargado'
            }

        if hasattr(self, 'is_improved_model') and self.is_improved_model:
            return {
                'loaded': True,
                'modelo': self.metadata.get('model_name', 'N/A'),
                'tipo': 'MEJORADO',
                'mae_test': round(self.metadata.get('test_mae', 0), 2),
                'rmse_test': round(self.metadata.get('test_rmse', 0), 2),
                'r2_test': round(self.metadata.get('test_r2', 0), 4),
                'n_features': self.metadata.get('n_features', 0)
            }
        else:
            return {
                'loaded': True,
                'tipo': 'ANTIGUO',
                'modelo': self.metadata.get('modelo', 'N/A') if self.metadata else 'N/A',
                'fecha_entrenamiento': self.metadata.get('fecha_entrenamiento', 'N/A') if self.metadata else 'N/A',
                'registros_entrenamiento': self.metadata.get('registros_entrenamiento', 'N/A') if self.metadata else 'N/A',
                'mae_test': self.metadata.get('metricas', {}).get('mae_test', 'N/A') if self.metadata else 'N/A',
                'r2_test': self.metadata.get('metricas', {}).get('r2_test', 'N/A') if self.metadata else 'N/A',
            }


# Instancia global del servicio
ml_prediccion_service = MLPrediccionService()
