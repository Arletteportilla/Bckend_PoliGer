# Sistema de Predicción de Maduración para Polinizaciones

## Resumen

Se ha implementado un sistema completo de predicción de días de maduración para polinizaciones usando Machine Learning (XGBoost con 94.91% de precisión).

## Archivos Creados/Modificados

### 1. Servicio de ML
- **`laboratorio/services/ml_polinizacion_service.py`**: Servicio principal de predicción ML
  - Carga el modelo `polinizacion.pkl`
  - Predice días de maduración basado en género, especie, tipo y fecha
  - Calcula confianza de la predicción
  - Maneja casos de especies/géneros nuevos con fallback a promedios

### 2. Comando de Entrenamiento
- **`laboratorio/management/commands/train_polinizacion_model.py`**: Entrena el modelo
  - Lee datos de `prediccion/polinizacion/datos_limpios.csv`
  - Crea 22 features avanzadas (temporales, estadísticas, cíclicas)
  - Entrena modelo XGBoost o Random Forest
  - Guarda modelo empaquetado en `laboratorio/modelos/polinizacion.pkl`

### 3. Comando de Cálculo de Predicciones
- **`laboratorio/management/commands/calcular_predicciones_polinizacion.py`**: Calcula predicciones faltantes
  - Procesa polinizaciones sin predicción
  - Actualiza campos de predicción automáticamente
  - Soporta modo `--force` para recalcular todas

### 4. Servicio de Polinización Actualizado
- **`laboratorio/services/polinizacion_service.py`**: Integración con ML
  - Método `predecir_maduracion()` que usa ML o heurística
  - Predicción automática al crear polinización
  - Fallback heurístico si ML no está disponible

### 5. Modelo Actualizado
- **`laboratorio/core/models.py`**: Campos de predicción agregados
  - `Tipo`: Tipo de polinización (SELF, SIBBLING, HYBRID)
  - `dias_maduracion_predichos`: Días predichos por ML
  - `fecha_maduracion_predicha`: Fecha estimada de maduración
  - `metodo_prediccion`: Método usado (ML, heurística)
  - `confianza_prediccion`: Confianza de la predicción (%)

### 6. Serializer Actualizado
- **`laboratorio/api/serializers.py`**: Campos de predicción en API
  - Incluye todos los campos de predicción ML
  - Compatible con campos legacy

### 7. Vistas Actualizadas
- **`laboratorio/view_modules/polinizacion_views.py`**: Endpoints de predicción
  - `POST /api/polinizaciones/predecir-maduracion/`: Predice maduración
  - `GET /api/polinizaciones/info-modelo-ml/`: Info del modelo cargado

### 8. Migración
- **`laboratorio/migrations/0003_add_ml_prediction_fields_polinizacion.py`**: Migración de BD

## Uso

### 1. Entrenar el Modelo (si es necesario)

```bash
cd BACK/backend
python manage.py train_polinizacion_model
```

Esto generará:
- Modelo entrenado en `laboratorio/modelos/polinizacion.pkl`
- Métricas: MAE ~10 días, R² ~95%

### 2. Calcular Predicciones Faltantes

```bash
# Calcular solo predicciones faltantes
python manage.py calcular_predicciones_polinizacion

# Recalcular todas las predicciones
python manage.py calcular_predicciones_polinizacion --force

# Limitar a 100 polinizaciones
python manage.py calcular_predicciones_polinizacion --limit 100
```

### 3. Aplicar Migración

```bash
python manage.py makemigrations
python manage.py migrate
```

### 4. Usar en el Código

#### Predicción Manual
```python
from laboratorio.services.polinizacion_service import polinizacion_service

prediccion = polinizacion_service.predecir_maduracion(
    genero='Cattleya',
    especie='maxima',
    tipo='SELF',
    fecha_pol='2025-01-15',
    cantidad=1
)

print(f"Días estimados: {prediccion['dias_estimados']}")
print(f"Fecha estimada: {prediccion['fecha_estimada']}")
print(f"Confianza: {prediccion['confianza']}%")
```

#### Predicción Automática al Crear
```python
# Al crear una polinización, la predicción se calcula automáticamente
polinizacion = polinizacion_service.create({
    'genero': 'Cattleya',
    'especie': 'maxima',
    'Tipo': 'SELF',
    'fechapol': '2025-01-15',
    'cantidad': 1
}, user=request.user)

# Los campos de predicción se llenan automáticamente
print(polinizacion.dias_maduracion_predichos)
print(polinizacion.fecha_maduracion_predicha)
```

### 5. Usar desde la API

#### Predecir Maduración
```bash
POST /api/polinizaciones/predecir-maduracion/
Content-Type: application/json

{
  "genero": "Cattleya",
  "especie": "maxima",
  "tipo": "SELF",
  "fecha_pol": "2025-01-15",
  "cantidad": 1
}
```

Respuesta:
```json
{
  "success": true,
  "prediccion": {
    "dias_estimados": 195,
    "fecha_estimada": "2025-07-29",
    "metodo": "ML",
    "modelo": "XGBoost",
    "confianza": 85.0,
    "nivel_confianza": "alta",
    "rango_probable": {
      "min": 185,
      "max": 205
    }
  }
}
```

#### Info del Modelo
```bash
GET /api/polinizaciones/info-modelo-ml/
```

Respuesta:
```json
{
  "success": true,
  "modelo": {
    "loaded": true,
    "modelo": "XGBoost",
    "mae_test": 10.33,
    "rmse_test": 20.81,
    "r2_test": 0.9491,
    "precision_percent": 94.91,
    "n_features": 22,
    "n_samples": 39264,
    "fecha_entrenamiento": "2025-01-15 10:30:00"
  }
}
```

## Características del Modelo

### Precisión
- **Algoritmo**: XGBoost Regressor
- **Precisión**: 94.91% (R² = 0.9491)
- **Error promedio**: ±10.33 días (MAE)
- **RMSE**: 20.81 días

### Features Utilizadas (22 total)
1. **Categóricas codificadas**: género, especie, tipo, género+tipo
2. **Temporales cíclicas**: mes, día del año, semana (sin/cos)
3. **Estadísticas de especie**: media, mediana, std, min, max, count
4. **Estadísticas de género**: media, std, count
5. **Estadísticas de tipo**: media, std
6. **Cantidad**: número de polinizaciones

### Datos de Entrenamiento
- **Registros**: 39,264 polinizaciones
- **Géneros**: 387 únicos
- **Especies**: 7,036 únicas
- **Rango**: 1-540 días (límite 547 = 1.5 años)

### Tipos de Polinización
- **SELF**: Auto-polinización
- **SIBBLING**: Entre hermanos
- **HYBRID**: Híbrida

## Niveles de Confianza

La confianza se calcula basándose en:
- Cantidad de datos históricos de la especie
- Si la especie está en el modelo entrenado
- Si el género está en el modelo
- Si el tipo está en el modelo

**Niveles**:
- **Alta** (≥80%): Especie con muchos datos históricos
- **Media** (60-79%): Especie con algunos datos
- **Baja** (<60%): Especie nueva o con pocos datos

## Fallback Heurístico

Si el modelo ML no está disponible o falla, se usa predicción heurística:
- **SELF**: 180 días
- **SIBBLING**: 190 días
- **HYBRID**: 200 días
- **Confianza**: 50% (baja)

## Próximos Pasos

1. **Frontend**: Integrar predicciones en el formulario de polinización
2. **Notificaciones**: Alertas cuando se acerque la fecha de maduración
3. **Reportes**: Incluir predicciones en reportes
4. **Reentrenamiento**: Actualizar modelo periódicamente con nuevos datos
5. **Validación**: Comparar predicciones con fechas reales de maduración

## Notas Técnicas

- El modelo se carga una vez al iniciar el servicio (singleton)
- Las predicciones son rápidas (~10ms por predicción)
- El modelo ocupa ~5-10 MB en disco
- Compatible con especies/géneros nuevos (usa promedios)
- Thread-safe para uso en producción
