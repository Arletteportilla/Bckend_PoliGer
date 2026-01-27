# Sistema de Alertas de Revisión Automáticas

Este sistema genera alertas automáticas para recordar a los usuarios que deben revisar sus polinizaciones y germinaciones cada 10 días.

## Características

- ✅ **Alertas automáticas** cada 10 días después de crear un registro
- ✅ **Notificaciones personalizadas** con información detallada del registro
- ✅ **Cambio de estado** desde las notificaciones
- ✅ **Reprogramación automática** de próximas revisiones
- ✅ **Estados granulares** para seguimiento detallado

## Funcionamiento

### 1. Creación de Registros
Cuando se crea una nueva polinización o germinación:
- Se establece automáticamente `fecha_proxima_revision` = fecha_creacion + 10 días
- Se marca `alerta_revision_enviada = False`

### 2. Generación de Alertas
El comando `generar_alertas_revision` busca registros que:
- Tengan `fecha_proxima_revision <= hoy`
- Tengan `alerta_revision_enviada = False`
- Estén en estados: `INICIAL`, `EN_PROCESO_TEMPRANO`, `EN_PROCESO_AVANZADO`

### 3. Notificaciones
Se crean notificaciones tipo `RECORDATORIO_REVISION` con:
- Información detallada del registro
- Estado y progreso actual
- Días transcurridos desde la creación
- Enlaces para cambiar estado

### 4. Marcar como Revisado
Los usuarios pueden:
- Cambiar el estado del registro
- Actualizar el progreso
- Reprogramar la próxima revisión (por defecto 10 días)

## Comandos Disponibles

### Generar Alertas Manualmente
```bash
# Ejecutar alertas reales
python manage.py generar_alertas_revision

# Modo de prueba (no crea notificaciones)
python manage.py generar_alertas_revision --dry-run
```

### Script Automatizado
```bash
# Ejecutar script diario
python scripts/ejecutar_alertas_diarias.py
```

## Configuración Automática

### En Linux/Mac (Cron)
Agregar al crontab para ejecutar diariamente a las 9:00 AM:
```bash
crontab -e
# Agregar línea:
0 9 * * * cd /ruta/al/proyecto && python scripts/ejecutar_alertas_diarias.py
```

### En Windows (Programador de Tareas)
1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Configurar para ejecutar diariamente
4. Acción: Iniciar programa
5. Programa: `python`
6. Argumentos: `scripts/ejecutar_alertas_diarias.py`
7. Directorio: Ruta del proyecto

## API Endpoints

### Polinizaciones
- `POST /api/polinizaciones/{id}/marcar-revisado/` - Marcar como revisada
- `GET /api/polinizaciones/pendientes-revision/` - Obtener pendientes

### Germinaciones
- `POST /api/germinaciones/{id}/marcar-revisado/` - Marcar como revisada
- `GET /api/germinaciones/pendientes-revision/` - Obtener pendientes

## Parámetros de Marcar como Revisado

```json
{
  "estado": "EN_PROCESO_TEMPRANO",  // Opcional: nuevo estado
  "progreso": 35,                   // Opcional: nuevo progreso (0-100)
  "dias_proxima_revision": 7        // Opcional: días para próxima revisión (default: 10)
}
```

## Estados Disponibles

- `INICIAL` (0-10%): Recién creado o inicializado
- `EN_PROCESO_TEMPRANO` (11-60%): Proceso temprano
- `EN_PROCESO_AVANZADO` (61-90%): Proceso avanzado
- `FINALIZADO` (91-100%): Completado (no genera más alertas)

## Logs

Los logs se guardan en:
- `logs/alertas_revision.log` - Log del script automatizado
- Django logs - Logs del comando manual

## Campos de Base de Datos

### Nuevos campos agregados:
- `fecha_proxima_revision` - Fecha programada para próxima revisión
- `alerta_revision_enviada` - Si ya se envió la alerta para esta fecha
- `fecha_ultima_revision` - Fecha de la última revisión manual

## Ejemplo de Notificación

```
🌸 Revisión de Polinización Pendiente

Es hora de revisar la polinización POL-20251218213722.

📊 Estado actual: Inicial
📈 Progreso: 10%
🌱 Especie: Cattleya Test Especie
📅 Creada hace: 10 días
👤 Responsable: admin

💡 Revisa el estado y actualiza el progreso según corresponda.
```

## Troubleshooting

### No se generan alertas
1. Verificar que existan registros con `fecha_proxima_revision <= hoy`
2. Verificar que `alerta_revision_enviada = False`
3. Verificar que el estado no sea `FINALIZADO`

### Alertas duplicadas
- Las alertas solo se envían una vez por fecha de revisión
- El campo `alerta_revision_enviada` previene duplicados

### Logs no se crean
- Verificar que existe el directorio `logs/`
- Verificar permisos de escritura

## Personalización

### Cambiar intervalo de revisión
Modificar en los modelos (`models.py`):
```python
self.fecha_proxima_revision = timezone.now().date() + timedelta(days=7)  # 7 días en lugar de 10
```

### Cambiar hora de ejecución
Modificar el cron job o tarea programada según necesidades.

### Personalizar mensajes
Modificar las plantillas de mensaje en `generar_alertas_revision.py`.