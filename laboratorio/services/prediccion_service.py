"""
Servicio de negocio para Predicciones
"""
from typing import Dict, Any, Optional
from datetime import date, datetime, timedelta
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import logging
import json
import os
from django.conf import settings

logger = logging.getLogger(__name__)


class PrediccionService:
    """
    Servicio de negocio para manejar predicciones de germinación y polinización
    Usa modelo de ML cuando está disponible, caso contrario usa método heurístico
    """

    def __init__(self):
        self.default_dias_germinacion = 30
        self.default_confianza = 75.0
        self.especies_promedios = {}

        # Cargar promedios de especies desde JSON
        self._cargar_promedios_especies()

        # Intentar cargar servicio de ML
        try:
            from .ml_prediccion_service import ml_prediccion_service
            self.ml_service = ml_prediccion_service
            logger.info("Servicio de ML cargado exitosamente")
        except Exception as e:
            logger.warning(f"No se pudo cargar servicio de ML: {e}. Usando metodo heuristico")
            self.ml_service = None

    def _cargar_promedios_especies(self):
        """Carga los promedios de germinación por especie desde el archivo JSON"""
        try:
            json_path = os.path.join(settings.BASE_DIR, 'data', 'promedios_germinacion_especies.json')
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.especies_promedios = json.load(f)
                logger.info(f"Promedios de especies cargados: {len(self.especies_promedios)} especies")
            else:
                logger.warning(f"Archivo de promedios no encontrado: {json_path}")
        except Exception as e:
            logger.error(f"Error cargando promedios de especies: {e}")
            self.especies_promedios = {}

    def calcular_prediccion_germinacion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula predicción de germinación usando ML o método heurístico

        Prioridad:
        1. Modelo de Machine Learning (si está disponible)
        2. Método heurístico (fallback)
        """
        try:
            # Validar datos de entrada
            validated_data = self._validate_germinacion_data(data)

            # INTENTAR PREDICCIÓN CON ML PRIMERO
            ml_result = None
            if self.ml_service and self.ml_service.model_loaded:
                try:
                    ml_result = self.ml_service.predecir_dias_germinacion(
                        especie=validated_data.get('especie', ''),
                        genero=validated_data.get('genero', ''),
                        clima=validated_data.get('clima', 'I'),
                        fecha_siembra=validated_data.get('fecha_siembra')
                    )

                    if ml_result:
                        ml_confianza = ml_result.get('confianza', 0)

                        # Si ML tiene ALTA confianza (>=70%), usarlo directamente
                        if ml_confianza >= 70:
                            logger.info(f"Usando prediccion ML con alta confianza: {ml_confianza}%")
                            return {
                                'dias_estimados': ml_result['dias_estimados'],
                                'fecha_estimada': ml_result['fecha_estimada'],
                                'confianza': ml_result['confianza'],
                                'nivel_confianza': ml_result['nivel_confianza'],
                                'metodo': 'ML',
                                'modelo_utilizado': ml_result['modelo'],
                                'tipo': 'prediccion_mejorada',
                                'parametros': {
                                    'especie': validated_data.get('especie', ''),
                                    'genero': validated_data.get('genero', ''),
                                    'clima': validated_data.get('clima', ''),
                                    'fecha_siembra': validated_data.get('fecha_siembra')
                                }
                            }
                        else:
                            logger.info(f"ML tiene confianza baja ({ml_confianza}%), verificando datos historicos primero")
                except Exception as ml_error:
                    logger.warning(f"Error en prediccion ML: {ml_error}. Usando metodo heuristico")

            # FALLBACK: MÉTODO HEURÍSTICO (con datos históricos si están disponibles)
            logger.info("Usando metodo heuristico/historico")

            # Obtener parámetros de la especie (intenta datos históricos primero)
            parametros = self._obtener_parametros_especie_genero(
                validated_data.get('especie', ''),
                validated_data.get('genero', '')
            )

            # Verificar si encontramos datos históricos
            fuente_datos = parametros.get('fuente_datos', 'heuristico')

            # Si tenemos datos históricos, usarlos
            if fuente_datos in ['historico', 'historico_similar']:
                logger.info(f"Usando datos {fuente_datos} en lugar de ML de baja confianza")

                # Calcular con datos históricos
                dias_estimados = self._calcular_tiempo_germinacion(validated_data, parametros)

                # Calcular fecha estimada
                fecha_siembra = validated_data.get('fecha_siembra')
                if isinstance(fecha_siembra, str):
                    fecha_siembra = datetime.strptime(fecha_siembra, '%Y-%m-%d').date()

                fecha_estimada = fecha_siembra + timedelta(days=dias_estimados)

                # Calcular confianza basada en datos disponibles
                confianza = self._calcular_confianza(validated_data, parametros)

                return {
                    'dias_estimados': dias_estimados,
                    'fecha_estimada': fecha_estimada.isoformat(),
                    'confianza': confianza,
                    'tipo': 'prediccion_historica',
                    'fuente_datos': fuente_datos,
                    'num_registros_historicos': parametros.get('num_registros', 0),
                    'rango_dias': parametros.get('rango_dias', ''),
                    'parametros_usados': {
                        'especie': validated_data.get('especie', ''),
                        'genero': validated_data.get('genero', ''),
                        'clima': validated_data.get('clima', 'I'),
                        'fecha_siembra': fecha_siembra.isoformat()
                    }
                }

            # Si NO hay datos históricos pero SÍ tenemos ML con baja confianza, usar ML
            if ml_result:
                logger.info(f"No hay datos historicos, usando ML con confianza baja ({ml_result.get('confianza')}%)")
                return {
                    'dias_estimados': ml_result['dias_estimados'],
                    'fecha_estimada': ml_result['fecha_estimada'],
                    'confianza': ml_result['confianza'],
                    'nivel_confianza': ml_result['nivel_confianza'],
                    'metodo': 'ML',
                    'modelo_utilizado': ml_result['modelo'],
                    'tipo': 'prediccion_ml_baja_confianza',
                    'parametros': {
                        'especie': validated_data.get('especie', ''),
                        'genero': validated_data.get('genero', ''),
                        'clima': validated_data.get('clima', ''),
                        'fecha_siembra': validated_data.get('fecha_siembra')
                    }
                }

            # ÚLTIMO FALLBACK: Heurístico puro (no hay datos históricos ni ML)
            logger.info("Usando heuristico puro (sin datos historicos ni ML)")

            # Calcular con heurísticos
            dias_estimados = self._calcular_tiempo_germinacion(validated_data, parametros)

            # Calcular fecha estimada
            fecha_siembra = validated_data.get('fecha_siembra')
            if isinstance(fecha_siembra, str):
                fecha_siembra = datetime.strptime(fecha_siembra, '%Y-%m-%d').date()

            fecha_estimada = fecha_siembra + timedelta(days=dias_estimados)

            # Calcular confianza basada en datos disponibles
            confianza = self._calcular_confianza(validated_data, parametros)

            return {
                'dias_estimados': dias_estimados,
                'fecha_estimada': fecha_estimada.isoformat(),
                'confianza': confianza,
                'tipo': 'prediccion_heuristica',
                'fuente_datos': 'heuristico',
                'num_registros_historicos': 0,
                'rango_dias': '',
                'parametros_usados': {
                    'especie': validated_data.get('especie', ''),
                    'genero': validated_data.get('genero', ''),
                    'clima': validated_data.get('clima', 'I'),
                    'fecha_siembra': fecha_siembra.isoformat()
                }
            }
        
        except Exception as e:
            logger.error(f"Error calculando predicción de germinación: {e}")
            raise ValidationError(f"Error en predicción: {str(e)}")
    
    def calcular_prediccion_polinizacion(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula predicción de polinización basada en datos históricos
        """
        try:
            # Validar datos de entrada
            validated_data = self._validate_polinizacion_data(data)
            
            # Obtener parámetros de la especie
            parametros = self._obtener_parametros_especie_polinizacion(
                validated_data.get('especie', ''),
                validated_data.get('genero', '')
            )
            
            # Calcular tiempo hasta semillas
            dias_estimados = self._calcular_tiempo_polinizacion(validated_data, parametros)
            
            # Calcular fecha estimada
            fecha_polinizacion = validated_data.get('fecha_polinizacion')
            if isinstance(fecha_polinizacion, str):
                fecha_polinizacion = datetime.strptime(fecha_polinizacion, '%Y-%m-%d').date()
            
            fecha_estimada = fecha_polinizacion + timedelta(days=dias_estimados)
            
            # Calcular confianza
            confianza = self._calcular_confianza_polinizacion(validated_data, parametros)
            
            return {
                'dias_estimados': dias_estimados,
                'fecha_estimada_semillas': fecha_estimada.isoformat(),
                'confianza': confianza,
                'tipo_prediccion': 'inicial',
                'condiciones_climaticas': self._obtener_condiciones_climaticas(validated_data),
                'especie_info': f"{validated_data.get('genero', '')} {validated_data.get('especie', '')}".strip(),
                'parametros_usados': {
                    'especie': validated_data.get('especie', ''),
                    'genero': validated_data.get('genero', ''),
                    'clima': validated_data.get('clima', 'I'),
                    'ubicacion': validated_data.get('ubicacion', ''),
                    'tipo_polinizacion': validated_data.get('tipo_polinizacion', 'SELF')
                }
            }
        
        except Exception as e:
            logger.error(f"Error calculando predicción de polinización: {e}")
            raise ValidationError(f"Error en predicción: {str(e)}")
    
    def _validate_germinacion_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para predicción de germinación"""
        validated_data = data.copy()
        
        # Campos requeridos
        if not data.get('fecha_siembra'):
            raise ValidationError('La fecha de siembra es requerida')
        
        # Validar fecha
        fecha_siembra = data['fecha_siembra']
        if isinstance(fecha_siembra, str):
            try:
                fecha_siembra = datetime.strptime(fecha_siembra, '%Y-%m-%d').date()
                validated_data['fecha_siembra'] = fecha_siembra
            except ValueError:
                raise ValidationError('Formato de fecha inválido')
        
        # Valores por defecto
        validated_data.setdefault('clima', 'I')
        validated_data.setdefault('especie', '')
        validated_data.setdefault('genero', '')
        
        return validated_data
    
    def _validate_polinizacion_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Valida datos para predicción de polinización"""
        validated_data = data.copy()
        
        # Campos requeridos
        if not data.get('especie'):
            raise ValidationError('La especie es requerida')
        
        # Validar fecha si se proporciona
        if data.get('fecha_polinizacion'):
            fecha_pol = data['fecha_polinizacion']
            if isinstance(fecha_pol, str):
                try:
                    fecha_pol = datetime.strptime(fecha_pol, '%Y-%m-%d').date()
                    validated_data['fecha_polinizacion'] = fecha_pol
                except ValueError:
                    raise ValidationError('Formato de fecha inválido')
        else:
            validated_data['fecha_polinizacion'] = date.today()
        
        # Valores por defecto
        validated_data.setdefault('clima', 'I')
        validated_data.setdefault('genero', '')
        validated_data.setdefault('ubicacion', 'laboratorio')
        validated_data.setdefault('tipo_polinizacion', 'SELF')
        
        return validated_data
    
    def _obtener_parametros_especie_genero(self, especie: str, genero: str) -> Dict[str, Any]:
        """Obtiene parámetros históricos de la especie/género"""
        parametros_base = {
            'tiempo_base': self.default_dias_germinacion,
            'factor_clima': 1.0,
            'factor_sustrato': 1.0,
            'variabilidad': 5,  # días de variabilidad
            'fuente_datos': 'heuristico'
        }

        # PRIORIDAD 1: Buscar en datos históricos reales por especie exacta
        if especie and especie in self.especies_promedios:
            datos_especie = self.especies_promedios[especie]
            logger.info(f"Usando datos historicos reales para especie '{especie}': {datos_especie['promedio_dias']} dias (n={datos_especie['num_registros']})")
            parametros_base.update({
                'tiempo_base': int(datos_especie['mediana_dias']),  # Usar mediana es más robusto
                'factor_clima': 1.0,
                'factor_sustrato': 1.0,
                'variabilidad': max(int(datos_especie['desviacion_std']), 5),
                'fuente_datos': 'historico',
                'num_registros': datos_especie['num_registros'],
                'promedio_dias': datos_especie['promedio_dias'],
                'rango_dias': f"{datos_especie['min_dias']}-{datos_especie['max_dias']}"
            })
            return parametros_base

        # PRIORIDAD 2: Buscar especies similares (búsqueda parcial)
        if especie:
            especie_normalizada = especie.lower().strip()
            for especie_bd, datos in self.especies_promedios.items():
                especie_bd_norm = especie_bd.lower().strip()
                # Buscar coincidencia parcial (ej: "Lepanthes calodictyon" coincide con "calodictyon")
                if especie_normalizada in especie_bd_norm or especie_bd_norm in especie_normalizada:
                    logger.info(f"Usando datos de especie similar '{especie_bd}' para '{especie}': {datos['mediana_dias']} dias")
                    parametros_base.update({
                        'tiempo_base': int(datos['mediana_dias']),
                        'factor_clima': 1.0,
                        'factor_sustrato': 1.0,
                        'variabilidad': max(int(datos['desviacion_std']), 5),
                        'fuente_datos': 'historico_similar',
                        'num_registros': datos['num_registros'],
                        'promedio_dias': datos['promedio_dias']
                    })
                    return parametros_base

        # PRIORIDAD 3: Fallback a heurísticos por género/familia
        logger.info(f"No hay datos historicos para '{especie}', usando heuristico")
        if 'orchid' in especie.lower() or 'orquidea' in especie.lower():
            parametros_base.update({
                'tiempo_base': 45,
                'factor_clima': 1.2,
                'variabilidad': 10
            })
        elif 'cattleya' in genero.lower():
            parametros_base.update({
                'tiempo_base': 40,
                'factor_clima': 1.1,
                'variabilidad': 8
            })
        elif 'phragmipedium' in genero.lower() or 'phragmipedium' in especie.lower():
            parametros_base.update({
                'tiempo_base': 120,
                'factor_clima': 1.15,
                'variabilidad': 20
            })
        elif 'lepanthes' in genero.lower() or 'lepanthes' in especie.lower():
            parametros_base.update({
                'tiempo_base': 140,
                'factor_clima': 1.2,
                'variabilidad': 30
            })

        return parametros_base
    
    def _obtener_parametros_especie_polinizacion(self, especie: str, genero: str) -> Dict[str, Any]:
        """Obtiene parámetros históricos para polinización"""
        parametros_base = {
            'tiempo_base': 90,  # días hasta semillas maduras
            'factor_clima': 1.0,
            'factor_ubicacion': 1.0,
            'variabilidad': 15
        }
        
        # Ajustes específicos por especie
        if 'orchid' in especie.lower() or 'orquidea' in especie.lower():
            parametros_base.update({
                'tiempo_base': 120,
                'factor_clima': 1.3,
                'variabilidad': 20
            })
        elif 'cattleya' in genero.lower():
            parametros_base.update({
                'tiempo_base': 100,
                'factor_clima': 1.2,
                'variabilidad': 18
            })
        
        return parametros_base
    
    def _calcular_tiempo_germinacion(self, data: Dict[str, Any], parametros: Dict[str, Any]) -> int:
        """Calcula el tiempo estimado de germinación"""
        tiempo_base = parametros['tiempo_base']
        
        # Ajustar por clima
        factor_clima = self._obtener_factor_clima(data.get('clima', 'I'))
        tiempo_ajustado = tiempo_base * factor_clima * parametros['factor_clima']
        
        # Ajustar por otros factores
        tiempo_ajustado *= parametros['factor_sustrato']
        
        return max(int(tiempo_ajustado), 7)  # Mínimo 7 días
    
    def _calcular_tiempo_polinizacion(self, data: Dict[str, Any], parametros: Dict[str, Any]) -> int:
        """Calcula el tiempo estimado hasta semillas maduras"""
        tiempo_base = parametros['tiempo_base']
        
        # Ajustar por clima
        factor_clima = self._obtener_factor_clima(data.get('clima', 'I'))
        tiempo_ajustado = tiempo_base * factor_clima * parametros['factor_clima']
        
        # Ajustar por ubicación
        factor_ubicacion = self._obtener_factor_ubicacion(data.get('ubicacion', ''))
        tiempo_ajustado *= factor_ubicacion * parametros['factor_ubicacion']
        
        # Ajustar por tipo de polinización
        factor_tipo = self._obtener_factor_tipo_polinizacion(data.get('tipo_polinizacion', 'SELF'))
        tiempo_ajustado *= factor_tipo
        
        return max(int(tiempo_ajustado), 30)  # Mínimo 30 días
    
    def _obtener_factor_clima(self, clima: str) -> float:
        """Obtiene factor de ajuste por clima"""
        factores = {
            'C': 0.8,   # Caliente - más rápido
            'W': 1.2,   # Frío - más lento
            'I': 1.0,   # Intermedio - normal
            'IW': 1.1,  # Intermedio caliente
            'IC': 0.9   # Intermedio frío
        }
        return factores.get(clima, 1.0)
    
    def _obtener_factor_ubicacion(self, ubicacion: str) -> float:
        """Obtiene factor de ajuste por ubicación"""
        if 'laboratorio' in ubicacion.lower():
            return 0.9  # Condiciones controladas
        elif 'vivero' in ubicacion.lower():
            return 1.0  # Condiciones normales
        elif 'finca' in ubicacion.lower():
            return 1.1  # Condiciones variables
        else:
            return 1.0
    
    def _obtener_factor_tipo_polinizacion(self, tipo: str) -> float:
        """Obtiene factor de ajuste por tipo de polinización"""
        factores = {
            'SELF': 1.0,     # Auto-polinización
            'SIBLING': 1.05,  # Entre hermanos
            'HIBRIDA': 1.1    # Híbrida - puede ser más lenta
        }
        return factores.get(tipo, 1.0)
    
    def _calcular_confianza(self, data: Dict[str, Any], parametros: Dict[str, Any]) -> float:
        """Calcula la confianza de la predicción"""
        confianza_base = self.default_confianza

        # AUMENTAR confianza si usamos datos históricos reales
        fuente_datos = parametros.get('fuente_datos', 'heuristico')
        if fuente_datos == 'historico':
            num_registros = parametros.get('num_registros', 0)
            if num_registros >= 6:
                confianza_base = 85.0  # Alta confianza con 6+ registros
            elif num_registros >= 4:
                confianza_base = 80.0  # Buena confianza con 4-5 registros
            else:
                confianza_base = 75.0  # Confianza moderada con 3 registros
        elif fuente_datos == 'historico_similar':
            confianza_base = 70.0  # Confianza moderada con especies similares

        # Reducir confianza si faltan datos
        if not data.get('especie'):
            confianza_base -= 20
        if not data.get('genero'):
            confianza_base -= 10

        # Ajustar por variabilidad de la especie
        variabilidad = parametros.get('variabilidad', 5)
        factor_variabilidad = max(0.5, 1 - (variabilidad / 100))
        confianza_base *= factor_variabilidad

        return max(min(confianza_base, 95.0), 30.0)  # Entre 30% y 95%
    
    def _calcular_confianza_polinizacion(self, data: Dict[str, Any], parametros: Dict[str, Any]) -> float:
        """Calcula la confianza de la predicción de polinización"""
        confianza_base = self.default_confianza
        
        # Aumentar confianza si hay más datos
        if data.get('genero'):
            confianza_base += 5
        if data.get('ubicacion'):
            confianza_base += 3
        if data.get('tipo_polinizacion'):
            confianza_base += 2
        
        # Ajustar por variabilidad
        variabilidad = parametros.get('variabilidad', 15)
        factor_variabilidad = max(0.6, 1 - (variabilidad / 60))
        confianza_base *= factor_variabilidad
        
        return max(min(confianza_base, 90.0), 40.0)  # Entre 40% y 90%
    
    def _obtener_condiciones_climaticas(self, data: Dict[str, Any]) -> str:
        """Obtiene descripción de condiciones climáticas"""
        clima = data.get('clima', 'I')
        descripciones = {
            'C': 'Clima caliente - favorece desarrollo rápido',
            'W': 'Clima frío - desarrollo más lento pero estable',
            'I': 'Clima intermedio - condiciones óptimas',
            'IW': 'Clima intermedio-caliente - buen desarrollo',
            'IC': 'Clima intermedio-frío - desarrollo moderado'
        }
        return descripciones.get(clima, 'Condiciones climáticas estándar')


# Instancia global del servicio
prediccion_service = PrediccionService()