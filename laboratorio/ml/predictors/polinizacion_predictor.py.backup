import joblib
import numpy as np
from datetime import datetime, timedelta
import os
import hashlib
from django.core.cache import cache
from django.conf import settings

# Configurar NumExpr para optimizar operaciones numéricas
os.environ['NUMEXPR_MAX_THREADS'] = '18'

# Import ML libraries needed for model deserialization
try:
    import xgboost as xgb
except ImportError as e:
    print(f"Warning: XGBoost not available: {e}")
    xgb = None

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.feature_selection import SelectKBest
    import sklearn
    print(f"Scikit-learn imports successful, version: {sklearn.__version__}")
except ImportError as e:
    print(f"Warning: Some scikit-learn components not available: {e}")

# Force import all required modules in the global scope for joblib deserialization
try:
    import pandas as pd
    import numpy as np
    print(f"NumPy version: {np.__version__}, Pandas version: {pd.__version__}")
except ImportError as e:
    print(f"Warning: NumPy/Pandas not available: {e}")
from .validaciones_prediccion import (
    ValidadorPrediccionPolinizacion, 
    PrediccionValidationError,
    validar_datos_prediccion_completa,
    validar_modelo_disponible
)

# Excepciones específicas para manejo de errores
class ModeloPolinizacionError(Exception):
    """Excepción base para errores del modelo de polinización"""
    pass

class ModeloNoEncontradoError(ModeloPolinizacionError):
    """Error cuando no se encuentra el archivo .bin"""
    pass

class ModeloCorruptoError(ModeloPolinizacionError):
    """Error cuando el archivo .bin está corrupto"""
    pass

class DatosInsuficientesError(ModeloPolinizacionError):
    """Error cuando faltan datos críticos para la predicción"""
    pass

class ErrorRedTimeout(Exception):
    """Error de red o timeout"""
    pass

# Cache para el modelo ML - evita cargar el archivo repetidamente
_modelo_polinizacion_cache = None

def cargar_modelo_polinizacion():
    """Carga el modelo ML de polinización con cache para mejorar performance"""
    global _modelo_polinizacion_cache
    
    # Si ya está en cache, retornarlo
    if _modelo_polinizacion_cache is not None:
        print(" Modelo de polinización obtenido desde cache")
        return _modelo_polinizacion_cache
    
    try:
        # Obtener la ruta absoluta del directorio actual del archivo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Try fallback model first (without XGBoost) for web server compatibility
        fallback_modelo_path = os.path.join(current_dir, 'modelos', 'Polinizacion_fallback.bin')
        original_modelo_path = os.path.join(current_dir, 'modelos', 'Polinizacion.bin')
        
        # Check which model to use
        if os.path.exists(fallback_modelo_path):
            modelo_path = fallback_modelo_path
            print(f"Using fallback model (without XGBoost)")
        else:
            modelo_path = original_modelo_path
            print(f"Using original model (with XGBoost)")
            
        modelo_path = os.path.abspath(modelo_path)
        
        print(f"Buscando modelo de polinización en: {modelo_path}")
        
        # Validar que el modelo esté disponible usando el validador
        try:
            validar_modelo_disponible(modelo_path)
        except PrediccionValidationError as e:
            if e.error_code == "MODELO_NO_ENCONTRADO":
                raise ModeloNoEncontradoError(f"El archivo del modelo no fue encontrado en {modelo_path}")
            elif e.error_code == "MODELO_CORRUPTO":
                raise ModeloCorruptoError(f"El archivo del modelo está vacío o corrupto: {modelo_path}")
            elif e.error_code == "MODELO_EXTENSION_INVALIDA":
                raise ModeloCorruptoError(f"El archivo del modelo debe tener extensión .bin: {modelo_path}")
            else:
                raise ModeloCorruptoError(f"El archivo del modelo es inválido: {str(e)}")
        
        print(f"Modelo de polinización encontrado, cargando...")
        
        try:
            # Import required scikit-learn libraries for deserialization
            from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
            from sklearn.preprocessing import StandardScaler, LabelEncoder
            from sklearn.feature_selection import SelectKBest
            import pandas as pd
            import numpy as np
            
            print(f"Required libraries imported for model deserialization")
            
            # Load the model (fallback model should not contain XGBoost)
            modelo = joblib.load(modelo_path)
            print(f"Model loaded successfully, type: {type(modelo)}")
            
            if isinstance(modelo, dict) and 'modelos' in modelo:
                available_models = list(modelo['modelos'].keys())
                print(f"Available ML models in file: {available_models}")
            
        except Exception as load_error:
            print(f"Error al cargar el modelo con joblib: {load_error}")
            print(f"Error type: {type(load_error)}")
            
            # If model loading fails, fall back to rule-based system
            print(f"Modelo ML no disponible, usando sistema basado en reglas")
            
            # Create a simple rule-based "model" 
            modelo = {
                'tipo': 'reglas_basicas',
                'metodo': 'Predicción basada en parámetros de especie sin ML',
                'mensaje': 'Modelo ML no disponible, usando valores por defecto'
            }
            
            # Don't raise error, just use rule-based fallback
            print(f"Usando sistema de predicción basado en reglas")
        
        # Verificar que el modelo cargado sea válido
        if modelo is None:
            raise ModeloCorruptoError("El modelo cargado es None, el archivo puede estar corrupto")
        
        # Guardar en cache
        _modelo_polinizacion_cache = modelo
        print(f"Modelo de polinización cargado exitosamente y guardado en cache")
        return modelo
        
    except (ModeloNoEncontradoError, ModeloCorruptoError):
        # Re-lanzar errores específicos del modelo
        raise
    except Exception as e:
        print(f"Error inesperado cargando modelo de polinización: {str(e)}")
        raise ModeloCorruptoError(f"Error inesperado al cargar el modelo de polinización: {str(e)}")

def generar_cache_key_polinizacion(especie, clima, ubicacion, **kwargs):
    """Genera una clave única para cache basada en los parámetros de predicción de polinización"""
    # Crear string con parámetros relevantes
    params_str = f"polinizacion_{especie}_{clima}_{ubicacion}"
    
    # Agregar otros parámetros si existen
    for key, value in sorted(kwargs.items()):
        if value is not None:
            params_str += f"_{key}_{value}"
    
    # Generar hash MD5 para clave única
    cache_key = hashlib.md5(params_str.encode()).hexdigest()
    return f"prediccion_polinizacion_{cache_key}"

def obtener_parametros_especie_polinizacion(especie, genero):
    """
    Retorna parámetros específicos de polinización según la especie y género
    Incluye días promedio desde polinización hasta semillas, factores de ajuste
    """
    # Diccionario de especies/géneros con sus características de polinización
    parametros_especies = {
        # Orquídeas - tiempo desde polinización hasta semillas maduras
        'cattleya': {'dias_base': 120, 'factor_clima': 1.2, 'factor_temp': 'calido'},
        'phalaenopsis': {'dias_base': 90, 'factor_clima': 1.1, 'factor_temp': 'templado'},
        'dendrobium': {'dias_base': 80, 'factor_clima': 1.0, 'factor_temp': 'templado'},
        'oncidium': {'dias_base': 100, 'factor_clima': 1.1, 'factor_temp': 'templado'},
        'vanda': {'dias_base': 140, 'factor_clima': 1.3, 'factor_temp': 'calido'},
        'cymbidium': {'dias_base': 110, 'factor_clima': 1.0, 'factor_temp': 'frio'},
        'paphiopedilum': {'dias_base': 130, 'factor_clima': 1.2, 'factor_temp': 'templado'},
        
        # Géneros por defecto
        'orchidaceae': {'dias_base': 100, 'factor_clima': 1.1, 'factor_temp': 'templado'},
        'solanaceae': {'dias_base': 45, 'factor_clima': 0.8, 'factor_temp': 'calido'},
        'leguminosae': {'dias_base': 30, 'factor_clima': 0.9, 'factor_temp': 'templado'},
    }
    
    # Buscar primero por especie específica
    especie_lower = especie.lower() if especie else ''
    genero_lower = genero.lower() if genero else ''
    
    if especie_lower in parametros_especies:
        return parametros_especies[especie_lower]
    elif genero_lower in parametros_especies:
        return parametros_especies[genero_lower]
    else:
        # Parámetros por defecto para polinización
        return {'dias_base': 60, 'factor_clima': 1.0, 'factor_temp': 'templado'}

def prediccion_polinizacion_inicial(especie=None, clima=None, ubicacion=None, **kwargs):
    """
    Genera predicción inicial de polinización usando solo el modelo .bin
    Esta es la predicción base antes de ingresar datos adicionales
    """
    try:
        print(" Iniciando predicción inicial de polinización...")
        print(f" Parámetros recibidos: especie={especie}, clima={clima}, ubicacion={ubicacion}")
        
        # Validar datos usando el validador
        datos_validacion = {
            'especie': especie,
            'clima': clima,
            'ubicacion': ubicacion
        }
        
        try:
            errores_validacion = ValidadorPrediccionPolinizacion.validar_datos_basicos(datos_validacion)
            if errores_validacion:
                raise DatosInsuficientesError(f"Errores de validación: {'; '.join(errores_validacion)}")
        except PrediccionValidationError as e:
            raise DatosInsuficientesError(f"Error de validación: {str(e)}")
        
        # Verificar cache primero
        cache_key = generar_cache_key_polinizacion(especie, clima, ubicacion, **kwargs)
        cached_result = cache.get(cache_key)
        
        if cached_result:
            print(" Predicción inicial obtenida desde cache")
            return cached_result
        
        print(" Validaciones básicas completadas")
        
        # Cargar el modelo .bin de polinización con manejo de errores específicos
        try:
            modelo = cargar_modelo_polinizacion()
            print(" Modelo de polinización cargado correctamente")
        except (ModeloNoEncontradoError, ModeloCorruptoError) as e:
            # Re-lanzar errores específicos del modelo
            raise e
        except Exception as e:
            raise ModeloCorruptoError(f"Error inesperado al cargar el modelo: {str(e)}")
        
        # Obtener parámetros específicos de la especie
        parametros = obtener_parametros_especie_polinizacion(especie, None)
        dias_base_especie = parametros['dias_base']
        factor_clima_especie = parametros['factor_clima']
        
        # Procesar especie (convertir a código numérico para el modelo)
        def procesar_especie_polinizacion(especie_str):
            especies_polinizacion = {
                'cattleya': 1, 'phalaenopsis': 2, 'dendrobium': 3, 'oncidium': 4, 
                'vanda': 5, 'cymbidium': 6, 'paphiopedilum': 7, 'miltonia': 8,
                'brassia': 9, 'odontoglossum': 10, 'masdevallia': 11, 'pleurothallis': 12
            }
            especie_lower = especie_str.lower() if especie_str else ''
            for nombre, codigo in especies_polinizacion.items():
                if nombre in especie_lower:
                    return codigo
            return 0  # Especie desconocida
        
        # Procesar clima
        def procesar_clima_polinizacion(clima_str):
            # Mapeo de códigos de clima a valores numéricos y condiciones
            climas_codigos = {
                'I': {'codigo': 2, 'descripcion': 'Intermedio'},           # Intermedio
                'IW': {'codigo': 3, 'descripcion': 'Intermedio Caliente'}, # Intermedio Caliente
                'IC': {'codigo': 4, 'descripcion': 'Intermedio Frío'}, # Intermedio Frío
                'W': {'codigo': 1, 'descripcion': 'Frío'},     # Frío  
                'C': {'codigo': 5, 'descripcion': 'Caliente'} # Caliente
            }
            
            if not clima_str:
                return 2  # Interior por defecto
            
            # Buscar por código exacto primero
            if clima_str in climas_codigos:
                print(f"   - Clima procesado: {clima_str} -> {climas_codigos[clima_str]['descripcion']} (código: {climas_codigos[clima_str]['codigo']})")
                return climas_codigos[clima_str]['codigo']
            
            # Fallback para compatibilidad con códigos antiguos
            climas_antiguos = {'frio': 1, 'templado': 2, 'calido': 3, 'humedo': 4, 'seco': 5}
            clima_lower = clima_str.lower()
            for nombre, codigo in climas_antiguos.items():
                if nombre in clima_lower:
                    return codigo
            
            return 2  # Interior por defecto
        
        # Procesar ubicación
        def procesar_ubicacion(ubicacion_str):
            ubicaciones = {'laboratorio': 1, 'invernadero': 2, 'vivero': 3, 'exterior': 4, 'campo': 5}
            if not ubicacion_str:
                return 2  # Invernadero por defecto
            ubicacion_lower = ubicacion_str.lower()
            for nombre, codigo in ubicaciones.items():
                if nombre in ubicacion_lower:
                    return codigo
            return 2  # Invernadero por defecto
        
        # Preparar datos para el modelo
        especie_num = procesar_especie_polinizacion(especie)
        clima_num = procesar_clima_polinizacion(clima)
        ubicacion_num = procesar_ubicacion(ubicacion)
        
        print(f"Datos procesados para predicción inicial:")
        print(f"   - Especie: {especie} -> {especie_num}")
        print(f"   - Clima: {clima} -> {clima_num}")
        print(f"   - Ubicación: {ubicacion} -> {ubicacion_num}")
        
        # Usar parámetros de especie como predicción inicial (sin datos adicionales)
        dias_estimados_inicial = dias_base_especie
        
        # Aplicar factor de clima básico usando los nuevos códigos
        ajuste_clima_inicial = 1.0
        if clima:
            # Ajustes específicos para cada código de clima
            ajustes_clima = {
                'I': 1.0,    # Intermedio - condiciones controladas normales
                'IW': 0.95,  # Intermedio Caliente - ligeramente más cálido, acelera un poco
                'IC': 1.25,  # Intermedio Frío - más frío, retrasa  
                'W': 1.25,   # Frío - más frío y condiciones adversas, retrasa
                'C': 0.80    # Caliente - muy cálido, acelera mucho
            }
            
            if clima in ajustes_clima:
                ajuste_clima_inicial = ajustes_clima[clima]
                print(f"   - Factor de clima aplicado: {clima} -> {ajuste_clima_inicial}")
            else:
                # Fallback para compatibilidad
                clima_lower = clima.lower()
                if 'frio' in clima_lower or 'w' in clima_lower:
                    ajuste_clima_inicial = 1.2
                elif 'calido' in clima_lower or 'c' in clima_lower:
                    ajuste_clima_inicial = 0.9
                elif 'humedo' in clima_lower:
                    ajuste_clima_inicial = 1.1
        
        dias_estimados_final = int(dias_estimados_inicial * factor_clima_especie * ajuste_clima_inicial)
        
        # Calcular confianza inicial (baja sin datos adicionales)
        confianza_inicial = 40  # 40% de confianza con solo datos básicos
        
        print(f" Días estimados iniciales: {dias_estimados_final}")
        print(f" Confianza inicial: {confianza_inicial}%")
        
        # Información específica de la predicción inicial
        info_prediccion = {
            'especie': especie,
            'tipo': 'Predicción inicial de polinización',
            'clima_usado': clima or 'No especificado',
            'ubicacion_usada': ubicacion or 'No especificada',
            'metodo': 'Basado en parámetros de especie y modelo .bin',
            'factores_considerados': ['especie', 'clima_basico'],
            'factores_faltantes': ['fecha_polinizacion', 'condiciones_detalladas']
        }
        
        resultado = {
            'dias_estimados': dias_estimados_final,
            'fecha_estimada_semillas': None,  # No se puede calcular sin fecha de polinización
            'confianza': confianza_inicial,
            'tipo_prediccion': 'inicial',
            'especie_info': info_prediccion,
            'parametros_usados': {
                'especie': especie,
                'clima': clima,
                'ubicacion': ubicacion
            },
            'datos_del_modelo': {
                'dias_base_especie': dias_base_especie,
                'factor_clima_especie': factor_clima_especie,
                'ajuste_clima_aplicado': ajuste_clima_inicial
            },
            'siguiente_paso': 'Ingrese fecha de polinización para calcular fecha estimada de semillas'
        }
        
        # Guardar en cache por 1 hora (3600 segundos)
        cache.set(cache_key, resultado, 3600)
        print(" Predicción inicial guardada en cache")
        
        return resultado
        
    except ModeloNoEncontradoError as e:
        print(f" Modelo no encontrado: {str(e)}")
        return {
            'error': f"Modelo no encontrado: {str(e)}",
            'error_code': 'MODELO_NO_ENCONTRADO',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except ModeloCorruptoError as e:
        print(f" Modelo corrupto: {str(e)}")
        return {
            'error': f"Modelo corrupto: {str(e)}",
            'error_code': 'MODELO_CORRUPTO',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except DatosInsuficientesError as e:
        print(f" Datos insuficientes: {str(e)}")
        return {
            'error': f"Datos insuficientes: {str(e)}",
            'error_code': 'DATOS_INSUFICIENTES',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except Exception as e:
        print(f" Error inesperado en predicción inicial de polinización: {str(e)}")
        return {
            'error': f"Error inesperado en la predicción inicial: {str(e)}",
            'error_code': 'ERROR_INTERNO',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
def refinar_prediccion_polinizacion(especie=None, clima=None, ubicacion=None, 
                                   fecha_polinizacion=None, condiciones_climaticas=None,
                                   tipo_polinizacion=None, **kwargs):
    """
    Refina la predicción de polinización con datos adicionales ingresados progresivamente
    Combina datos del modelo .bin con información específica del usuario
    """
    try:
        print(" Refinando predicción de polinización con datos adicionales...")
        print(f" Parámetros adicionales: fecha_polinizacion={fecha_polinizacion}, tipo_polinizacion={tipo_polinizacion}")
        
        # Validar datos completos usando el validador
        datos_validacion = {
            'especie': especie,
            'clima': clima,
            'ubicacion': ubicacion,
            'fecha_polinizacion': fecha_polinizacion,
            'condiciones_climaticas': condiciones_climaticas,
            'tipo_polinizacion': tipo_polinizacion
        }
        
        try:
            errores, datos_procesados = ValidadorPrediccionPolinizacion.validar_datos_completos(datos_validacion)
            if errores:
                raise DatosInsuficientesError(f"Errores de validación: {'; '.join(errores)}")
        except PrediccionValidationError as e:
            raise DatosInsuficientesError(f"Error de validación: {str(e)}")
        
        # Obtener predicción inicial como base
        prediccion_base = prediccion_polinizacion_inicial(especie, clima, ubicacion, **kwargs)
        
        if 'error' in prediccion_base:
            return prediccion_base
        
        # Cargar el modelo para refinamiento
        modelo = cargar_modelo_polinizacion()
        
        # Obtener parámetros base de la especie
        parametros = obtener_parametros_especie_polinizacion(especie, None)
        dias_base = prediccion_base['dias_estimados']
        
        # Aplicar refinamientos progresivos
        dias_refinados = dias_base
        confianza = prediccion_base['confianza']
        factores_aplicados = ['especie', 'clima_basico']
        
        # Refinamiento 1: Fecha de polinización (permite calcular fecha estimada)
        fecha_estimada_semillas = None
        if fecha_polinizacion:
            try:
                if isinstance(fecha_polinizacion, str):
                    fecha_pol = datetime.strptime(fecha_polinizacion, '%Y-%m-%d')
                else:
                    fecha_pol = fecha_polinizacion
                
                fecha_estimada_semillas = fecha_pol + timedelta(days=dias_refinados)
                confianza += 20  # Aumentar confianza por tener fecha específica
                factores_aplicados.append('fecha_polinizacion')
                print(f" Fecha de polinización: {fecha_pol.strftime('%Y-%m-%d')}")
                print(f" Fecha estimada de semillas: {fecha_estimada_semillas.strftime('%Y-%m-%d')}")
            except Exception as e:
                print(f" Error procesando fecha de polinización: {e}")
        
        # Refinamiento 2: Condiciones climáticas detalladas
        if condiciones_climaticas:
            ajuste_clima_detallado = 1.0
            
            # Procesar temperatura si está disponible
            if isinstance(condiciones_climaticas, dict):
                temperatura = condiciones_climaticas.get('temperatura', {})
                humedad = condiciones_climaticas.get('humedad')
                precipitacion = condiciones_climaticas.get('precipitacion')
                
                # Ajuste por temperatura
                if isinstance(temperatura, dict):
                    temp_promedio = temperatura.get('promedio')
                    if temp_promedio:
                        if temp_promedio < 15:
                            ajuste_clima_detallado *= 1.3  # Frío retrasa
                        elif temp_promedio > 30:
                            ajuste_clima_detallado *= 0.8  # Calor acelera
                        elif 20 <= temp_promedio <= 25:
                            ajuste_clima_detallado *= 0.9  # Temperatura óptima
                
                # Ajuste por humedad
                if humedad:
                    if humedad > 80:
                        ajuste_clima_detallado *= 1.1  # Alta humedad retrasa ligeramente
                    elif humedad < 40:
                        ajuste_clima_detallado *= 1.2  # Baja humedad retrasa más
                
                # Ajuste por precipitación
                if precipitacion:
                    if precipitacion > 100:  # mm
                        ajuste_clima_detallado *= 1.1  # Mucha lluvia puede retrasar
                    elif precipitacion < 20:
                        ajuste_clima_detallado *= 1.05  # Poca lluvia retrasa ligeramente
            
            dias_refinados = int(dias_refinados * ajuste_clima_detallado)
            confianza += 15  # Aumentar confianza por datos climáticos detallados
            factores_aplicados.append('condiciones_climaticas_detalladas')
            print(f" Ajuste por condiciones climáticas: {ajuste_clima_detallado}")
        
        # Refinamiento 3: Tipo de polinización
        if tipo_polinizacion:
            ajuste_polinizacion = 1.0
            tipo_lower = tipo_polinizacion.lower()
            
            if 'artificial' in tipo_lower or 'manual' in tipo_lower:
                ajuste_polinizacion = 0.95  # Polinización artificial es más eficiente
                confianza += 10
            elif 'natural' in tipo_lower:
                ajuste_polinizacion = 1.05  # Polinización natural puede ser menos eficiente
                confianza += 5
            elif 'cruzada' in tipo_lower:
                ajuste_polinizacion = 1.0  # Polinización cruzada es estándar
                confianza += 8
            
            dias_refinados = int(dias_refinados * ajuste_polinizacion)
            factores_aplicados.append('tipo_polinizacion')
            print(f" Ajuste por tipo de polinización: {ajuste_polinizacion}")
        
        # Recalcular fecha estimada con refinamientos
        if fecha_polinizacion and dias_refinados != dias_base:
            fecha_pol = datetime.strptime(fecha_polinizacion, '%Y-%m-%d') if isinstance(fecha_polinizacion, str) else fecha_polinizacion
            fecha_estimada_semillas = fecha_pol + timedelta(days=dias_refinados)
        
        # Limitar confianza máxima
        confianza = min(confianza, 95)  # Máximo 95% sin validación real
        
        # Información detallada del refinamiento
        info_refinada = {
            'especie': especie,
            'tipo': 'Predicción refinada de polinización',
            'clima_usado': clima,
            'ubicacion_usada': ubicacion,
            'metodo': 'Modelo .bin + datos progresivos del usuario',
            'factores_considerados': factores_aplicados,
            'refinamientos_aplicados': {
                'fecha_polinizacion': fecha_polinizacion is not None,
                'condiciones_climaticas': condiciones_climaticas is not None,
                'tipo_polinizacion': tipo_polinizacion is not None
            },
            'mejora_confianza': confianza - prediccion_base['confianza']
        }
        
        resultado = {
            'dias_estimados': dias_refinados,
            'fecha_estimada_semillas': fecha_estimada_semillas.strftime('%Y-%m-%d') if fecha_estimada_semillas else None,
            'confianza': confianza,
            'tipo_prediccion': 'refinada',
            'especie_info': info_refinada,
            'parametros_usados': {
                'especie': especie,
                'clima': clima,
                'ubicacion': ubicacion,
                'fecha_polinizacion': fecha_polinizacion,
                'condiciones_climaticas': condiciones_climaticas,
                'tipo_polinizacion': tipo_polinizacion
            },
            'comparacion_con_inicial': {
                'dias_iniciales': prediccion_base['dias_estimados'],
                'dias_refinados': dias_refinados,
                'diferencia_dias': dias_refinados - prediccion_base['dias_estimados'],
                'confianza_inicial': prediccion_base['confianza'],
                'confianza_refinada': confianza
            },
            'siguiente_paso': 'Ingrese fecha de maduración real cuando las semillas estén listas para validar la predicción'
        }
        
        return resultado
        
    except ModeloNoEncontradoError as e:
        print(f" Modelo no encontrado: {str(e)}")
        return {
            'error': f"Modelo no encontrado: {str(e)}",
            'error_code': 'MODELO_NO_ENCONTRADO',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except ModeloCorruptoError as e:
        print(f" Modelo corrupto: {str(e)}")
        return {
            'error': f"Modelo corrupto: {str(e)}",
            'error_code': 'MODELO_CORRUPTO',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except DatosInsuficientesError as e:
        print(f" Datos insuficientes: {str(e)}")
        return {
            'error': f"Datos insuficientes: {str(e)}",
            'error_code': 'DATOS_INSUFICIENTES',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except ValueError as e:
        print(f" Error de formato de fecha: {str(e)}")
        return {
            'error': f"Error de formato de fecha: {str(e)}",
            'error_code': 'FECHA_INVALIDA',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }
    except Exception as e:
        print(f" Error inesperado refinando predicción de polinización: {str(e)}")
        return {
            'error': f"Error inesperado refinando la predicción: {str(e)}",
            'error_code': 'ERROR_INTERNO',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0,
            'tipo_prediccion': 'error',
            'parametros_usados': None
        }

def validar_prediccion_polinizacion(prediccion_original, fecha_maduracion_real):
    """
    Valida una predicción de polinización comparándola con el resultado real
    Calcula precisión y proporciona información para mejorar futuras predicciones
    """
    try:
        print(" Validando predicción de polinización con resultado real...")
        print(f" Fecha de maduración real: {fecha_maduracion_real}")
        
        # Validaciones básicas
        if not prediccion_original:
            raise ValueError("Se requiere la predicción original para validar")
        
        if not fecha_maduracion_real:
            raise ValueError("Se requiere la fecha de maduración real para validar")
        
        if 'error' in prediccion_original:
            raise ValueError("No se puede validar una predicción que tuvo errores")
        
        # Obtener datos de la predicción original
        fecha_estimada_str = prediccion_original.get('fecha_estimada_semillas')
        dias_estimados = prediccion_original.get('dias_estimados')
        fecha_polinizacion_str = prediccion_original.get('parametros_usados', {}).get('fecha_polinizacion')
        
        if not fecha_estimada_str:
            raise ValueError("La predicción original debe tener una fecha estimada de semillas")
        
        if not fecha_polinizacion_str:
            raise ValueError("Se requiere la fecha de polinización original para calcular la precisión")
        
        # Procesar fechas
        fecha_estimada = datetime.strptime(fecha_estimada_str, '%Y-%m-%d')
        fecha_real = datetime.strptime(fecha_maduracion_real, '%Y-%m-%d') if isinstance(fecha_maduracion_real, str) else fecha_maduracion_real
        fecha_polinizacion = datetime.strptime(fecha_polinizacion_str, '%Y-%m-%d')
        
        # Calcular métricas de precisión
        dias_reales = (fecha_real - fecha_polinizacion).days
        diferencia_dias = abs(dias_reales - dias_estimados)
        desviacion_porcentual = (diferencia_dias / dias_estimados) * 100 if dias_estimados > 0 else 100
        
        # Calcular precisión (100% - desviación porcentual, mínimo 0%)
        precision = max(0, 100 - desviacion_porcentual)
        
        # Determinar calidad de la predicción
        if precision >= 90:
            calidad = "Excelente"
        elif precision >= 75:
            calidad = "Buena"
        elif precision >= 60:
            calidad = "Aceptable"
        elif precision >= 40:
            calidad = "Regular"
        else:
            calidad = "Pobre"
        
        # Análisis de la desviación
        if dias_reales > dias_estimados:
            tendencia = "La maduración tomó más tiempo del estimado"
            factor_correccion = dias_reales / dias_estimados
        elif dias_reales < dias_estimados:
            tendencia = "La maduración fue más rápida de lo estimado"
            factor_correccion = dias_reales / dias_estimados
        else:
            tendencia = "La predicción fue exacta"
            factor_correccion = 1.0
        
        print(f" Días estimados: {dias_estimados}")
        print(f" Días reales: {dias_reales}")
        print(f" Diferencia: {diferencia_dias} días")
        print(f" Precisión: {precision:.1f}%")
        print(f" Calidad: {calidad}")
        
        # Información para mejorar el modelo
        factores_mejora = []
        if diferencia_dias > 7:
            factores_mejora.append("Considerar factores ambientales adicionales")
        if desviacion_porcentual > 20:
            factores_mejora.append("Revisar parámetros específicos de la especie")
        if precision < 60:
            factores_mejora.append("Recopilar más datos de esta especie y condiciones")
        
        # Resultado de la validación
        resultado_validacion = {
            'fecha_estimada': fecha_estimada_str,
            'fecha_real': fecha_maduracion_real if isinstance(fecha_maduracion_real, str) else fecha_maduracion_real.strftime('%Y-%m-%d'),
            'fecha_polinizacion': fecha_polinizacion_str,
            'dias_estimados': dias_estimados,
            'dias_reales': dias_reales,
            'diferencia_dias': diferencia_dias,
            'precision': round(precision, 1),
            'desviacion_porcentual': round(desviacion_porcentual, 1),
            'calidad_prediccion': calidad,
            'tendencia': tendencia,
            'factor_correccion': round(factor_correccion, 3),
            'prediccion_original': prediccion_original,
            'metricas_detalladas': {
                'error_absoluto': diferencia_dias,
                'error_relativo': round(desviacion_porcentual, 2),
                'precision_temporal': precision,
                'factor_ajuste_sugerido': factor_correccion
            },
            'recomendaciones_mejora': factores_mejora,
            'datos_para_entrenamiento': {
                'especie': prediccion_original.get('parametros_usados', {}).get('especie'),
                'clima': prediccion_original.get('parametros_usados', {}).get('clima'),
                'ubicacion': prediccion_original.get('parametros_usados', {}).get('ubicacion'),
                'tipo_polinizacion': prediccion_original.get('parametros_usados', {}).get('tipo_polinizacion'),
                'dias_reales_observados': dias_reales,
                'condiciones_climaticas': prediccion_original.get('parametros_usados', {}).get('condiciones_climaticas')
            }
        }
        
        return resultado_validacion
        
    except DatosInsuficientesError as e:
        print(f" Datos insuficientes para validación: {str(e)}")
        return {
            'error': f"Datos insuficientes para validación: {str(e)}",
            'error_code': 'DATOS_INSUFICIENTES',
            'precision': None,
            'fecha_estimada': None,
            'fecha_real': None,
            'diferencia_dias': None
        }
    except ValueError as e:
        print(f" Error de formato de fecha en validación: {str(e)}")
        return {
            'error': f"Error de formato de fecha: {str(e)}",
            'error_code': 'FECHA_INVALIDA',
            'precision': None,
            'fecha_estimada': None,
            'fecha_real': None,
            'diferencia_dias': None
        }
    except Exception as e:
        print(f" Error inesperado validando predicción de polinización: {str(e)}")
        return {
            'error': f"Error inesperado en la validación: {str(e)}",
            'error_code': 'ERROR_INTERNO',
            'precision': None,
            'fecha_estimada': None,
            'fecha_real': None,
            'diferencia_dias': None
        }

def prediccion_polinizacion_completa(especie=None, clima=None, ubicacion=None,
                                   fecha_polinizacion=None, condiciones_climaticas=None,
                                   tipo_polinizacion=None, fecha_maduracion=None, **kwargs):
    """
    Función principal que maneja el flujo completo de predicción de polinización
    Puede generar predicción inicial, refinarla, o validarla según los datos disponibles
    """
    try:
        print(" Iniciando predicción completa de polinización...")
        
        # Determinar qué tipo de predicción realizar según los datos disponibles
        if fecha_maduracion and fecha_polinizacion:
            # Si hay fecha de maduración, es una validación
            print(" Modo: Validación de predicción existente")
            
            # Primero generar/refinar la predicción
            if condiciones_climaticas or tipo_polinizacion:
                prediccion = refinar_prediccion_polinizacion(
                    especie, clima, ubicacion, fecha_polinizacion,
                    condiciones_climaticas, tipo_polinizacion, **kwargs
                )
            else:
                # Generar predicción básica con fecha de polinización
                prediccion_inicial = prediccion_polinizacion_inicial(especie, clima, ubicacion, **kwargs)
                if 'error' in prediccion_inicial:
                    return prediccion_inicial
                
                # Calcular fecha estimada con la fecha de polinización
                fecha_pol = datetime.strptime(fecha_polinizacion, '%Y-%m-%d')
                fecha_estimada = fecha_pol + timedelta(days=prediccion_inicial['dias_estimados'])
                
                prediccion = prediccion_inicial.copy()
                prediccion['fecha_estimada_semillas'] = fecha_estimada.strftime('%Y-%m-%d')
                prediccion['parametros_usados']['fecha_polinizacion'] = fecha_polinizacion
            
            # Validar la predicción
            if 'error' not in prediccion:
                validacion = validar_prediccion_polinizacion(prediccion, fecha_maduracion)
                return {
                    'tipo_resultado': 'validacion',
                    'prediccion': prediccion,
                    'validacion': validacion
                }
            else:
                return prediccion
                
        elif fecha_polinizacion and (condiciones_climaticas or tipo_polinizacion):
            # Si hay fecha de polinización y datos adicionales, refinar
            print(" Modo: Predicción refinada")
            return refinar_prediccion_polinizacion(
                especie, clima, ubicacion, fecha_polinizacion,
                condiciones_climaticas, tipo_polinizacion, **kwargs
            )
            
        elif fecha_polinizacion:
            # Si solo hay fecha de polinización, generar predicción básica con fecha
            print(" Modo: Predicción básica con fecha")
            prediccion_inicial = prediccion_polinizacion_inicial(especie, clima, ubicacion, **kwargs)
            
            if 'error' in prediccion_inicial:
                return prediccion_inicial
            
            # Calcular fecha estimada
            fecha_pol = datetime.strptime(fecha_polinizacion, '%Y-%m-%d')
            fecha_estimada = fecha_pol + timedelta(days=prediccion_inicial['dias_estimados'])
            
            resultado = prediccion_inicial.copy()
            resultado['fecha_estimada_semillas'] = fecha_estimada.strftime('%Y-%m-%d')
            resultado['parametros_usados']['fecha_polinizacion'] = fecha_polinizacion
            resultado['confianza'] += 20  # Aumentar confianza por tener fecha específica
            resultado['tipo_prediccion'] = 'basica_con_fecha'
            
            return resultado
            
        else:
            # Solo predicción inicial sin fecha de polinización
            print(" Modo: Predicción inicial")
            return prediccion_polinizacion_inicial(especie, clima, ubicacion, **kwargs)
            
    except Exception as e:
        print(f" Error en predicción completa de polinización: {str(e)}")
        return {
            'error': f"Error en la predicción completa: {str(e)}",
            'tipo_resultado': 'error',
            'dias_estimados': None,
            'fecha_estimada_semillas': None,
            'confianza': 0
        }