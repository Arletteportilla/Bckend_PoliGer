# Tests de Predicciones de Polinización

Este documento describe los tests unitarios implementados para el sistema de predicciones de polinización basado en archivo .bin.

## Archivos de Tests

### 1. `test_predicciones_polinizacion.py`
Tests unitarios principales para todas las funciones del módulo `predicciones_polinizaciones.py`:

#### Clases de Test:
- **CargarModeloPolinizacionTest**: Tests para la carga del modelo .bin
- **GenerarCacheKeyPolinizacionTest**: Tests para generación de claves de cache
- **ObtenerParametrosEspeciePolinizacionTest**: Tests para parámetros de especies
- **PrediccionPolinizacionInicialTest**: Tests para predicción inicial
- **RefinarPrediccionPolinizacionTest**: Tests para refinamiento progresivo
- **ValidarPrediccionPolinizacionTest**: Tests para validación con fechas reales
- **ExcepcionesTest**: Tests para excepciones personalizadas
- **IntegracionTest**: Tests de integración del flujo completo

### 2. `test_views.py` (extensión)
Tests para los endpoints API de predicciones de polinización:

#### Clases de Test Agregadas:
- **PrediccionPolinizacionAPITest**: Tests de endpoints API
- **PrediccionPolinizacionPerformanceTest**: Tests de rendimiento
- **PrediccionPolinizacionIntegrationTest**: Tests de integración API

### 3. `test_config_polinizacion.py`
Configuración y utilidades para tests:

#### Componentes:
- **PolinizacionTestMixin**: Mixin con utilidades comunes
- **PolinizacionTestData**: Datos de prueba
- **MockModeloPolinizacion**: Mock del modelo ML
- **Decoradores**: Para manejo de modelos y cache

### 4. `run_polinizacion_tests.py`
Script ejecutor específico para tests de polinización con reporte detallado.

## Cobertura de Requirements

Los tests cubren todos los requirements especificados en la tarea:

### Requirement 1.1 - Carga automática del archivo .bin
- ✅ `test_carga_modelo_exitosa`: Verifica carga correcta
- ✅ `test_cache_modelo`: Verifica sistema de cache
- ✅ `test_prediccion_inicial_exitosa`: Verifica uso del modelo

### Requirement 1.2 - Manejo de errores de archivo corrupto/inexistente
- ✅ `test_modelo_no_encontrado`: Archivo no existe
- ✅ `test_modelo_corrupto`: Archivo corrupto
- ✅ `test_error_carga_joblib`: Error en carga
- ✅ `test_modelo_none`: Modelo inválido

### Requirement 3.4 - Actualización en tiempo real de predicciones
- ✅ `test_refinamiento_con_fecha_polinizacion`: Refinamiento con fecha
- ✅ `test_refinamiento_con_condiciones_climaticas`: Refinamiento con clima
- ✅ `test_refinamiento_con_tipo_polinizacion`: Refinamiento con tipo
- ✅ `test_refinar_prediccion_exitosa`: API de refinamiento

### Requirement 5.3 - Comparación con resultados reales
- ✅ `test_validacion_exitosa`: Validación básica
- ✅ `test_validacion_prediccion_exacta`: Predicción exacta
- ✅ `test_calidad_prediccion_excelente`: Clasificación de calidad
- ✅ `test_calidad_prediccion_pobre`: Clasificación pobre

### Requirement 5.4 - Uso de información para mejorar predicciones
- ✅ `test_validacion_exitosa`: Cálculo de precisión
- ✅ `test_flujo_completo_prediccion`: Flujo completo de mejora
- ✅ `test_flujo_completo_api`: Integración API completa

## Tipos de Tests Implementados

### 1. Tests Unitarios
- **Funciones individuales**: Cada función tiene tests específicos
- **Manejo de errores**: Tests para todos los casos de error
- **Validaciones**: Tests para validación de datos
- **Cache**: Tests para sistema de cache

### 2. Tests de Integración
- **Flujo completo**: Inicial → Refinada → Validada
- **API endpoints**: Tests de todos los endpoints
- **Interacción entre componentes**: Tests de integración

### 3. Tests de Rendimiento
- **Tiempo de respuesta**: Verificación de tiempos
- **Requests concurrentes**: Manejo de múltiples requests
- **Cache performance**: Eficiencia del cache

### 4. Tests de API
- **Endpoints individuales**: Cada endpoint tiene tests
- **Autenticación**: Tests de seguridad
- **Formatos de datos**: Validación de entrada/salida
- **Códigos de estado**: Verificación de responses

## Cómo Ejecutar los Tests

### Opción 1: Script Específico (Recomendado)
```bash
cd BACK/backend
python laboratorio/tests/run_polinizacion_tests.py
```

### Opción 2: Django Test Runner
```bash
cd BACK/backend

# Todos los tests de polinización
python manage.py test laboratorio.tests.test_predicciones_polinizacion --verbosity=2

# Tests específicos
python manage.py test laboratorio.tests.test_predicciones_polinizacion.CargarModeloPolinizacionTest --verbosity=2

# Tests de API
python manage.py test laboratorio.tests.test_views.PrediccionPolinizacionAPITest --verbosity=2
```

### Opción 3: Tests Individuales
```bash
# Test de carga del modelo
python manage.py test laboratorio.tests.test_predicciones_polinizacion.CargarModeloPolinizacionTest.test_carga_modelo_exitosa --verbosity=2

# Test de predicción inicial
python manage.py test laboratorio.tests.test_predicciones_polinizacion.PrediccionPolinizacionInicialTest.test_prediccion_inicial_exitosa --verbosity=2

# Test de refinamiento
python manage.py test laboratorio.tests.test_predicciones_polinizacion.RefinarPrediccionPolinizacionTest.test_refinamiento_con_fecha_polinizacion --verbosity=2
```

## Coverage Report

Para generar reporte de cobertura:

```bash
cd BACK/backend

# Coverage específico para polinización
coverage run --source='laboratorio.predicciones_polinizaciones' manage.py test laboratorio.tests.test_predicciones_polinizacion

# Reporte en terminal
coverage report --show-missing --include='*predicciones_polinizaciones*'

# Reporte HTML
coverage html --include='*predicciones_polinizaciones*'
```

## Estructura de Tests

### Patrón de Naming
- `test_[funcionalidad]_[escenario]`: Nombre descriptivo
- `setUp()`: Configuración antes de cada test
- `tearDown()`: Limpieza después de cada test

### Mocks y Fixtures
- **Modelo ML**: Mock del modelo de machine learning
- **Cache**: Mock del sistema de cache de Django
- **Validadores**: Mock de validaciones
- **Datos de prueba**: Fixtures con datos consistentes

### Assertions Principales
- `assertEqual()`: Verificar valores exactos
- `assertIn()`: Verificar presencia de elementos
- `assertGreater()`: Verificar rangos numéricos
- `assertRaises()`: Verificar excepciones
- `assertTrue()/assertFalse()`: Verificar booleanos

## Casos de Test Críticos

### 1. Carga del Modelo
- ✅ Carga exitosa con cache
- ✅ Archivo no encontrado
- ✅ Archivo corrupto
- ✅ Error de joblib

### 2. Predicción Inicial
- ✅ Predicción con datos mínimos
- ✅ Uso de cache
- ✅ Datos insuficientes
- ✅ Parámetros de especies

### 3. Refinamiento Progresivo
- ✅ Refinamiento con fecha de polinización
- ✅ Refinamiento con condiciones climáticas
- ✅ Refinamiento con tipo de polinización
- ✅ Mejora de confianza

### 4. Validación
- ✅ Validación exitosa
- ✅ Cálculo de precisión
- ✅ Clasificación de calidad
- ✅ Análisis de desviación

### 5. API Endpoints
- ✅ Todos los endpoints funcionan
- ✅ Autenticación requerida
- ✅ Manejo de errores HTTP
- ✅ Formatos de respuesta correctos

## Métricas de Calidad

### Cobertura Esperada
- **Funciones**: 100% de las funciones principales
- **Líneas**: >95% de cobertura de código
- **Branches**: >90% de ramas de decisión
- **Excepciones**: 100% de excepciones personalizadas

### Performance Esperada
- **Tiempo de respuesta**: <2 segundos por endpoint
- **Requests concurrentes**: Manejo de 5+ requests simultáneos
- **Cache hit rate**: >80% para predicciones repetidas

## Troubleshooting

### Problemas Comunes

1. **Error de migración de BD**:
   ```bash
   python manage.py migrate --run-syncdb
   ```

2. **Modelo .bin no encontrado**:
   - Los tests usan mocks, no requieren archivo real
   - Verificar que los mocks estén configurados

3. **Error de importación**:
   ```bash
   export DJANGO_SETTINGS_MODULE=backend.settings
   ```

4. **Tests lentos**:
   - Usar `--keepdb` para mantener BD de test
   - Ejecutar tests específicos en lugar de suite completa

### Debug de Tests

Para debug detallado:
```bash
python manage.py test laboratorio.tests.test_predicciones_polinizacion --verbosity=3 --debug-mode
```

## Mantenimiento

### Agregar Nuevos Tests
1. Seguir el patrón de naming existente
2. Usar los mixins y utilidades de `test_config_polinizacion.py`
3. Agregar al script `run_polinizacion_tests.py`
4. Actualizar este README

### Actualizar Tests Existentes
1. Mantener compatibilidad con tests existentes
2. Actualizar mocks si cambian las interfaces
3. Verificar que coverage se mantenga alto
4. Ejecutar suite completa antes de commit

---

**Nota**: Estos tests están diseñados para ejecutarse independientemente del archivo .bin real, usando mocks para simular el comportamiento del modelo ML. Esto garantiza que los tests sean rápidos, confiables y no dependan de archivos externos.