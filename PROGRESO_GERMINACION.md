# 📊 Sistema de Progreso de Germinación

## 🎯 Descripción

Se ha agregado un campo de **progreso** (0-100%) que está sincronizado con el estado de germinación. El progreso y el estado se actualizan automáticamente según las siguientes reglas:

### Reglas de Sincronización

| Progreso | Estado | Comportamiento |
|----------|--------|----------------|
| **0%** | INICIAL | Germinación recién creada |
| **1-99%** | EN_PROCESO | Germinación en curso (ej: 60% = en proceso) |
| **100%** | FINALIZADO | Germinación completada + fecha registrada |

---

## 🔄 Funcionamiento

### Actualizar por Progreso (Recomendado)
Cuando actualizas el **progreso**, el **estado** se calcula automáticamente:

```bash
POST /api/germinaciones/{id}/cambiar-estado/
{
  "progreso": 60
}
```

**Resultado:**
- `progreso_germinacion`: 60%
- `estado_germinacion`: EN_PROCESO (automático)

### Actualizar por Estado
Cuando actualizas el **estado**, el **progreso** se ajusta automáticamente:

```bash
POST /api/germinaciones/{id}/cambiar-estado/
{
  "estado": "EN_PROCESO"
}
```

**Resultado:**
- `estado_germinacion`: EN_PROCESO
- `progreso_germinacion`: 50% (automático)

---

## 📝 Ejemplos de Uso

### Frontend (TypeScript)

```typescript
import { germinacionService } from '@/services/germinacion.service';

// Actualizar progreso a 60% (estado se actualiza a EN_PROCESO automáticamente)
await germinacionService.actualizarProgresoGerminacion(123, 60);

// Actualizar progreso a 100% (estado se actualiza a FINALIZADO + fecha)
await germinacionService.actualizarProgresoGerminacion(123, 100);

// O actualizar estado directamente
await germinacionService.cambiarEstadoGerminacion(123, 'EN_PROCESO');
```

### Backend (Python)

```python
from laboratorio.models import Germinacion

germinacion = Germinacion.objects.get(id=123)

# Actualizar progreso (estado se calcula automáticamente)
germinacion.progreso_germinacion = 60
germinacion.actualizar_estado_por_progreso()
germinacion.save()

# Resultado:
# - progreso_germinacion: 60
# - estado_germinacion: 'EN_PROCESO'
```

---

## 🎨 Botones de Acción Rápida (Notificaciones)

En la pantalla de notificaciones, ahora hay 3 botones:

1. **25% Progreso** (Naranja)
   - Actualiza a 25%
   - Estado: INICIAL → EN_PROCESO

2. **60% Progreso** (Azul)
   - Actualiza a 60%
   - Estado: EN_PROCESO

3. **100% Finalizado** (Verde)
   - Actualiza a 100%
   - Estado: FINALIZADO
   - Registra fecha de germinación

---

## 🔧 Campos del Modelo

### Nuevo Campo

```python
progreso_germinacion = models.PositiveIntegerField(
    default=0,
    verbose_name='Progreso de Germinación (%)',
    help_text='Porcentaje de progreso de la germinación (0-100%)'
)
```

### Método Nuevo

```python
def actualizar_estado_por_progreso(self):
    """Actualiza el estado de germinación basado en el progreso"""
    if self.progreso_germinacion == 0:
        self.estado_germinacion = 'INICIAL'
    elif self.progreso_germinacion >= 100:
        self.estado_germinacion = 'FINALIZADO'
        if not self.fecha_germinacion:
            self.fecha_germinacion = timezone.now().date()
    else:
        self.estado_germinacion = 'EN_PROCESO'
```

---

## 📊 Endpoint Actualizado

### POST `/api/germinaciones/{id}/cambiar-estado/`

**Opción 1: Actualizar por Progreso**
```json
{
  "progreso": 60
}
```

**Opción 2: Actualizar por Estado**
```json
{
  "estado": "EN_PROCESO"
}
```

**Respuesta:**
```json
{
  "message": "Estado actualizado de INICIAL a EN_PROCESO (Progreso: 60%)",
  "germinacion": {
    "id": 123,
    "codigo": "ABC-001",
    "estado_germinacion": "EN_PROCESO",
    "progreso_germinacion": 60,
    ...
  }
}
```

---

## 🚀 Migración

### Aplicar Migración

```bash
cd BACK/backend
python manage.py migrate laboratorio
```

### Actualizar Registros Existentes

```bash
python actualizar_progreso_germinacion.py
```

**Resultado:**
- FINALIZADO → 100%
- EN_PROCESO → 50%
- INICIAL → 0%

---

## 📈 Casos de Uso

### Caso 1: Seguimiento Gradual
```typescript
// Día 1: Siembra
await germinacionService.actualizarProgresoGerminacion(123, 10);
// Estado: EN_PROCESO, Progreso: 10%

// Día 5: Primeros brotes
await germinacionService.actualizarProgresoGerminacion(123, 30);
// Estado: EN_PROCESO, Progreso: 30%

// Día 10: Crecimiento visible
await germinacionService.actualizarProgresoGerminacion(123, 60);
// Estado: EN_PROCESO, Progreso: 60%

// Día 15: Germinación completa
await germinacionService.actualizarProgresoGerminacion(123, 100);
// Estado: FINALIZADO, Progreso: 100%, fecha_germinacion: HOY
```

### Caso 2: Cambio Rápido de Estado
```typescript
// Marcar como finalizado directamente
await germinacionService.cambiarEstadoGerminacion(123, 'FINALIZADO');
// Estado: FINALIZADO, Progreso: 100%, fecha_germinacion: HOY
```

---

## ✅ Validaciones

1. **Progreso entre 0-100:**
   - Si < 0 → se ajusta a 0
   - Si > 100 → se ajusta a 100

2. **Estado válido:**
   - Solo acepta: INICIAL, EN_PROCESO, FINALIZADO

3. **Fecha automática:**
   - Al llegar a 100% o FINALIZADO, se registra `fecha_germinacion`

---

## 🔍 Verificación

### 1. Verificar en Admin
```
http://localhost:8000/admin/laboratorio/germinacion/
```
Debe aparecer el campo "Progreso de Germinación (%)"

### 2. Probar Endpoint
```bash
# Actualizar progreso a 60%
curl -X POST http://localhost:8000/api/germinaciones/1/cambiar-estado/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"progreso": 60}'

# Verificar respuesta
# estado_germinacion: "EN_PROCESO"
# progreso_germinacion: 60
```

### 3. Verificar en Frontend
1. Abrir notificaciones
2. Seleccionar una notificación de germinación
3. Usar botones de progreso (25%, 60%, 100%)
4. Verificar que el estado cambia automáticamente

---

## 📊 Estadísticas Actuales

```
Total de germinaciones: 17,660
├─ FINALIZADO (100%): 3,937
├─ EN_PROCESO (50%): 13,723
└─ INICIAL (0%): 0
```

---

## 🎯 Ventajas

✅ **Más preciso:** Progreso numérico en lugar de solo 3 estados  
✅ **Automático:** Estado se calcula según progreso  
✅ **Flexible:** Puedes actualizar por progreso o por estado  
✅ **Visual:** Fácil de mostrar en barras de progreso  
✅ **Histórico:** Se mantiene compatibilidad con datos antiguos  

---

## 📚 Referencias

- **Modelo:** `BACK/backend/laboratorio/core/models.py`
- **Vista:** `BACK/backend/laboratorio/view_modules/germinacion_views.py`
- **Servicio Frontend:** `PoliGer/services/germinacion.service.ts`
- **Componente:** `PoliGer/components/alerts/NotificationsScreen.tsx`
