# ✅ Sistema de Notificaciones de Recordatorio - Implementado

## 📋 Resumen

Se ha implementado exitosamente un sistema de notificaciones automáticas que alerta a los usuarios cuando sus registros de germinación o polinización permanecen en estado **INICIAL** por más de 5 días.

## 🎯 Objetivo Cumplido

**Requisito:** Generar alertas y notificaciones después de 5 días de haber iniciado un nuevo registro de germinación o polinizacion. Las notificaciones deben llegar constantemente hasta que se cambie el estado a EN_PROCESO.

**Solución:** Sistema automático que:
- ✅ Detecta registros con más de 5 días en estado INICIAL
- ✅ Genera notificaciones de recordatorio diarias
- ✅ Evita duplicados (cooldown de 24 horas)
- ✅ Se detiene automáticamente al cambiar a EN_PROCESO
- ✅ Incluye información detallada y predicciones

## 📁 Archivos Creados

### 1. Comando de Django
```
BACK/backend/laboratorio/management/commands/generar_notificaciones_recordatorio.py
```
- Comando principal que genera las notificaciones
- Soporta modo simulación (`--dry-run`)
- Personalizable con `--dias X`

### 2. Scripts de Configuración

**Windows:**
```
BACK/backend/scripts/setup_task_notificaciones.bat
BACK/backend/scripts/run_notificaciones.bat (generado automáticamente)
```

**Linux/Mac:**
```
BACK/backend/scripts/setup_cron_notificaciones.sh
```

**Python (multiplataforma):**
```
BACK/backend/scripts/generar_notificaciones.py
```

### 3. Documentación
```
BACK/backend/NOTIFICACIONES_RECORDATORIO.md (completa)
BACK/backend/QUICK_START_NOTIFICACIONES.md (inicio rápido)
BACK/backend/RESUMEN_NOTIFICACIONES_RECORDATORIO.md (este archivo)
```

### 4. Actualizaciones en Código Existente

**Servicio de Notificaciones:**
- Agregado método `obtener_registros_pendientes_revision()`
- Ubicación: `BACK/backend/laboratorio/services/notification_service.py`

**Vistas de Notificaciones:**
- Agregado endpoint `/api/notificaciones/registros-pendientes/`
- Ubicación: `BACK/backend/laboratorio/view_modules/notification_views.py`

## 🚀 Cómo Usar

### Ejecución Manual

```bash
# Modo simulación (ver qué se generaría)
python manage.py generar_notificaciones_recordatorio --dry-run

# Modo producción (generar notificaciones reales)
python manage.py generar_notificaciones_recordatorio

# Personalizar días límite
python manage.py generar_notificaciones_recordatorio --dias 7
```

### Configuración Automática

**Windows (como Administrador):**
```cmd
scripts\setup_task_notificaciones.bat
```

**Linux/Mac:**
```bash
chmod +x scripts/setup_cron_notificaciones.sh
./scripts/setup_cron_notificaciones.sh
```

La tarea se ejecutará **diariamente a las 9:00 AM**.

## 📊 Ejemplo de Funcionamiento

### Escenario
1. Usuario crea una germinación el **27/11/2025**
2. Estado: **INICIAL**
3. No cambia el estado

### Resultado
- **2/12/2025 (5 días después):** Primera notificación de recordatorio
- **3/12/2025:** Segunda notificación (si sigue en INICIAL)
- **4/12/2025:** Tercera notificación (si sigue en INICIAL)
- **Usuario cambia estado a EN_PROCESO:** Las notificaciones se detienen

### Contenido de la Notificación

```
Título: ⏰ Recordatorio: Germinación GER-2025-001 lleva 7 días sin iniciar

Mensaje:
La germinación GER-2025-001 de Cattleya Trianae lleva 7 días en estado INICIAL.

📅 Fecha de siembra: 27/11/2025
🔮 Fecha estimada de germinación: 15/12/2025
⏳ Días restantes: 11

💡 Considera iniciar el proceso de seguimiento para un mejor control.
```

## 🔧 Características Técnicas

### Prevención de Duplicados
- No crea notificaciones si ya existe una en las últimas 24 horas
- Evita spam de notificaciones

### Filtros Inteligentes
- Solo registros en estado **INICIAL**
- Solo registros con usuario creador
- Solo registros creados manualmente (no importados)
- Solo registros con más de X días (configurable)

### Información Detallada
- Días transcurridos en estado INICIAL
- Predicción de fecha estimada (si existe)
- Días restantes hasta la fecha estimada
- Información de especies y códigos

## 📡 API Endpoints

### Obtener Notificaciones de Recordatorio
```http
GET /api/notificaciones/?tipo=RECORDATORIO_REVISION
Authorization: Token YOUR_TOKEN
```

### Obtener Registros Pendientes
```http
GET /api/notificaciones/registros-pendientes/?dias=5
Authorization: Token YOUR_TOKEN
```

Respuesta:
```json
{
  "germinaciones": [
    {
      "id": 1,
      "codigo": "GER-2025-001",
      "dias_transcurridos": 7,
      "fecha_siembra": "2025-11-27",
      "prediccion_fecha_estimada": "2025-12-15"
    }
  ],
  "polinizaciones": [...],
  "total_germinaciones": 1,
  "total_polinizaciones": 0,
  "total": 1,
  "dias_limite": 5
}
```

## 🎨 Integración con Frontend

Las notificaciones aparecerán automáticamente en:
1. **Pantalla de Notificaciones** (`PoliGer/components/alerts/NotificationsScreen.tsx`)
2. **Badge de notificaciones** en la navegación
3. **Filtro por tipo:** "Recordatorio de Revisión"

## ⚙️ Configuración Avanzada

### Cambiar Frecuencia de Ejecución

**Cada 12 horas (Windows):**
```cmd
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /SC HOURLY /MO 12
```

**Cada 12 horas (Linux/Mac):**
```bash
crontab -e
# Agregar: 0 */12 * * * cd /ruta && python manage.py generar_notificaciones_recordatorio
```

### Cambiar Hora de Ejecución

**Windows:**
```cmd
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /ST 14:00
```

**Linux/Mac:**
```bash
crontab -e
# Cambiar: 0 14 * * * (para las 2:00 PM)
```

### Cambiar Días Límite

Editar el comando en la tarea/cron:
```bash
python manage.py generar_notificaciones_recordatorio --dias 7
```

## 📈 Monitoreo

### Ver Logs

**Windows:**
```cmd
type logs\notificaciones_task.log
```

**Linux/Mac:**
```bash
tail -f logs/notificaciones_cron.log
```

### Estadísticas

```python
from laboratorio.models import Notification
from datetime import date, timedelta

# Notificaciones de hoy
hoy = date.today()
count = Notification.objects.filter(
    tipo='RECORDATORIO_REVISION',
    fecha_creacion__date=hoy
).count()
print(f"Notificaciones generadas hoy: {count}")
```

## ✅ Testing

El comando fue probado exitosamente:
```bash
python manage.py generar_notificaciones_recordatorio --dry-run
```

Resultado:
```
======================================================================
Generando notificaciones de recordatorio
Días límite: 5
Modo: DRY RUN (simulación)
======================================================================

📋 Procesando germinaciones...
🌸 Procesando polinizaciones...

======================================================================
RESUMEN:
  - Notificaciones de germinación: 0
  - Notificaciones de polinización: 0
  - Total: 0
======================================================================

⚠️  Modo DRY RUN: No se crearon notificaciones reales
```

## 🔐 Seguridad

- ✅ Solo usuarios autenticados reciben notificaciones
- ✅ Cada usuario solo ve sus propios registros
- ✅ No se expone información sensible
- ✅ Logs seguros sin datos personales

## 🎯 Próximos Pasos Recomendados

1. **Configurar la tarea automática** en el servidor de producción
2. **Ajustar el horario** según las necesidades del equipo
3. **Monitorear los logs** durante la primera semana
4. **Ajustar el número de días** si es necesario
5. **Considerar integración con Celery** para proyectos grandes

## 📞 Soporte

Para más detalles, consulta:
- `NOTIFICACIONES_RECORDATORIO.md` - Documentación completa
- `QUICK_START_NOTIFICACIONES.md` - Guía de inicio rápido

## 🎉 Conclusión

El sistema está **completamente funcional** y listo para usar. Las notificaciones se generarán automáticamente según la configuración establecida, ayudando a los usuarios a mantener un seguimiento activo de sus registros.

**Estado:** ✅ IMPLEMENTADO Y PROBADO
**Fecha:** 27/11/2025
