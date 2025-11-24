"""
Servicio de Machine Learning para predicción de maduración de polinizaciones
Utiliza el modelo XGBoost entrenado para predecir días de maduración
"""

import joblib
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class MLPolinizacionService:
    """Servicio para hacer predicciones de maduración usando el modelo de ML"""

    def __init__(self):
        self.model = None
        self.scaler = None
        self.encoders = None
        self.feature_columns = None
        self.species_stats = None
        self.genus_stats = None
        self.tipo_stats = None
        self.genero_tipo_stats = None
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

            model_path = os.path.join(base_path, 'polinizacion.pkl')

            if os.path.exists(model_path):
                logger.info(f"Cargando modelo de polinización desde: {model_path}")
                model_package = joblib.load(model_path)

                # Verificar si es un modelo empaquetado
                if isinstance(model_package, dict) and 'model' in model_package:
                    self.model = model_package['model']
                    self.scaler = model_package.get('scaler')
                    self.encoders = model_package.get('label_encoders', {})
                    self.feature_columns = model_package.get('feature_columns', [])
                    self.species_stats = model_package.get('species_stats', pd.DataFrame())
                    self.genus_stats = model_package.get('genus_stats', pd.DataFrame())
                    self.tipo_stats = model_package.get('tipo_stats', pd.DataFrame())
                    self.genero_tipo_stats = model_package.get('genero_tipo_stats', pd.DataFrame())
                    self.metadata = model_package.get('metadata', {})
                    self.model_loaded = True

                    logger.info(f"Modelo cargado exitosamente: {self.metadata.get('model_name', 'N/A')}")
                    logger.info(f"MAE: {self.metadata.get('test_mae', 'N/A')} dias, R²: {self.metadata.get('test_r2', 'N/A')}")
                else:
                    # Modelo simple sin empaquetado
                    self.model = model_package
                    self.model_loaded = True
                    logger.info("Modelo simple cargado (sin metadata)")
                
                return

            logger.warning(f"No se encontró modelo de polinización en: {model_path}")

        except Exception as e:
            logger.error(f"Error cargando modelo de polinización: {e}")
            self.model_loaded = False

    def predecir_dias_maduracion(self, genero, especie, tipo, fecha_pol, cantidad=1):
        """
        Predice los días de maduración usando el modelo de ML

        Args:
            genero: Género de la planta
            especie: Especie de la planta
            tipo: Tipo de polinización (SELF, SIBBLING, HYBRID)
            fecha_pol: Fecha de polinización (datetime.date o str 'YYYY-MM-DD')
            cantidad: Cantidad de polinizaciones (default=1)

        Returns:
            dict con la predicción o None si no se pudo predecir
        """
        if not self.model_loaded:
            logger.warning("Modelo de ML no está cargado.")
            return None

        try:
            # Convertir fecha si es string
            if isinstance(fecha_pol, str):
                fecha_pol = datetime.strptime(fecha_pol, '%Y-%m-%d').date()

            logger.info(f"ML Predicción Polinización - Fecha: {fecha_pol}, Género: {genero}, Especie: {especie}, Tipo: {tipo}")

            # Extraer features temporales
            mes_pol = fecha_pol.month
            dia_anio_pol = fecha_pol.timetuple().tm_yday
            semana_pol = fecha_pol.isocalendar()[1]

            # Features cíclicas
            mes_sin = np.sin(2 * np.pi * mes_pol / 12)
            mes_cos = np.cos(2 * np.pi * mes_pol / 12)
            dia_anio_sin = np.sin(2 * np.pi * dia_anio_pol / 365)
            dia_anio_cos = np.cos(2 * np.pi * dia_anio_pol / 365)
            semana_sin = np.sin(2 * np.pi * semana_pol / 52)
            semana_cos = np.cos(2 * np.pi * semana_pol / 52)

            # Obtener estadísticas de la especie
            species_row = self.species_stats[
                (self.species_stats['genero'] == genero) & 
                (self.species_stats['especie'] == especie)
            ]
            
            if len(species_row) > 0:
                especie_media = float(species_row['especie_media'].iloc[0])
                especie_mediana = float(species_row['especie_mediana'].iloc[0])
                especie_std = float(species_row['especie_std'].iloc[0])
                especie_min = float(species_row['especie_min'].iloc[0])
                especie_max = float(species_row['especie_max'].iloc[0])
                especie_count = int(species_row['especie_count'].iloc[0])
                # Features adicionales del modelo avanzado
                especie_q25 = float(species_row['especie_q25'].iloc[0]) if 'especie_q25' in species_row.columns else especie_media - especie_std
                especie_q75 = float(species_row['especie_q75'].iloc[0]) if 'especie_q75' in species_row.columns else especie_media + especie_std
            else:
                # Especie nueva, usar stats del género
                genus_row = self.genus_stats[self.genus_stats['genero'] == genero]
                if len(genus_row) > 0:
                    especie_media = float(genus_row['genero_media'].iloc[0])
                    especie_mediana = especie_media
                    especie_std = float(genus_row['genero_std'].iloc[0])
                    especie_min = especie_media - 50
                    especie_max = especie_media + 50
                    especie_count = 1
                    especie_q25 = especie_media - especie_std
                    especie_q75 = especie_media + especie_std
                else:
                    # Género nuevo también, usar global
                    especie_media = especie_mediana = 196
                    especie_std = 112
                    especie_min = 100
                    especie_max = 300
                    especie_count = 1
                    especie_q25 = 150
                    especie_q75 = 250

            # Estadísticas de género
            genus_row = self.genus_stats[self.genus_stats['genero'] == genero]
            if len(genus_row) > 0:
                genero_media = float(genus_row['genero_media'].iloc[0])
                genero_std = float(genus_row['genero_std'].iloc[0])
                genero_count = int(genus_row['genero_count'].iloc[0])
                # Features adicionales del modelo avanzado
                genero_mediana = float(genus_row['genero_mediana'].iloc[0]) if 'genero_mediana' in genus_row.columns else genero_media
                genero_min = float(genus_row['genero_min'].iloc[0]) if 'genero_min' in genus_row.columns else genero_media - 50
                genero_max = float(genus_row['genero_max'].iloc[0]) if 'genero_max' in genus_row.columns else genero_media + 50
            else:
                genero_media = 196
                genero_std = 112
                genero_count = 1
                genero_mediana = 196
                genero_min = 100
                genero_max = 300

            # Estadísticas de tipo
            tipo_row = self.tipo_stats[self.tipo_stats['Tipo'] == tipo]
            if len(tipo_row) > 0:
                tipo_media = float(tipo_row['tipo_media'].iloc[0])
                tipo_std = float(tipo_row['tipo_std'].iloc[0])
                # Features adicionales del modelo avanzado
                tipo_mediana = float(tipo_row.get('tipo_mediana', tipo_media).iloc[0]) if 'tipo_mediana' in tipo_row.columns else tipo_media
            else:
                tipo_media = 196
                tipo_std = 112
                tipo_mediana = 196
            
            # Estadísticas combinadas género + tipo (si existen en el modelo)
            genero_tipo_media = genero_media
            genero_tipo_std = genero_std
            if hasattr(self, 'genero_tipo_stats') and self.genero_tipo_stats is not None and len(self.genero_tipo_stats) > 0:
                try:
                    genero_tipo_row = self.genero_tipo_stats[
                        (self.genero_tipo_stats['genero'] == genero) & 
                        (self.genero_tipo_stats['Tipo'] == tipo)
                    ]
                    if len(genero_tipo_row) > 0:
                        genero_tipo_media = float(genero_tipo_row['genero_tipo_media'].iloc[0])
                        genero_tipo_std = float(genero_tipo_row['genero_tipo_std'].iloc[0])
                except:
                    pass

            # Codificar categóricas
            genero_encoded = self._encode_safe('genero', genero)
            especie_key = f"{genero}_{especie}"
            especie_encoded = self._encode_safe('especie', especie_key)
            tipo_encoded = self._encode_safe('tipo', tipo)
            genero_tipo_encoded = genero_encoded * 100 + tipo_encoded

            # Calcular features de interacción
            especie_tipo_ratio = especie_media / (tipo_media + 1)
            genero_especie_ratio = genero_media / (especie_media + 1)

            # Crear DataFrame con TODAS las features (32 total)
            features_data = {
                'genero_encoded': [genero_encoded],
                'especie_encoded': [especie_encoded],
                'tipo_encoded': [tipo_encoded],
                'genero_tipo_encoded': [genero_tipo_encoded],
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
                'genero_media': [genero_media],
                'genero_mediana': [genero_mediana],
                'genero_std': [genero_std],
                'genero_min': [genero_min],
                'genero_max': [genero_max],
                'genero_count': [genero_count],
                'tipo_media': [tipo_media],
                'tipo_mediana': [tipo_mediana],
                'tipo_std': [tipo_std],
                'genero_tipo_media': [genero_tipo_media],
                'genero_tipo_std': [genero_tipo_std],
                'especie_tipo_ratio': [especie_tipo_ratio],
                'genero_especie_ratio': [genero_especie_ratio],
                'cantidad': [cantidad]
            }

            X = pd.DataFrame(features_data)

            # Asegurar orden correcto de columnas
            X = X[self.feature_columns]

            # Escalar si hay scaler
            if self.scaler:
                X_scaled = self.scaler.transform(X)
                X = pd.DataFrame(X_scaled, columns=self.feature_columns)

            # Hacer predicción
            dias_predichos = self.model.predict(X)[0]
            dias_predichos = max(1, int(round(dias_predichos)))

            fecha_mad_estimada = fecha_pol + timedelta(days=dias_predichos)

            # Calcular confianza
            mae = self.metadata.get('test_mae', 10)
            confianza = self._calcular_confianza(genero, especie, tipo, especie_count)

            logger.info(f"Predicción: {dias_predichos} días (confianza: {confianza:.1f}%)")

            return {
                'dias_estimados': dias_predichos,
                'fecha_estimada': fecha_mad_estimada.strftime('%Y-%m-%d'),
                'metodo': 'ML',
                'modelo': self.metadata.get('model_name', 'ML'),
                'confianza': confianza,
                'nivel_confianza': self._get_nivel_confianza(confianza),
                'rango_probable': {
                    'min': max(1, dias_predichos - int(mae)),
                    'max': dias_predichos + int(mae)
                }
            }

        except Exception as e:
            logger.error(f"Error en predicción ML de polinización: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None

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

    def _calcular_confianza(self, genero, especie, tipo, especie_count):
        """
        Calcula el nivel de confianza de la predicción
        """
        confianza = 60.0  # Base

        # Si la especie tiene datos históricos significativos
        if especie_count > 10:
            confianza += 25.0
        elif especie_count > 5:
            confianza += 15.0
        elif especie_count > 0:
            confianza += 10.0

        # Si la especie está en el encoder
        especie_key = f"{genero}_{especie}"
        if self._valor_en_encoder('especie', especie_key):
            confianza += 10.0

        # Si el género está en el encoder
        if self._valor_en_encoder('genero', genero):
            confianza += 5.0

        # Si el tipo está en el encoder
        if self._valor_en_encoder('tipo', tipo):
            confianza += 5.0

        return min(confianza, 99.0)

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

    def get_model_info(self):
        """Retorna información sobre el modelo cargado"""
        if not self.model_loaded:
            return {
                'loaded': False,
                'error': 'Modelo no cargado'
            }

        return {
            'loaded': True,
            'modelo': self.metadata.get('model_name', 'N/A'),
            'mae_test': round(self.metadata.get('test_mae', 0), 2),
            'rmse_test': round(self.metadata.get('test_rmse', 0), 2),
            'r2_test': round(self.metadata.get('test_r2', 0), 4),
            'precision_percent': round(self.metadata.get('precision_percent', 0), 2),
            'n_features': self.metadata.get('n_features', 0),
            'n_samples': self.metadata.get('n_samples', 0),
            'fecha_entrenamiento': self.metadata.get('fecha_entrenamiento', 'N/A')
        }


# Instancia global del servicio
ml_polinizacion_service = MLPolinizacionService()
