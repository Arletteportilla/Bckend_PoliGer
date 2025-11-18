# Estructura de Vistas Refactorizada

Este directorio (`view_modules/`) contiene las vistas del laboratorio organizadas de manera modular para mejorar la mantenibilidad y escalabilidad del código.

**Nota**: El directorio se llama `view_modules` en lugar de `views` para evitar conflictos con el archivo `views.py` principal.

## Estructura de Archivos

### `base_views.py`
Contiene las clases base y mixins que proporcionan funcionalidades comunes:
- `BaseServiceViewSet`: ViewSet base que utiliza servicios de negocio
- `OptimizedPagination`: Paginación optimizada
- `ErrorHandlerMixin`: Manejo consistente de errores
- `CacheInvalidationMixin`: Invalidación de cache
- `SearchMixin`: Funcionalidad de búsqueda

### `polinizacion_views.py`
ViewSet especializado para polinizaciones:
- `PolinizacionViewSet`: Gestión completa de polinizaciones
- Utiliza el servicio `polinizacion_service`
- Incluye endpoints específicos como `mis-polinizaciones`, `todas-admin`, etc.
- Generación de PDFs y reportes

### `germinacion_views.py`
ViewSet especializado para germinaciones:
- `GerminacionViewSet`: Gestión completa de germinaciones
- Utiliza el servicio `germinacion_service`
- Incluye endpoints específicos como `mis-germinaciones`, `codigos-unicos`, etc.
- Predicciones y cálculos específicos

### `user_views.py`
ViewSets para gestión de usuarios y perfiles:
- `UserProfileViewSet`: Gestión de perfiles de usuario
- `UserManagementViewSet`: Gestión completa de usuarios (solo admin)
- `UserMetasViewSet`: Gestión de metas de rendimiento
- Control de roles y permisos

### `utils_views.py`
Funciones de utilidad y reportes:
- Generación de reportes Excel y PDF
- Estadísticas de germinaciones y polinizaciones
- Funciones de estilo para Excel
- Reportes con estadísticas completas

### `prediccion_views.py`
Vistas para predicciones y alertas:
- Predicciones de germinación y polinización
- Alertas y notificaciones
- Cambio de estados desde alertas
- Estadísticas de modelos de ML

## Beneficios de la Refactorización

### 1. **Separación de Responsabilidades**
- Cada archivo tiene una responsabilidad específica
- Fácil localización de funcionalidades
- Reducción de acoplamiento

### 2. **Mantenibilidad**
- Archivos más pequeños y manejables
- Código más fácil de leer y entender
- Cambios aislados por funcionalidad

### 3. **Escalabilidad**
- Fácil agregar nuevas funcionalidades
- Estructura preparada para crecimiento
- Reutilización de componentes base

### 4. **Testabilidad**
- Cada módulo puede ser testeado independientemente
- Mocks más específicos y precisos
- Cobertura de pruebas más granular

### 5. **Arquitectura de Servicios**
- Separación entre lógica de negocio (servicios) y presentación (vistas)
- ViewSets más ligeros y enfocados en HTTP
- Servicios reutilizables en diferentes contextos

## Uso de Servicios

Las vistas refactorizadas utilizan servicios de negocio ubicados en `services/`:
- `germinacion_service`: Lógica de negocio para germinaciones
- `polinizacion_service`: Lógica de negocio para polinizaciones
- `prediccion_service`: Cálculos y predicciones
- `base_service`: Funcionalidades comunes

## Compatibilidad

El archivo principal `views.py` mantiene:
- Importaciones de las vistas refactorizadas
- ViewSets básicos para modelos simples
- Funciones legacy para compatibilidad
- Referencias a las nuevas ubicaciones

## Migración

Para migrar código existente:

1. **Importaciones**: Actualizar imports para usar las nuevas ubicaciones
2. **Herencia**: Usar `BaseServiceViewSet` para nuevos ViewSets
3. **Servicios**: Mover lógica de negocio a servicios apropiados
4. **Mixins**: Utilizar mixins para funcionalidades comunes

## Ejemplo de Uso

```python
# Antes
from .views import PolinizacionViewSet

# Después
from .view_modules.polinizacion_views import PolinizacionViewSet
# o
from .views import PolinizacionViewSet  # Funciona por compatibilidad
```

## Próximos Pasos

1. **Tests**: Crear tests específicos para cada módulo
2. **Documentación API**: Actualizar documentación de endpoints
3. **Optimizaciones**: Implementar caching y optimizaciones específicas
4. **Monitoreo**: Agregar logging y métricas por módulo