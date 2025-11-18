import joblib
import numpy as np
from datetime import datetime, timedelta
import os

# Configurar NumExpr para usar núcleos optimizados (18 en lugar de 20 para mejor rendimiento)
os.environ['NUMEXPR_MAX_THREADS'] = '18'

# aqui se carga el metodo de prediccion para retornar la fecha y debe cargar con el model .bin
def cargar_modelo():
    try:
        # Obtener la ruta absoluta del directorio actual del archivo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Subir dos niveles para llegar a laboratorio/
        laboratorio_dir = os.path.dirname(os.path.dirname(current_dir))
        # El modelo está en laboratorio/modelos/germinacion.pkl
        modelo_path = os.path.join(laboratorio_dir, 'modelos', 'germinacion.pkl')
        modelo_path = os.path.abspath(modelo_path)
        
        print(f"🔍 Buscando modelo en: {modelo_path}")
        
        if not os.path.exists(modelo_path):
            raise FileNotFoundError(f"Modelo no encontrado en {modelo_path}")
        
        print(f"✅ Modelo encontrado, cargando...")
        modelo = joblib.load(modelo_path)
        print(f"✅ Modelo cargado exitosamente")
        return modelo
    except Exception as e:
        print(f"❌ Error cargando modelo: {str(e)}")
        raise Exception(f"Error al cargar el modelo: {str(e)}")

def calcular_tiempo_germinacion(f_siembra, f_germi, fecha_ingreso, fecha_polinizacion):
    """
    Calcula el tiempo de germinación usando fechas alternativas
    Prioridad: f_germi y f_siembra > fecha_ingreso y fecha_polinizacion
    """
    def procesar_fecha(fecha):
        if isinstance(fecha, str):
            try:
                return datetime.strptime(fecha, '%Y-%m-%d')
            except:
                try:
                    return datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
                except:
                    return None
        elif isinstance(fecha, datetime):
            return fecha
        return None
    
    # Procesar todas las fechas
    fecha_siembra = procesar_fecha(f_siembra)
    fecha_germinacion = procesar_fecha(f_germi)
    fecha_ing = procesar_fecha(fecha_ingreso)
    fecha_pol = procesar_fecha(fecha_polinizacion)
    
    # Intentar calcular tiempo_germinacion con diferentes combinaciones
    tiempo_germinacion = None
    
    # Opción 1: f_germi - f_siembra (más preciso)
    if fecha_germinacion and fecha_siembra:
        tiempo_germinacion = (fecha_germinacion - fecha_siembra).days
    
    # Opción 2: fecha_ingreso - fecha_polinizacion
    elif fecha_ing and fecha_pol:
        tiempo_germinacion = (fecha_ing - fecha_pol).days
    
    # Opción 3: f_germi - fecha_polinizacion
    elif fecha_germinacion and fecha_pol:
        tiempo_germinacion = (fecha_germinacion - fecha_pol).days
    
    # Opción 4: fecha_ingreso - f_siembra
    elif fecha_ing and fecha_siembra:
        tiempo_germinacion = (fecha_ing - fecha_siembra).days
    
    return max(0, tiempo_germinacion) if tiempo_germinacion is not None else None

def obtener_parametros_especie_genero(especie, genero):
    """
    Retorna parámetros específicos de germinación según la especie y género
    Incluye días promedio, factores de ajuste y características específicas
    """
    # Diccionario de especies/géneros con sus características de germinación
    parametros_especies = {
        # Orquídeas
        'cattleya': {'dias_base': 180, 'factor_clima': 1.2, 'factor_temp': 'calido'},
        'phalaenopsis': {'dias_base': 150, 'factor_clima': 1.1, 'factor_temp': 'templado'},
        'dendrobium': {'dias_base': 120, 'factor_clima': 1.0, 'factor_temp': 'templado'},
        'oncidium': {'dias_base': 140, 'factor_clima': 1.1, 'factor_temp': 'templado'},
        'vanda': {'dias_base': 200, 'factor_clima': 1.3, 'factor_temp': 'calido'},
        
        # Géneros por defecto
        'orchidaceae': {'dias_base': 160, 'factor_clima': 1.1, 'factor_temp': 'templado'},
        'solanaceae': {'dias_base': 15, 'factor_clima': 0.7, 'factor_temp': 'calido'},
        'leguminosae': {'dias_base': 12, 'factor_clima': 0.8, 'factor_temp': 'templado'},
    }
    
    # Buscar primero por especie específica
    especie_lower = especie.lower() if especie else ''
    genero_lower = genero.lower() if genero else ''
    
    if especie_lower in parametros_especies:
        return parametros_especies[especie_lower]
    elif genero_lower in parametros_especies:
        return parametros_especies[genero_lower]
    else:
        # Parámetros por defecto
        return {'dias_base': 30, 'factor_clima': 1.0, 'factor_temp': 'templado'}

def ajustar_prediccion_por_especie(dias_predichos, especie, genero, clima, ubicacion, tipo_polinizacion):
    """
    Ajusta la predicción base usando conocimiento específico de la especie/género
    """
    parametros = obtener_parametros_especie_genero(especie, genero)
    
    # Usar días base específicos de la especie si la predicción del modelo es muy diferente
    dias_base_especie = parametros['dias_base']
    factor_clima_especie = parametros['factor_clima']
    
    # Ajuste por clima
    ajuste_clima = 1.0
    if clima:
        clima_lower = clima.lower()
        if 'frio' in clima_lower or 'fría' in clima_lower:
            ajuste_clima = 1.3
        elif 'calido' in clima_lower or 'cálido' in clima_lower or 'calor' in clima_lower:
            ajuste_clima = 0.8
        elif 'templado' in clima_lower:
            ajuste_clima = 1.0
    
    # Ajuste por ubicación
    ajuste_ubicacion = 1.0
    if ubicacion:
        ubicacion_lower = ubicacion.lower()
        if 'invernadero' in ubicacion_lower:
            ajuste_ubicacion = 0.9
        elif 'exterior' in ubicacion_lower or 'campo' in ubicacion_lower:
            ajuste_ubicacion = 1.2
        elif 'laboratorio' in ubicacion_lower:
            ajuste_ubicacion = 0.8
    
    # Ajuste por tipo de polinización
    ajuste_polinizacion = 1.0
    if tipo_polinizacion:
        tipo_lower = tipo_polinizacion.lower()
        if 'artificial' in tipo_lower or 'manual' in tipo_lower:
            ajuste_polinizacion = 0.9
        elif 'natural' in tipo_lower:
            ajuste_polinizacion = 1.1
        elif 'cruzada' in tipo_lower:
            ajuste_polinizacion = 1.0
    
    # Combinar predicción del modelo con conocimiento específico de especie
    peso_modelo = 0.7
    peso_especie = 0.3
    
    dias_ajustados = (
        (dias_predichos * peso_modelo) + 
        (dias_base_especie * factor_clima_especie * peso_especie)
    ) * ajuste_clima * ajuste_ubicacion * ajuste_polinizacion
    
    return int(max(1, dias_ajustados))

# Función de predicción de germinación eliminada