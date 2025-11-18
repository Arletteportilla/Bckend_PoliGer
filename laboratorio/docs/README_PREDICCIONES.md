# Sistema de Predicciones - PoliGer

Este módulo proporciona funcionalidades de predicción para el sistema PoliGer, permitiendo predecir fechas de germinación y polinización basándose en modelos de machine learning y reglas heurísticas.

## 📁 Archivos del Sistema

- `predicciones.py` - Módulo principal con todas las funciones de predicción
- `ejemplo_predicciones.py` - Ejemplos de uso del sistema
- `README_PREDICCIONES.md` - Esta documentación
- `modelos/` - Directorio con los modelos entrenados (.bin)

## 🚀 Funciones Principales

### 1. `cargar_modelo(modelo_path)`
Carga un modelo de machine learning desde un archivo .bin

**Parámetros:**
- `modelo_path` (str): Ruta al archivo del modelo (por defecto: './modelos/germinacion.bin')

**Retorna:**
- Modelo cargado o `None` si hay error

### 2. `predecir_fecha_germinacion(...)`
Predice la fecha de germinación basada en múltiples parámetros

**Parámetros:**
- `especie` (str): Nombre de la especie
- `genero` (str): Nombre del género
- `clima` (str): Condiciones climáticas
- `fecha_siembra` (date): Fecha de siembra
- `fecha_germinacion` (date, opcional): Fecha de germinación para validación
- `fecha_ingreso` (date, opcional): Fecha de ingreso
- `fecha_polinizacion` (date, opcional): Fecha de polinización
- `**kwargs`: Parámetros adicionales

**Retorna:**
```python
{
    'prediccion': date,           # Fecha predicha
    'confianza': float,           # Nivel de confianza (0-1)
    'dias_estimados': int,        # Días estimados
    'modelo_usado': str,          # Nombre del modelo usado
    'parametros_entrada': dict    # Parámetros de entrada
}
```

### 3. `predecir_fecha_polinizacion(...)`
Predice la fecha óptima de polinización

**Parámetros:**
- `especie` (str): Nombre de la especie
- `genero` (str): Nombre del género
- `clima` (str): Condiciones climáticas
- `fecha_actual` (date, opcional): Fecha actual (por defecto: hoy)
- `**kwargs`: Parámetros adicionales

**Retorna:**
```python
{
    'prediccion': date,           # Fecha predicha
    'tipo': str,                  # Tipo de predicción
    'dias_estimados': int,        # Días estimados (si aplica)
    'confianza': float,           # Nivel de confianza (si aplica)
    'modelo_usado': str           # Nombre del modelo usado (si aplica)
}
```

### 4. `obtener_estadisticas_modelo()`
Obtiene información sobre los modelos disponibles

**Retorna:**
```python
{
    'germinacion': {
        'disponible': bool,
        'tipo': str,
        'tamaño_archivo': str
    },
    'polinizacion': {
        'disponible': bool,
        'tipo': str,
        'tamaño_archivo': str
    }
}
```

## 🔧 Funciones Auxiliares

### `preparar_datos_entrada(...)`
Prepara los datos de entrada para el modelo de predicción

### `procesar_prediccion(prediccion, fecha_siembra)`
Procesa la predicción del modelo y la convierte a fecha

### `calcular_dias_estimados(fecha_inicio, fecha_fin)`
Calcula los días estimados entre dos fechas

### `predecir_polinizacion_heuristica(...)`
Predicción heurística basada en reglas del dominio

## 📊 Tipos de Predicción

### 1. Predicción de Germinación
- **Modelo ML**: Usa el archivo `germinacion.bin`
- **Entrada**: Especie, género, clima, fechas relevantes
- **Salida**: Fecha predicha de germinación con confianza

### 2. Predicción de Polinización
- **Modelo ML**: Usa el archivo `polinizacion.bin` (si existe)
- **Fallback**: Reglas heurísticas basadas en género y clima
- **Salida**: Fecha óptima de polinización

## 🎯 Reglas Heurísticas

### Géneros y Tiempos Estimados
- **Phalaenopsis**: 60 días
- **Cattleya**: 90 días
- **Dendrobium**: 75 días
- **Oncidium**: 80 días
- **Vanda**: 70 días

### Ajustes por Clima
- **Templado**: +10 días
- **Frío**: +20 días
- **Cálido**: -10 días

## 💻 Ejemplo de Uso

```python
from datetime import date
from predicciones import predecir_fecha_germinacion

# Predicción de germinación
resultado = predecir_fecha_germinacion(
    especie="Phalaenopsis",
    genero="Phalaenopsis",
    clima="Templado",
    fecha_siembra=date(2024, 1, 15),
    fecha_polinizacion=date(2023, 12, 1)
)

if 'error' not in resultado:
    print(f"Fecha predicha: {resultado['prediccion']}")
    print(f"Confianza: {resultado['confianza']:.2%}")
    print(f"Días estimados: {resultado['dias_estimados']}")
else:
    print(f"Error: {resultado['error']}")
```

## 🏃‍♂️ Ejecutar Ejemplos

Para ejecutar los ejemplos incluidos:

```bash
cd BACK/backend/laboratorio
python ejemplo_predicciones.py
```

## 📋 Requisitos

### Dependencias Python
```python
import joblib
import numpy as np
import pandas as pd
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import os
```

### Archivos de Modelo
- `./modelos/germinacion.bin` - Modelo de predicción de germinación
- `./modelos/polinizacion.bin` - Modelo de predicción de polinización (opcional)

## ⚠️ Manejo de Errores

El sistema maneja los siguientes errores:

1. **Modelo no encontrado**: Retorna predicción heurística o error
2. **Error de carga**: Informa el problema específico
3. **Datos inválidos**: Valida parámetros antes de procesar
4. **Predicción fallida**: Proporciona valores por defecto

## 🔄 Integración con Django

Para integrar con las vistas de Django:

```python
from .predicciones import predecir_fecha_germinacion

def vista_prediccion(request):
    # Obtener datos del request
    especie = request.POST.get('especie')
    genero = request.POST.get('genero')
    # ... otros campos
    
    # Realizar predicción
    resultado = predecir_fecha_germinacion(
        especie=especie,
        genero=genero,
        # ... otros parámetros
    )
    
    return JsonResponse(resultado)
```

## 📈 Mejoras Futuras

1. **Más modelos**: Agregar modelos para otras predicciones
2. **Validación cruzada**: Implementar validación de modelos
3. **Métricas**: Agregar métricas de rendimiento
4. **Caché**: Implementar caché para predicciones frecuentes
5. **API REST**: Crear endpoints específicos para predicciones

## 🐛 Solución de Problemas

### Error: "Modelo no encontrado"
- Verificar que los archivos .bin estén en `./modelos/`
- Verificar permisos de lectura

### Error: "Error al cargar el modelo"
- Verificar que el archivo no esté corrupto
- Verificar versión de joblib compatible

### Predicciones incorrectas
- Verificar formato de datos de entrada
- Revisar que las fechas estén en formato correcto
- Verificar que el modelo esté entrenado con datos similares

## 📞 Soporte

Para problemas o preguntas sobre el sistema de predicciones:
1. Revisar los ejemplos en `ejemplo_predicciones.py`
2. Verificar la documentación de las funciones
3. Revisar los logs de error para detalles específicos 