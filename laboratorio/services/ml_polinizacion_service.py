"""
Servicio de Machine Learning para predicción de maduración de polinizaciones
Delega al predictor XGBoost (polinizacion.joblib + label_encoders.pkl)
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MLPolinizacionService:
    """Servicio para hacer predicciones de maduración usando el modelo XGBoost"""

    def __init__(self):
        self._predictor = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Inicializa el predictor XGBoost"""
        try:
            from ..ml.predictors import get_predictor
            self._predictor = get_predictor()
            self.model_loaded = self._predictor.model_loaded
            if self.model_loaded:
                logger.info("MLPolinizacionService: modelo XGBoost listo")
            else:
                logger.warning("MLPolinizacionService: modelo XGBoost no pudo cargarse")
        except Exception as e:
            logger.error(f"Error inicializando MLPolinizacionService: {e}")
            self.model_loaded = False

    def predecir_dias_maduracion(self, genero, especie, tipo, fecha_pol, cantidad=1):
        """
        Predice los días de maduración usando el modelo XGBoost

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
            # Convertir fecha a string si es objeto date
            if hasattr(fecha_pol, 'strftime'):
                fechapol_str = fecha_pol.strftime('%Y-%m-%d')
            else:
                fechapol_str = str(fecha_pol)

            result = self._predictor.predecir(
                fechapol=fechapol_str,
                genero=genero,
                especie=especie,
                ubicacion='',
                responsable='',
                tipo=tipo,
                cantidad=int(cantidad) if cantidad else 1,
                disponible=1
            )

            # Adaptar formato de salida al esperado por los callers
            return {
                'dias_estimados': result['dias_estimados'],
                'fecha_estimada': result['fecha_estimada_maduracion'],
                'metodo': result['metodo'],
                'modelo': result['modelo'],
                'confianza': result['confianza'],
                'nivel_confianza': result['nivel_confianza'],
            }

        except Exception as e:
            logger.error(f"Error en predicción ML de polinización: {e}")
            return None

    def get_model_info(self):
        """Retorna información sobre el modelo cargado"""
        if not self.model_loaded or not self._predictor:
            return {
                'loaded': False,
                'error': 'Modelo no cargado'
            }

        return {
            'loaded': True,
            'modelo': 'XGBoost (polinizacion.joblib)',
            'mae_test': 10.22,
            'rmse_test': 19.43,
            'r2_test': 0.9563,
            'precision_percent': 95.63,
            'n_features': len(self._predictor.feature_list) if self._predictor.feature_list else 16,
            'n_samples': 0,
            'fecha_entrenamiento': 'N/A'
        }


# Instancia global del servicio
ml_polinizacion_service = MLPolinizacionService()
