"""
Tests unitarios para el sistema de predicciones de polinización
Cubre todas las funciones del archivo predicciones_polinizaciones.py
"""
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
from django.test import TestCase
from django.core.cache import cache
from django.contrib.auth.models import User
from django.test import Client
from django.urls import reverse
import joblib
import json

from laboratorio.predicciones_polinizaciones import (
    cargar_modelo_polinizacion,
    generar_cache_key_polinizacion,
    obtener_parametros_especie_polinizacion,
    prediccion_polinizacion_inicial,
    refinar_prediccion_polinizacion,
    validar_prediccion_polinizacion,
    ModeloPolinizacionError,
    ModeloNoEncontradoError,
    ModeloCorruptoError,
    DatosInsuficientesError
)


class CargarModeloPolinizacionTest(TestCase):
    """Tests para la función cargar_modelo_polinizacion"""
    
    def setUp(self):
        """Configuración inicial para cada test"""
        # Limpiar cache del modelo antes de cada test
        import laboratorio.predicciones_polinizaciones
        laboratorio.predicciones_polinizaciones._modelo_polinizacion_cache = None
        cache.clear()
    
    @patch('laboratorio.predicciones_polinizaciones.validar_modelo_disponible')
    @patch('laboratorio.predicciones_polinizaciones.joblib.load')
    @patch('laboratorio.predicciones_polinizaciones.os.path.join')
    @patch('laboratorio.predicciones_polinizaciones.os.path.abspath')
    def test_carga_modelo_exitosa(self, mock_abspath, mock_join, mock_joblib_load, mock_validar):
        """Test carga exitosa del modelo .bin"""
        # Configurar mocks
        mock_modelo = MagicMock()
        mock_joblib_load.return_value = mock_modelo
        mock_join.return_value = '/path/to/Polinizacion.bin'
        mock_abspath.return_value = '/path/to/Polinizacion.bin'
        mock_validar.return_value = None  # Sin errores de validación
        
        # Ejecutar función
        resultado = cargar_modelo_polinizacion()
        
        # Verificaciones
        self.assertEqual(resultado, mock_modelo)
        mock_validar.assert_called_once()
        mock_joblib_load.assert_called_once_with('/path/to/Polinizacion.bin')
    
    @patch('laboratorio.predicciones_polinizaciones.validar_modelo_disponible')
    def test_modelo_no_encontrado(self, mock_validar):
        """Test cuando el archivo .bin no existe"""
        from laboratorio.validaciones_prediccion import PrediccionValidationError
        
        # Configurar mock para simular archivo no encontrado
        mock_validar.side_effect = PrediccionValidationError(
            "Archivo no encontrado", 
            error_code="MODELO_NO_ENCONTRADO"
        )
        
        # Verificar que se lance la excepción correcta
        with self.assertRaises(ModeloNoEncontradoError) as context:
            cargar_modelo_polinizacion()
        
        self.assertIn("no fue encontrado", str(context.exception))
    
    @patch('laboratorio.predicciones_polinizaciones.validar_modelo_disponible')
    def test_modelo_corrupto(self, mock_validar):
        """Test cuando el archivo .bin está corrupto"""
        from laboratorio.validaciones_prediccion import PrediccionValidationError
        
        # Configurar mock para simular archivo corrupto
        mock_validar.side_effect = PrediccionValidationError(
            "Archivo corrupto", 
            error_code="MODELO_CORRUPTO"
        )
        
        # Verificar que se lance la excepción correcta
        with self.assertRaises(ModeloCorruptoError) as context:
            cargar_modelo_polinizacion()
        
        self.assertIn("corrupto", str(context.exception))
    
    @patch('laboratorio.predicciones_polinizaciones.validar_modelo_disponible')
    @patch('laboratorio.predicciones_polinizaciones.joblib.load')
    def test_error_carga_joblib(self, mock_joblib_load, mock_validar):
        """Test cuando joblib.load falla"""
        # Configurar mocks
        mock_validar.return_value = None  # Validación OK
        mock_joblib_load.side_effect = Exception("Error de joblib")
        
        # Verificar que se lance ModeloCorruptoError
        with self.assertRaises(ModeloCorruptoError) as context:
            cargar_modelo_polinizacion()
        
        self.assertIn("Error de joblib", str(context.exception))
    
    @patch('laboratorio.predicciones_polinizaciones.validar_modelo_disponible')
    @patch('laboratorio.predicciones_polinizaciones.joblib.load')
    def test_modelo_none(self, mock_joblib_load, mock_validar):
        """Test cuando joblib.load retorna None"""
        # Configurar mocks
        mock_validar.return_value = None
        mock_joblib_load.return_value = None
        
        # Verificar que se lance ModeloCorruptoError
        with self.assertRaises(ModeloCorruptoError) as context:
            cargar_modelo_polinizacion()
        
        self.assertIn("modelo cargado es None", str(context.exception))
    
    @patch('laboratorio.predicciones_polinizaciones.validar_modelo_disponible')
    @patch('laboratorio.predicciones_polinizaciones.joblib.load')
    def test_cache_modelo(self, mock_joblib_load, mock_validar):
        """Test que el modelo se guarde en cache"""
        # Configurar mocks
        mock_modelo = MagicMock()
        mock_joblib_load.return_value = mock_modelo
        mock_validar.return_value = None
        
        # Primera carga
        resultado1 = cargar_modelo_polinizacion()
        self.assertEqual(mock_joblib_load.call_count, 1)
        
        # Segunda carga (debería usar cache)
        resultado2 = cargar_modelo_polinizacion()
        self.assertEqual(mock_joblib_load.call_count, 1)  # No debería cargar de nuevo
        
        # Ambos resultados deberían ser el mismo objeto
        self.assertIs(resultado1, resultado2)


class GenerarCacheKeyPolinizacionTest(TestCase):
    """Tests para la función generar_cache_key_polinizacion"""
    
    def test_cache_key_basico(self):
        """Test generación básica de cache key"""
        key = generar_cache_key_polinizacion(
            especie='cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        self.assertIsInstance(key, str)
        self.assertTrue(key.startswith('prediccion_polinizacion_'))
        self.assertEqual(len(key), 52)  # 'prediccion_polinizacion_' + 32 chars MD5
    
    def test_cache_key_consistente(self):
        """Test que la misma entrada genere la misma clave"""
        key1 = generar_cache_key_polinizacion(
            especie='cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        key2 = generar_cache_key_polinizacion(
            especie='cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        self.assertEqual(key1, key2)
    
    def test_cache_key_diferente(self):
        """Test que diferentes entradas generen claves diferentes"""
        key1 = generar_cache_key_polinizacion(
            especie='cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        key2 = generar_cache_key_polinizacion(
            especie='phalaenopsis',
            clima='templado',
            ubicacion='invernadero'
        )
        
        self.assertNotEqual(key1, key2)
    
    def test_cache_key_con_kwargs(self):
        """Test cache key con parámetros adicionales"""
        key1 = generar_cache_key_polinizacion(
            especie='cattleya',
            clima='templado',
            ubicacion='invernadero',
            tipo_polinizacion='artificial'
        )
        
        key2 = generar_cache_key_polinizacion(
            especie='cattleya',
            clima='templado',
            ubicacion='invernadero',
            tipo_polinizacion='natural'
        )
        
        self.assertNotEqual(key1, key2)


class ObtenerParametrosEspeciePolinizacionTest(TestCase):
    """Tests para obtener_parametros_especie_polinizacion"""
    
    def test_parametros_cattleya(self):
        """Test parámetros específicos para Cattleya"""
        params = obtener_parametros_especie_polinizacion('Cattleya', None)
        
        self.assertEqual(params['dias_base'], 120)
        self.assertEqual(params['factor_clima'], 1.2)
        self.assertEqual(params['factor_temp'], 'calido')
    
    def test_parametros_phalaenopsis(self):
        """Test parámetros específicos para Phalaenopsis"""
        params = obtener_parametros_especie_polinizacion('Phalaenopsis', None)
        
        self.assertEqual(params['dias_base'], 90)
        self.assertEqual(params['factor_clima'], 1.1)
        self.assertEqual(params['factor_temp'], 'templado')
    
    def test_parametros_por_genero(self):
        """Test parámetros por género cuando no hay especie específica"""
        params = obtener_parametros_especie_polinizacion(None, 'Orchidaceae')
        
        self.assertEqual(params['dias_base'], 100)
        self.assertEqual(params['factor_clima'], 1.1)
        self.assertEqual(params['factor_temp'], 'templado')
    
    def test_parametros_por_defecto(self):
        """Test parámetros por defecto para especie desconocida"""
        params = obtener_parametros_especie_polinizacion('Desconocida', 'Desconocido')
        
        self.assertEqual(params['dias_base'], 60)
        self.assertEqual(params['factor_clima'], 1.0)
        self.assertEqual(params['factor_temp'], 'templado')
    
    def test_case_insensitive(self):
        """Test que la búsqueda sea case-insensitive"""
        params1 = obtener_parametros_especie_polinizacion('cattleya', None)
        params2 = obtener_parametros_especie_polinizacion('CATTLEYA', None)
        params3 = obtener_parametros_especie_polinizacion('Cattleya', None)
        
        self.assertEqual(params1, params2)
        self.assertEqual(params2, params3)


class PrediccionPolinizacionInicialTest(TestCase):
    """Tests para prediccion_polinizacion_inicial"""
    
    def setUp(self):
        """Configuración inicial"""
        cache.clear()
        import laboratorio.predicciones_polinizaciones
        laboratorio.predicciones_polinizaciones._modelo_polinizacion_cache = None
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_basicos')
    @patch('laboratorio.predicciones_polinizaciones.cargar_modelo_polinizacion')
    @patch('laboratorio.predicciones_polinizaciones.cache')
    def test_prediccion_inicial_exitosa(self, mock_cache, mock_cargar_modelo, mock_validar):
        """Test predicción inicial exitosa"""
        # Configurar mocks
        mock_validar.return_value = []  # Sin errores
        mock_modelo = MagicMock()
        mock_cargar_modelo.return_value = mock_modelo
        mock_cache.get.return_value = None  # No hay cache
        
        # Ejecutar función
        resultado = prediccion_polinizacion_inicial(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        # Verificaciones
        self.assertIn('dias_estimados', resultado)
        self.assertIn('confianza', resultado)
        self.assertIn('tipo_prediccion', resultado)
        self.assertEqual(resultado['tipo_prediccion'], 'inicial')
        self.assertGreater(resultado['confianza'], 0)
        self.assertIsNone(resultado['fecha_estimada_semillas'])  # Sin fecha de polinización
        
        # Verificar que se guardó en cache
        mock_cache.set.assert_called_once()
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_basicos')
    def test_datos_insuficientes(self, mock_validar):
        """Test cuando faltan datos requeridos"""
        # Configurar mock para retornar errores
        mock_validar.return_value = ['Especie es requerida']
        
        # Ejecutar función
        resultado = prediccion_polinizacion_inicial(
            especie=None,
            clima='templado',
            ubicacion='invernadero'
        )
        
        # Verificaciones
        self.assertIn('error', resultado)
        self.assertEqual(resultado['error_code'], 'DATOS_INSUFICIENTES')
        self.assertEqual(resultado['confianza'], 0)
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_basicos')
    @patch('laboratorio.predicciones_polinizaciones.cargar_modelo_polinizacion')
    def test_modelo_no_encontrado(self, mock_cargar_modelo, mock_validar):
        """Test cuando el modelo no se encuentra"""
        # Configurar mocks
        mock_validar.return_value = []
        mock_cargar_modelo.side_effect = ModeloNoEncontradoError("Modelo no encontrado")
        
        # Ejecutar función
        resultado = prediccion_polinizacion_inicial(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        # Verificaciones
        self.assertIn('error', resultado)
        self.assertEqual(resultado['error_code'], 'MODELO_NO_ENCONTRADO')
        self.assertEqual(resultado['confianza'], 0)
    
    @patch('laboratorio.predicciones_polinizaciones.cache')
    def test_uso_cache(self, mock_cache):
        """Test que se use el cache cuando está disponible"""
        # Configurar cache con resultado previo
        cached_result = {
            'dias_estimados': 120,
            'confianza': 40,
            'tipo_prediccion': 'inicial',
            'cached': True
        }
        mock_cache.get.return_value = cached_result
        
        # Ejecutar función
        resultado = prediccion_polinizacion_inicial(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        # Verificaciones
        self.assertEqual(resultado, cached_result)
        mock_cache.get.assert_called_once()


class RefinarPrediccionPolinizacionTest(TestCase):
    """Tests para refinar_prediccion_polinizacion"""
    
    def setUp(self):
        """Configuración inicial"""
        cache.clear()
        import laboratorio.predicciones_polinizaciones
        laboratorio.predicciones_polinizaciones._modelo_polinizacion_cache = None
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_completos')
    @patch('laboratorio.predicciones_polinizaciones.prediccion_polinizacion_inicial')
    @patch('laboratorio.predicciones_polinizaciones.cargar_modelo_polinizacion')
    def test_refinamiento_con_fecha_polinizacion(self, mock_cargar_modelo, mock_inicial, mock_validar):
        """Test refinamiento con fecha de polinización"""
        # Configurar mocks
        mock_validar.return_value = ([], {})  # Sin errores
        mock_inicial.return_value = {
            'dias_estimados': 120,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        mock_modelo = MagicMock()
        mock_cargar_modelo.return_value = mock_modelo
        
        # Ejecutar función
        resultado = refinar_prediccion_polinizacion(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero',
            fecha_polinizacion='2024-01-01'
        )
        
        # Verificaciones
        self.assertIn('dias_estimados', resultado)
        self.assertIn('fecha_estimada_semillas', resultado)
        self.assertIn('confianza', resultado)
        self.assertEqual(resultado['tipo_prediccion'], 'refinada')
        self.assertGreater(resultado['confianza'], 40)  # Debería aumentar
        self.assertIsNotNone(resultado['fecha_estimada_semillas'])
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_completos')
    @patch('laboratorio.predicciones_polinizaciones.prediccion_polinizacion_inicial')
    @patch('laboratorio.predicciones_polinizaciones.cargar_modelo_polinizacion')
    def test_refinamiento_con_condiciones_climaticas(self, mock_cargar_modelo, mock_inicial, mock_validar):
        """Test refinamiento con condiciones climáticas detalladas"""
        # Configurar mocks
        mock_validar.return_value = ([], {})
        mock_inicial.return_value = {
            'dias_estimados': 120,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        mock_modelo = MagicMock()
        mock_cargar_modelo.return_value = mock_modelo
        
        condiciones_climaticas = {
            'temperatura': {'promedio': 25},
            'humedad': 70,
            'precipitacion': 50
        }
        
        # Ejecutar función
        resultado = refinar_prediccion_polinizacion(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero',
            fecha_polinizacion='2024-01-01',
            condiciones_climaticas=condiciones_climaticas
        )
        
        # Verificaciones
        self.assertIn('comparacion_con_inicial', resultado)
        self.assertGreater(resultado['confianza'], 40)  # Debería aumentar con más datos
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_completos')
    @patch('laboratorio.predicciones_polinizaciones.prediccion_polinizacion_inicial')
    @patch('laboratorio.predicciones_polinizaciones.cargar_modelo_polinizacion')
    def test_refinamiento_con_tipo_polinizacion(self, mock_cargar_modelo, mock_inicial, mock_validar):
        """Test refinamiento con tipo de polinización"""
        # Configurar mocks
        mock_validar.return_value = ([], {})
        mock_inicial.return_value = {
            'dias_estimados': 120,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        mock_modelo = MagicMock()
        mock_cargar_modelo.return_value = mock_modelo
        
        # Ejecutar función con polinización artificial
        resultado = refinar_prediccion_polinizacion(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero',
            fecha_polinizacion='2024-01-01',
            tipo_polinizacion='artificial'
        )
        
        # Verificaciones
        self.assertIn('especie_info', resultado)
        self.assertIn('refinamientos_aplicados', resultado['especie_info'])
        self.assertTrue(resultado['especie_info']['refinamientos_aplicados']['tipo_polinizacion'])
    
    def test_fecha_polinizacion_invalida(self):
        """Test con fecha de polinización en formato inválido"""
        resultado = refinar_prediccion_polinizacion(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero',
            fecha_polinizacion='fecha-invalida'
        )
        
        # Debería retornar error de fecha inválida
        self.assertIn('error', resultado)
        self.assertEqual(resultado['error_code'], 'FECHA_INVALIDA')


class ValidarPrediccionPolinizacionTest(TestCase):
    """Tests para validar_prediccion_polinizacion"""
    
    def test_validacion_exitosa(self):
        """Test validación exitosa de predicción"""
        # Predicción original simulada
        prediccion_original = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': '2024-05-01',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        fecha_maduracion_real = '2024-05-05'  # 4 días de diferencia
        
        # Ejecutar función
        resultado = validar_prediccion_polinizacion(
            prediccion_original,
            fecha_maduracion_real
        )
        
        # Verificaciones
        self.assertIn('precision', resultado)
        self.assertIn('dias_reales', resultado)
        self.assertIn('diferencia_dias', resultado)
        self.assertIn('calidad_prediccion', resultado)
        self.assertGreater(resultado['precision'], 0)
        self.assertEqual(resultado['diferencia_dias'], 4)
    
    def test_validacion_prediccion_exacta(self):
        """Test validación cuando la predicción es exacta"""
        prediccion_original = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': '2024-05-01',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        fecha_maduracion_real = '2024-05-01'  # Exacta
        
        resultado = validar_prediccion_polinizacion(
            prediccion_original,
            fecha_maduracion_real
        )
        
        # Verificaciones
        self.assertEqual(resultado['diferencia_dias'], 0)
        self.assertEqual(resultado['precision'], 100.0)
        self.assertIn('exacta', resultado['analisis']['tendencia'])
    
    def test_validacion_sin_prediccion_original(self):
        """Test validación sin predicción original"""
        with self.assertRaises(ValueError) as context:
            validar_prediccion_polinizacion(None, '2024-05-01')
        
        self.assertIn('predicción original', str(context.exception))
    
    def test_validacion_sin_fecha_real(self):
        """Test validación sin fecha de maduración real"""
        prediccion_original = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': '2024-05-01',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        with self.assertRaises(ValueError) as context:
            validar_prediccion_polinizacion(prediccion_original, None)
        
        self.assertIn('fecha de maduración real', str(context.exception))
    
    def test_validacion_prediccion_con_error(self):
        """Test validación de predicción que tuvo errores"""
        prediccion_con_error = {
            'error': 'Modelo no encontrado',
            'error_code': 'MODELO_NO_ENCONTRADO'
        }
        
        with self.assertRaises(ValueError) as context:
            validar_prediccion_polinizacion(prediccion_con_error, '2024-05-01')
        
        self.assertIn('predicción que tuvo errores', str(context.exception))
    
    def test_calidad_prediccion_excelente(self):
        """Test clasificación de calidad excelente (>= 90%)"""
        prediccion_original = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': '2024-05-01',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        # 1 día de diferencia = ~99% precisión
        fecha_maduracion_real = '2024-05-02'
        
        resultado = validar_prediccion_polinizacion(
            prediccion_original,
            fecha_maduracion_real
        )
        
        self.assertEqual(resultado['calidad_prediccion'], 'Excelente')
        self.assertGreaterEqual(resultado['precision'], 90)
    
    def test_calidad_prediccion_pobre(self):
        """Test clasificación de calidad pobre (< 40%)"""
        prediccion_original = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': '2024-05-01',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        # 80 días de diferencia = muy pobre precisión
        fecha_maduracion_real = '2024-07-20'
        
        resultado = validar_prediccion_polinizacion(
            prediccion_original,
            fecha_maduracion_real
        )
        
        self.assertEqual(resultado['calidad_prediccion'], 'Pobre')
        self.assertLess(resultado['precision'], 40)


class ExcepcionesTest(TestCase):
    """Tests para las excepciones personalizadas"""
    
    def test_modelo_polinizacion_error(self):
        """Test excepción base ModeloPolinizacionError"""
        with self.assertRaises(ModeloPolinizacionError):
            raise ModeloPolinizacionError("Error base")
    
    def test_modelo_no_encontrado_error(self):
        """Test excepción ModeloNoEncontradoError"""
        with self.assertRaises(ModeloNoEncontradoError):
            raise ModeloNoEncontradoError("Modelo no encontrado")
        
        # Verificar que es subclase de ModeloPolinizacionError
        self.assertTrue(issubclass(ModeloNoEncontradoError, ModeloPolinizacionError))
    
    def test_modelo_corrupto_error(self):
        """Test excepción ModeloCorruptoError"""
        with self.assertRaises(ModeloCorruptoError):
            raise ModeloCorruptoError("Modelo corrupto")
        
        # Verificar que es subclase de ModeloPolinizacionError
        self.assertTrue(issubclass(ModeloCorruptoError, ModeloPolinizacionError))
    
    def test_datos_insuficientes_error(self):
        """Test excepción DatosInsuficientesError"""
        with self.assertRaises(DatosInsuficientesError):
            raise DatosInsuficientesError("Datos insuficientes")
        
        # Verificar que es subclase de ModeloPolinizacionError
        self.assertTrue(issubclass(DatosInsuficientesError, ModeloPolinizacionError))


class IntegracionTest(TestCase):
    """Tests de integración para el flujo completo de predicciones"""
    
    def setUp(self):
        """Configuración inicial"""
        cache.clear()
        import laboratorio.predicciones_polinizaciones
        laboratorio.predicciones_polinizaciones._modelo_polinizacion_cache = None
    
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_basicos')
    @patch('laboratorio.predicciones_polinizaciones.ValidadorPrediccionPolinizacion.validar_datos_completos')
    @patch('laboratorio.predicciones_polinizaciones.cargar_modelo_polinizacion')
    def test_flujo_completo_prediccion(self, mock_cargar_modelo, mock_validar_completos, mock_validar_basicos):
        """Test del flujo completo: inicial -> refinada -> validada"""
        # Configurar mocks
        mock_validar_basicos.return_value = []
        mock_validar_completos.return_value = ([], {})
        mock_modelo = MagicMock()
        mock_cargar_modelo.return_value = mock_modelo
        
        # 1. Predicción inicial
        resultado_inicial = prediccion_polinizacion_inicial(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero'
        )
        
        self.assertEqual(resultado_inicial['tipo_prediccion'], 'inicial')
        self.assertIsNone(resultado_inicial['fecha_estimada_semillas'])
        
        # 2. Refinamiento
        resultado_refinado = refinar_prediccion_polinizacion(
            especie='Cattleya',
            clima='templado',
            ubicacion='invernadero',
            fecha_polinizacion='2024-01-01',
            tipo_polinizacion='artificial'
        )
        
        self.assertEqual(resultado_refinado['tipo_prediccion'], 'refinada')
        self.assertIsNotNone(resultado_refinado['fecha_estimada_semillas'])
        self.assertGreater(resultado_refinado['confianza'], resultado_inicial['confianza'])
        
        # 3. Validación
        resultado_validacion = validar_prediccion_polinizacion(
            resultado_refinado,
            '2024-05-05'
        )
        
        self.assertIn('precision', resultado_validacion)
        self.assertIn('calidad_prediccion', resultado_validacion)
        self.assertGreater(resultado_validacion['precision'], 0)