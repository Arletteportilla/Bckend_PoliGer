# Sistema de Notificaciones de Recordatorio

## Descripción

Este sistema genera notificaciones automáticas de recordatorio para germinaciones y polinizaciones que permanecen en estado **INICIAL** por más de 5 días.

## Características

- ✅ Detecta registros en estado INICIAL con más de 5 días de antigüedad
- ✅ Genera notificaciones de recordatorio automáticas
- ✅ Evita duplicados (no crea notificaciones si ya existe una en las últimas 24 horas)
- ✅ Incluye información detallada: días transcurridos, predicciones, etc.
- ✅ Se ejecuta diariamente de forma automática

## Funcionamiento

### Criterios de Notificación

**Para Germinaciones:**
- Estado: `INICIAL`
- Fecha de siembra: Hace 5 o más días
- Usuario creador: Debe existir

**Para Polinizaciones:**
- Estado: `INICIAL`
- Fecha de polinización: Hace 5 o más días
- Usuario creador: Debe existir

### Contenido de las Notificaciones

Las notificaciones incluyen:
- 📅 Fecha de creación del registro
- ⏰ Días transcurridos en estado INICIAL
- 🔮 Predicción de fecha estimada (si existe)
- ⏳ Días restantes hasta la fecha estimada
- 💡 Sugerencia de acción

## Instalación y Configuración

### 1. Ejecutar el Comando Manualmente

Puedes probar el comando manualmente antes de configurar la tarea automática:

```bash
# Modo simulación (no crea notificaciones reales)
python manage.py generar_notificaciones_recordatorio --dry-run

# Modo producción (crea notificaciones reales)
python manage.py generar_notificaciones_recordatorio

# Personalizar días límite (ejemplo: 7 días)
python manage.py generar_notificaciones_recordatorio --dias 7
```

### 2. Configurar Tarea Automática

#### En Linux/Mac (Cron)

1. Dar permisos de ejecución al script:
```bash
chmod +x scripts/setup_cron_notificaciones.sh
```

2. Ejecutar el script de configuración:
```bash
./scripts/setup_cron_notificaciones.sh
```

3. El script configurará un cron job que se ejecuta diariamente a las 9:00 AM

#### En Windows (Task Scheduler)

1. Ejecutar como Administrador el archivo:
```
scripts\setup_task_notificaciones.bat
```

2. El script configurará una tarea programada que se ejecuta diariamente a las 9:00 AM

### 3. Verificar Configuración

#### Linux/Mac
```bash
# Ver cron jobs actuales
crontab -l

# Ver logs
tail -f logs/notificaciones_cron.log
```

#### Windows
```cmd
# Ver tarea programada
schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"

# Ejecutar manualmente
schtasks /Run /TN "PoliGer_Notificaciones_Recordatorio"

# Ver logs
type logs\notificaciones_task.log
```

## Personalización

### Cambiar la Hora de Ejecución

#### Linux/Mac
Editar el cron job:
```bash
crontab -e
```

Formato: `minuto hora día mes día_semana comando`
- Ejemplo 1: `0 9 * * *` = Todos los días a las 9:00 AM
- Ejemplo 2: `0 14 * * *` = Todos los días a las 2:00 PM
- Ejemplo 3: `0 9 * * 1-5` = Lunes a viernes a las 9:00 AM

#### Windows
Usar el Programador de Tareas de Windows o ejecutar:
```cmd
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /ST 14:00
```

### Cambiar el Número de Días

Editar el comando en el cron job o tarea programada y agregar `--dias X`:
```bash
python manage.py generar_notificaciones_recordatorio --dias 7
```

### Cambiar la Frecuencia

#### Linux/Mac
Editar el cron job para ejecutar cada 12 horas:
```
0 */12 * * * cd /ruta/proyecto && python manage.py generar_notificaciones_recordatorio
```

#### Windows
Modificar la tarea programada para ejecutar cada 12 horas:
```cmd
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /SC HOURLY /MO 12
```

## Monitoreo

### Ver Notificaciones Generadas

Desde el frontend:
1. Ir a la sección de Notificaciones
2. Filtrar por tipo: "Recordatorio de Revisión"

Desde la API:
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notificaciones/?tipo=RECORDATORIO_REVISION
```

### Ver Logs

Los logs se guardan en:
- Linux/Mac: `logs/notificaciones_cron.log`
- Windows: `logs\notificaciones_task.log`

### Estadísticas

Ver cuántas notificaciones se han generado:
```bash
python manage.py shell
```

```python
from laboratorio.models import Notification
from datetime import date, timedelta

# Notificaciones de recordatorio de hoy
hoy = date.today()
count = Notification.objects.filter(
    tipo='RECORDATORIO_REVISION',
    fecha_creacion__date=hoy
).count()
print(f"Notificaciones generadas hoy: {count}")

# Notificaciones de la última semana
hace_semana = hoy - timedelta(days=7)
count_semana = Notification.objects.filter(
    tipo='RECORDATORIO_REVISION',
    fecha_creacion__date__gte=hace_semana
).count()
print(f"Notificaciones de la última semana: {count_semana}")
```

## Solución de Problemas

### El comando no se ejecuta automáticamente

1. Verificar que la tarea/cron está configurada:
   - Linux/Mac: `crontab -l`
   - Windows: `schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"`

2. Verificar los logs para ver errores

3. Ejecutar manualmente para verificar que funciona:
   ```bash
   python manage.py generar_notificaciones_recordatorio
   ```

### No se generan notificaciones

1. Verificar que existen registros en estado INICIAL con más de 5 días
2. Verificar que los registros tienen usuario creador (`creado_por`)
3. Ejecutar en modo dry-run para ver qué registros se detectan:
   ```bash
   python manage.py generar_notificaciones_recordatorio --dry-run
   ```

### Se generan demasiadas notificaciones

El sistema evita duplicados automáticamente (no crea notificaciones si ya existe una en las últimas 24 horas). Si aún así se generan muchas:

1. Aumentar el número de días límite:
   ```bash
   python manage.py generar_notificaciones_recordatorio --dias 7
   ```

2. Reducir la frecuencia de ejecución (por ejemplo, cada 2 días en lugar de diario)

## Integración con Celery (Opcional)

Para proyectos que ya usan Celery, puedes crear una tarea periódica:

```python
# En laboratorio/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def generar_notificaciones_recordatorio():
    """Tarea Celery para generar notificaciones de recordatorio"""
    call_command('generar_notificaciones_recordatorio')
```

```python
# En backend/celery.py
from celery.schedules import crontab

app.conf.beat_schedule = {
    'generar-notificaciones-recordatorio': {
        'task': 'laboratorio.tasks.generar_notificaciones_recordatorio',
        'schedule': crontab(hour=9, minute=0),  # Diario a las 9:00 AM
    },
}
```

## Ejemplo de Notificación Generada

```
Título: ⏰ Recordatorio: Germinación GER-2025-001 lleva 7 días sin iniciar

Mensaje:
La germinación GER-2025-001 de Cattleya Trianae lleva 7 días en estado INICIAL.

📅 Fecha de siembra: 27/11/2025
🔮 Fecha estimada de germinación: 15/12/2025
⏳ Días restantes: 11

💡 Considera iniciar el proceso de seguimiento para un mejor control.
```

## Notas Importantes

- ⚠️ Las notificaciones se generan **solo para registros en estado INICIAL**
- ⚠️ Una vez que cambias el estado a **EN_PROCESO**, las notificaciones dejan de generarse
- ⚠️ El sistema evita duplicados automáticamente (24 horas de cooldown)
- ⚠️ Los registros importados desde archivos Excel no generan notificaciones (solo los creados manualmente)

## Soporte

Para más información o problemas, contacta al equipo de desarrollo.
