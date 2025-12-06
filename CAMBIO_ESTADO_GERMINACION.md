# Cambio: Sistema de Estados de Germinación

## 📋 Resumen

Se ha implementado un nuevo sistema de estados para las germinaciones, reemplazando el sistema anterior de "estado de cápsula" por un sistema más claro de estados del proceso de germinación.

## 🔄 Cambios Realizados

### Backend

#### 1. Modelo `Germinacion` (models.py)
- **Nuevo campo:** `estado_germinacion`
- **Valores posibles:**
  - `INICIAL`: Germinación recién creada
  - `EN_PROCESO`: Germinación en curso
  - `FINALIZADO`: Germinación completada

#### 2. Nuevo Endpoint
```
POST /api/germinaciones/{id}/cambiar-estado/
```

**Request Body:**
```json
{
  "estado": "EN_PROCESO"  // INICIAL | EN_PROCESO | FINALIZADO
}
```

**Response:**
```json
{
  "message": "Estado actualizado de INICIAL a EN_PROCESO",
  "germinacion": {
    "id": 123,
    "codigo": "ABC-001",
    "estado_germinacion": "EN_PROCESO",
    ...
  }
}
```

**Comportamiento:**
- Al cambiar a `FINALIZADO`, se registra automáticamente `fecha_germinacion` con la fecha actual
- Se crea una notificación automática del cambio de estado

#### 3. Serializer Actualizado
- Se agregó el campo `estado_germinacion` al `GerminacionSerializer`
- El campo se incluye en todas las respuestas de la API

### Frontend

#### 1. Servicio TypeScript (`germinacion.service.ts`)
**Nuevo método:**
```typescript
cambiarEstadoGerminacion: async (
  id: number, 
  estado: 'INICIAL' | 'EN_PROCESO' | 'FINALIZADO'
): Promise<any>
```

#### 2. Componente de Notificaciones (`NotificationsScreen.tsx`)
**Botones de acción rápida actualizados:**
- ❌ Eliminado: "Cápsula Abierta", "Semiabierta"
- ✅ Agregado: "En Proceso", "Finalizado"

#### 3. Tipos TypeScript (`types/index.ts`)
```typescript
interface Germinacion {
  ...
  estado_germinacion?: 'INICIAL' | 'EN_PROCESO' | 'FINALIZADO';
  ...
}
```

## 🚀 Migración de Datos

### Aplicar Migración

```bash
cd BACK/backend
python aplicar_migracion_estado_germinacion.py
```

Este script:
1. Crea y aplica la migración del nuevo campo
2. Actualiza registros existentes:
   - Con `fecha_germinacion` → `FINALIZADO`
   - Con `fecha_siembra` pero sin `fecha_germinacion` → `EN_PROCESO`
   - Resto → `INICIAL`

### Migración Manual (alternativa)

```bash
cd BACK/backend
python manage.py makemigrations
python manage.py migrate
```

Luego actualizar datos:
```python
from laboratorio.models import Germinacion

# Finalizadas
Germinacion.objects.filter(
    fecha_germinacion__isnull=False
).update(estado_germinacion='FINALIZADO')

# En proceso
Germinacion.objects.filter(
    fecha_germinacion__isnull=True,
    fecha_siembra__isnull=False
).update(estado_germinacion='EN_PROCESO')
```

## 📝 Uso

### Desde el Frontend (React Native)

```typescript
import { germinacionService } from '@/services/germinacion.service';

// Cambiar estado a EN_PROCESO
await germinacionService.cambiarEstadoGerminacion(123, 'EN_PROCESO');

// Cambiar estado a FINALIZADO (registra fecha automáticamente)
await germinacionService.cambiarEstadoGerminacion(123, 'FINALIZADO');
```

### Desde Notificaciones

Los usuarios pueden cambiar el estado directamente desde las notificaciones usando los botones de acción rápida:
- **En Proceso**: Marca la germinación como en proceso
- **Finalizado**: Marca como finalizada y registra la fecha

## 🔍 Verificación

### 1. Verificar en Admin de Django
```
http://localhost:8000/admin/laboratorio/germinacion/
```
Debe aparecer el campo "Estado de Germinación"

### 2. Probar Endpoint
```bash
curl -X POST http://localhost:8000/api/germinaciones/1/cambiar-estado/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"estado": "EN_PROCESO"}'
```

### 3. Verificar en Frontend
1. Abrir notificaciones
2. Seleccionar una notificación de germinación
3. Usar botones de acción rápida
4. Verificar que el estado cambia correctamente

## ⚠️ Notas Importantes

1. **Compatibilidad:** El campo `etapa_actual` legacy se mantiene para compatibilidad
2. **Notificaciones:** Se crean automáticamente al cambiar el estado
3. **Fecha de germinación:** Se registra automáticamente al marcar como FINALIZADO
4. **Permisos:** Solo el usuario que creó la germinación puede cambiar su estado (o administradores)

## 🔄 Campos Eliminados/Deprecados

- ❌ `cambiarEstadoCapsula()` - Método eliminado del servicio frontend
- ⚠️ `estado_capsula` - Campo mantenido pero no usado para el flujo principal
- ⚠️ `etapa_actual` - Campo legacy mantenido para compatibilidad

## 📊 Flujo de Estados

```
INICIAL → EN_PROCESO → FINALIZADO
   ↓          ↓            ↓
Creación   Siembra    Germinación
           iniciada   completada
```

## 🐛 Troubleshooting

### Error: "Campo estado_germinacion no existe"
**Solución:** Aplicar migración
```bash
python manage.py migrate laboratorio
```

### Error: "Estado inválido"
**Solución:** Verificar que el estado sea uno de: INICIAL, EN_PROCESO, FINALIZADO

### Notificaciones no se crean
**Solución:** Verificar que los signals estén registrados en `apps.py`:
```python
def ready(self):
    import laboratorio.signals
```

## 📚 Referencias

- Modelo: `BACK/backend/laboratorio/core/models.py`
- Vista: `BACK/backend/laboratorio/view_modules/germinacion_views.py`
- Servicio Frontend: `PoliGer/services/germinacion.service.ts`
- Componente: `PoliGer/components/alerts/NotificationsScreen.tsx`
