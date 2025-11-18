"""
Validaciones específicas para predicciones de polinización
"""
import os
import re
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from django.core.exceptions import ValidationError
from django.utils import timezone


class PrediccionValidationError(ValidationError):
    """Excepción personalizada para errores de validación de predicciones"""
    
    def __init__(self, message: str, code: str = None, params: Dict = None):
        super().__init__(message, code, params)
        self.error_code = code
        self.error_params = params or {}


class ValidadorPrediccionPolinizacion:
    """Validador para datos de predicciones de polinización"""
    
    # Especies soportadas por el modelo
    ESPECIES_SOPORTADAS = {
        'cattleya', 'phalaenopsis', 'dendrobium', 'oncidium', 'vanda',
        'cymbidium', 'paphiopedilum', 'miltonia', 'brassia', 'odontoglossum',
        'masdevallia', 'pleurothallis'
    }
    
    # Climas válidos (nuevos códigos)
    CLIMAS_VALIDOS = {'i', 'iw', 'ic', 'w', 'c'}
    
    # Ubicaciones válidas
    UBICACIONES_VALIDAS = {'laboratorio', 'invernadero', 'vivero', 'exterior', 'campo'}
    
    # Tipos de polinización válidos
    TIPOS_POLINIZACION_VALIDOS = {'self', 'hybrid', 'sibling'}
    
    # Estaciones válidas
    ESTACIONES_VALIDAS = {'primavera', 'verano', 'otoño', 'invierno'}
    
    @classmethod
    def validar_modelo_disponible(cls, ruta_modelo: str) -> None:
        """Valida que el modelo .bin esté disponible y sea válido"""
        if not os.path.exists(ruta_modelo):
            raise PrediccionValidationError(
                f"El archivo del modelo no fue encontrado en {ruta_modelo}",
                code="MODELO_NO_ENCONTRADO"
            )
        
        if not os.path.isfile(ruta_modelo):
            raise PrediccionValidationError(
                f"La ruta del modelo no apunta a un archivo válido: {ruta_modelo}",
                code="MODELO_INVALIDO"
            )
        
        # Verificar que el archivo no esté vacío
        if os.path.getsize(ruta_modelo) == 0:
            raise PrediccionValidationError(
                "El archivo del modelo está vacío o corrupto",
                code="MODELO_CORRUPTO"
            )
        
        # Verificar extensión
        if not ruta_modelo.endswith('.bin'):
            raise PrediccionValidationError(
                "El archivo del modelo debe tener extensión .bin",
                code="MODELO_EXTENSION_INVALIDA"
            )
    
    @classmethod
    def validar_datos_basicos(cls, datos: Dict[str, Any]) -> List[str]:
        """Valida los datos básicos requeridos para una predicción"""
        errores = []
        
        # Validar especie (requerida)
        especie = datos.get('especie')
        if not especie:
            errores.append("La especie es requerida para generar una predicción")
        elif not isinstance(especie, str):
            errores.append("La especie debe ser una cadena de texto")
        elif especie.strip() == '':
            errores.append("La especie no puede estar vacía")
        elif especie.lower().strip() not in cls.ESPECIES_SOPORTADAS:
            especies_disponibles = ', '.join(sorted(cls.ESPECIES_SOPORTADAS))
            errores.append(
                f"La especie '{especie}' no está soportada. "
                f"Especies disponibles: {especies_disponibles}"
            )
        
        # Validar clima (opcional)
        clima = datos.get('clima')
        if clima is not None:
            if not isinstance(clima, str):
                errores.append("El clima debe ser una cadena de texto")
            elif clima.lower().strip() not in cls.CLIMAS_VALIDOS:
                climas_disponibles = ', '.join(sorted(cls.CLIMAS_VALIDOS))
                errores.append(
                    f"El clima '{clima}' no es válido. "
                    f"Climas disponibles: {climas_disponibles}"
                )
        
        # Validar ubicación (opcional)
        ubicacion = datos.get('ubicacion')
        if ubicacion is not None:
            if not isinstance(ubicacion, str):
                errores.append("La ubicación debe ser una cadena de texto")
            elif ubicacion.lower().strip() not in cls.UBICACIONES_VALIDAS:
                ubicaciones_disponibles = ', '.join(sorted(cls.UBICACIONES_VALIDAS))
                errores.append(
                    f"La ubicación '{ubicacion}' no es válida. "
                    f"Ubicaciones disponibles: {ubicaciones_disponibles}"
                )
        
        return errores
    
    @classmethod
    def validar_fecha(cls, fecha_str: str, nombre_campo: str) -> Optional[date]:
        """Valida formato y validez de una fecha"""
        if not fecha_str:
            return None
        
        # Validar formato YYYY-MM-DD
        patron_fecha = r'^\d{4}-\d{2}-\d{2}$'
        if not re.match(patron_fecha, fecha_str):
            raise PrediccionValidationError(
                f"El formato de {nombre_campo} debe ser YYYY-MM-DD, recibido: {fecha_str}",
                code="FECHA_FORMATO_INVALIDO"
            )
        
        try:
            fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError as e:
            raise PrediccionValidationError(
                f"La {nombre_campo} no es una fecha válida: {fecha_str}",
                code="FECHA_INVALIDA"
            )
        
        # Verificar que no sea futura
        hoy = timezone.now().date()
        if fecha_obj > hoy:
            raise PrediccionValidationError(
                f"La {nombre_campo} no puede ser futura. Fecha: {fecha_str}, Hoy: {hoy}",
                code="FECHA_FUTURA"
            )
        
        return fecha_obj
    
    @classmethod
    def validar_fechas_relacionadas(cls, fecha_polinizacion: Optional[date], 
                                   fecha_maduracion: Optional[date]) -> None:
        """Valida la relación entre fechas de polinización y maduración"""
        if fecha_polinizacion and fecha_maduracion:
            if fecha_maduracion <= fecha_polinizacion:
                raise PrediccionValidationError(
                    f"La fecha de maduración ({fecha_maduracion}) debe ser posterior "
                    f"a la fecha de polinización ({fecha_polinizacion})",
                    code="FECHAS_ORDEN_INVALIDO"
                )
            
            # Verificar que no sea demasiado pronto (mínimo 7 días)
            diferencia_dias = (fecha_maduracion - fecha_polinizacion).days
            if diferencia_dias < 7:
                raise PrediccionValidationError(
                    f"La fecha de maduración debe ser al menos 7 días después "
                    f"de la polinización. Diferencia actual: {diferencia_dias} días",
                    code="MADURACION_MUY_TEMPRANA"
                )
    
    @classmethod
    def validar_tipo_polinizacion(cls, tipo_polinizacion: str) -> None:
        """Valida el tipo de polinización"""
        if tipo_polinizacion and tipo_polinizacion.lower().strip() not in cls.TIPOS_POLINIZACION_VALIDOS:
            tipos_disponibles = ', '.join(sorted(cls.TIPOS_POLINIZACION_VALIDOS))
            raise PrediccionValidationError(
                f"El tipo de polinización '{tipo_polinizacion}' no es válido. "
                f"Tipos disponibles: {tipos_disponibles}",
                code="TIPO_POLINIZACION_INVALIDO"
            )
    
    @classmethod
    def validar_condiciones_climaticas(cls, condiciones: Dict[str, Any]) -> List[str]:
        """Valida las condiciones climáticas detalladas"""
        errores = []
        
        if not isinstance(condiciones, dict):
            errores.append("Las condiciones climáticas deben ser un objeto")
            return errores
        
        # Validar temperatura
        temperatura = condiciones.get('temperatura')
        if temperatura is not None:
            if not isinstance(temperatura, dict):
                errores.append("La temperatura debe ser un objeto con promedio, mínima y máxima")
            else:
                # Validar temperatura promedio
                temp_promedio = temperatura.get('promedio')
                if temp_promedio is not None:
                    try:
                        temp_promedio = float(temp_promedio)
                        if temp_promedio < -50 or temp_promedio > 60:
                            errores.append("La temperatura promedio debe estar entre -50°C y 60°C")
                    except (ValueError, TypeError):
                        errores.append("La temperatura promedio debe ser un número")
                
                # Validar temperatura mínima
                temp_minima = temperatura.get('minima')
                if temp_minima is not None:
                    try:
                        temp_minima = float(temp_minima)
                        if temp_minima < -60 or temp_minima > 50:
                            errores.append("La temperatura mínima debe estar entre -60°C y 50°C")
                    except (ValueError, TypeError):
                        errores.append("La temperatura mínima debe ser un número")
                
                # Validar temperatura máxima
                temp_maxima = temperatura.get('maxima')
                if temp_maxima is not None:
                    try:
                        temp_maxima = float(temp_maxima)
                        if temp_maxima < -40 or temp_maxima > 70:
                            errores.append("La temperatura máxima debe estar entre -40°C y 70°C")
                    except (ValueError, TypeError):
                        errores.append("La temperatura máxima debe ser un número")
                
                # Validar coherencia entre temperaturas
                if (temp_minima is not None and temp_maxima is not None and 
                    isinstance(temp_minima, (int, float)) and isinstance(temp_maxima, (int, float))):
                    if temp_minima > temp_maxima:
                        errores.append("La temperatura mínima no puede ser mayor que la máxima")
        
        # Validar humedad
        humedad = condiciones.get('humedad')
        if humedad is not None:
            try:
                humedad = int(humedad)
                if humedad < 0 or humedad > 100:
                    errores.append("La humedad debe estar entre 0% y 100%")
            except (ValueError, TypeError):
                errores.append("La humedad debe ser un número entero")
        
        # Validar precipitación
        precipitacion = condiciones.get('precipitacion')
        if precipitacion is not None:
            try:
                precipitacion = float(precipitacion)
                if precipitacion < 0:
                    errores.append("La precipitación no puede ser negativa")
                elif precipitacion > 1000:  # Límite razonable
                    errores.append("La precipitación parece excesivamente alta (>1000mm)")
            except (ValueError, TypeError):
                errores.append("La precipitación debe ser un número")
        
        # Validar estación
        estacion = condiciones.get('estacion')
        if estacion is not None:
            if not isinstance(estacion, str):
                errores.append("La estación debe ser una cadena de texto")
            elif estacion.lower().strip() not in cls.ESTACIONES_VALIDAS:
                estaciones_disponibles = ', '.join(sorted(cls.ESTACIONES_VALIDAS))
                errores.append(
                    f"La estación '{estacion}' no es válida. "
                    f"Estaciones disponibles: {estaciones_disponibles}"
                )
        
        return errores
    
    @classmethod
    def validar_datos_completos(cls, datos: Dict[str, Any]) -> Tuple[List[str], Dict[str, Any]]:
        """Valida todos los datos de una predicción y retorna errores y datos procesados"""
        errores = []
        datos_procesados = {}
        
        # Validar datos básicos
        errores_basicos = cls.validar_datos_basicos(datos)
        errores.extend(errores_basicos)
        
        # Si hay errores básicos, no continuar
        if errores_basicos:
            return errores, datos_procesados
        
        # Procesar datos básicos
        datos_procesados['especie'] = datos['especie'].lower().strip()
        datos_procesados['clima'] = datos.get('clima', '').lower().strip() if datos.get('clima') else None
        datos_procesados['ubicacion'] = datos.get('ubicacion', '').lower().strip() if datos.get('ubicacion') else None
        
        # Validar y procesar fechas
        try:
            fecha_polinizacion = cls.validar_fecha(datos.get('fecha_polinizacion'), 'fecha de polinización')
            fecha_maduracion = cls.validar_fecha(datos.get('fecha_maduracion'), 'fecha de maduración')
            
            # Validar relación entre fechas
            cls.validar_fechas_relacionadas(fecha_polinizacion, fecha_maduracion)
            
            datos_procesados['fecha_polinizacion'] = fecha_polinizacion
            datos_procesados['fecha_maduracion'] = fecha_maduracion
            
        except PrediccionValidationError as e:
            errores.append(str(e))
        
        # Validar tipo de polinización
        tipo_polinizacion = datos.get('tipo_polinizacion')
        if tipo_polinizacion:
            try:
                cls.validar_tipo_polinizacion(tipo_polinizacion)
                datos_procesados['tipo_polinizacion'] = tipo_polinizacion.lower().strip()
            except PrediccionValidationError as e:
                errores.append(str(e))
        
        # Validar condiciones climáticas
        condiciones_climaticas = datos.get('condiciones_climaticas')
        if condiciones_climaticas:
            errores_clima = cls.validar_condiciones_climaticas(condiciones_climaticas)
            errores.extend(errores_clima)
            if not errores_clima:
                datos_procesados['condiciones_climaticas'] = condiciones_climaticas
        
        return errores, datos_procesados
    
    @classmethod
    def validar_prediccion_para_validacion(cls, prediccion_data: Dict[str, Any]) -> List[str]:
        """Valida que una predicción tenga los datos necesarios para ser validada"""
        errores = []
        
        if not prediccion_data:
            errores.append("Se requieren los datos de la predicción original")
            return errores
        
        # Verificar campos requeridos para validación
        campos_requeridos = ['dias_estimados', 'parametros_usados']
        for campo in campos_requeridos:
            if campo not in prediccion_data:
                errores.append(f"La predicción debe contener el campo '{campo}'")
        
        # Verificar que tenga fecha de polinización
        parametros_usados = prediccion_data.get('parametros_usados', {})
        if not parametros_usados.get('fecha_polinizacion'):
            errores.append("La predicción debe tener una fecha de polinización para poder ser validada")
        
        # Verificar que los días estimados sean válidos
        dias_estimados = prediccion_data.get('dias_estimados')
        if dias_estimados is not None:
            try:
                dias_estimados = int(dias_estimados)
                if dias_estimados <= 0:
                    errores.append("Los días estimados deben ser un número positivo")
            except (ValueError, TypeError):
                errores.append("Los días estimados deben ser un número válido")
        
        return errores


def validar_datos_prediccion_completa(datos: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función de conveniencia para validar datos completos de predicción
    Lanza PrediccionValidationError si hay errores
    """
    errores, datos_procesados = ValidadorPrediccionPolinizacion.validar_datos_completos(datos)
    
    if errores:
        raise PrediccionValidationError(
            f"Errores de validación: {'; '.join(errores)}",
            code="VALIDACION_FALLIDA",
            params={'errores': errores}
        )
    
    return datos_procesados


def validar_modelo_disponible(ruta_modelo: str) -> None:
    """
    Función de conveniencia para validar disponibilidad del modelo
    """
    ValidadorPrediccionPolinizacion.validar_modelo_disponible(ruta_modelo)