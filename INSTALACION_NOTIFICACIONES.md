# 🚀 Instalación del Sistema de Notificaciones de Recordatorio

## ⚡ Instalación Rápida (5 minutos)

### Paso 1: Verificar que el Comando Funciona

```bash
# Desde BACK/backend/
python manage.py generar_notificaciones_recordatorio --dry-run
```

✅ Si ves el mensaje de éxito, el comando está instalado correctamente.

### Paso 2: Configurar Ejecución Automática

#### 🪟 Windows

1. **Abrir PowerShell o CMD como Administrador**
   - Click derecho en el menú inicio
   - Seleccionar "Windows PowerShell (Administrador)" o "Símbolo del sistema (Administrador)"

2. **Navegar al directorio del proyecto**
   ```cmd
   cd C:\ruta\a\tu\proyecto\BACK\backend
   ```

3. **Ejecutar el script de configuración**
   ```cmd
   scripts\setup_task_notificaciones.bat
   ```

4. **Verificar que se creó la tarea**
   ```cmd
   schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"
   ```

✅ **¡Listo!** La tarea se ejecutará diariamente a las 9:00 AM.

#### 🐧 Linux / 🍎 Mac

1. **Dar permisos de ejecución al script**
   ```bash
   cd /ruta/a/tu/proyecto/BACK/backend
   chmod +x scripts/setup_cron_notificaciones.sh
   ```

2. **Ejecutar el script de configuración**
   ```bash
   ./scripts/setup_cron_notificaciones.sh
   ```

3. **Verificar que se creó el cron job**
   ```bash
   crontab -l
   ```

✅ **¡Listo!** El cron job se ejecutará diariamente a las 9:00 AM.

### Paso 3: Probar Manualmente (Opcional)

```bash
# Generar notificaciones reales
python manage.py generar_notificaciones_recordatorio

# Ver las notificaciones generadas
python manage.py shell
```

```python
from laboratorio.models import Notification
notificaciones = Notification.objects.filter(tipo='RECORDATORIO_REVISION')
print(f"Total de notificaciones de recordatorio: {notificaciones.count()}")
for n in notificaciones[:5]:
    print(f"- {n.titulo}")
```

## 🔧 Configuración Personalizada

### Cambiar el Horario de Ejecución

#### Windows
```cmd
# Cambiar a las 2:00 PM
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /ST 14:00

# Cambiar a las 8:00 AM
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /ST 08:00
```

#### Linux/Mac
```bash
# Editar el cron job
crontab -e

# Cambiar la hora (formato: minuto hora día mes día_semana)
# Ejemplo para las 2:00 PM:
0 14 * * * cd /ruta/proyecto && python manage.py generar_notificaciones_recordatorio

# Ejemplo para las 8:00 AM:
0 8 * * * cd /ruta/proyecto && python manage.py generar_notificaciones_recordatorio
```

### Cambiar el Número de Días

Editar el comando en la tarea/cron para agregar `--dias X`:

#### Windows
1. Abrir el Programador de Tareas
2. Buscar "PoliGer_Notificaciones_Recordatorio"
3. Editar la acción
4. Cambiar el script `run_notificaciones.bat` para incluir `--dias 7`

O editar manualmente:
```cmd
notepad scripts\run_notificaciones.bat
```

Cambiar la última línea a:
```batch
python manage.py generar_notificaciones_recordatorio --dias 7 >> logs\notificaciones_task.log 2>&1
```

#### Linux/Mac
```bash
crontab -e
```

Cambiar el comando a:
```bash
0 9 * * * cd /ruta/proyecto && python manage.py generar_notificaciones_recordatorio --dias 7
```

### Cambiar la Frecuencia

#### Ejecutar Cada 12 Horas

**Windows:**
```cmd
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /SC HOURLY /MO 12
```

**Linux/Mac:**
```bash
crontab -e
# Agregar:
0 */12 * * * cd /ruta/proyecto && python manage.py generar_notificaciones_recordatorio
```

#### Ejecutar Solo de Lunes a Viernes

**Windows:**
```cmd
schtasks /Change /TN "PoliGer_Notificaciones_Recordatorio" /D MON,TUE,WED,THU,FRI
```

**Linux/Mac:**
```bash
crontab -e
# Cambiar a:
0 9 * * 1-5 cd /ruta/proyecto && python manage.py generar_notificaciones_recordatorio
```

## 📊 Verificación

### Ver Logs

#### Windows
```cmd
type logs\notificaciones_task.log
```

#### Linux/Mac
```bash
cat logs/notificaciones_cron.log
# O en tiempo real:
tail -f logs/notificaciones_cron.log
```

### Ejecutar Manualmente la Tarea

#### Windows
```cmd
schtasks /Run /TN "PoliGer_Notificaciones_Recordatorio"
```

#### Linux/Mac
```bash
cd /ruta/proyecto/BACK/backend
python manage.py generar_notificaciones_recordatorio
```

### Ver Notificaciones en la Base de Datos

```bash
python manage.py shell
```

```python
from laboratorio.models import Notification
from datetime import date

# Notificaciones de hoy
hoy = date.today()
notificaciones_hoy = Notification.objects.filter(
    tipo='RECORDATORIO_REVISION',
    fecha_creacion__date=hoy
)

print(f"Notificaciones generadas hoy: {notificaciones_hoy.count()}")

for n in notificaciones_hoy:
    print(f"\n{n.titulo}")
    print(f"Usuario: {n.usuario.username}")
    print(f"Leída: {n.leida}")
```

## 🗑️ Desinstalación

### Eliminar la Tarea Automática

#### Windows
```cmd
schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F
```

#### Linux/Mac
```bash
crontab -e
# Eliminar la línea del cron job
```

### Eliminar Notificaciones Existentes (Opcional)

```bash
python manage.py shell
```

```python
from laboratorio.models import Notification

# Eliminar todas las notificaciones de recordatorio
Notification.objects.filter(tipo='RECORDATORIO_REVISION').delete()
```

## ❓ Solución de Problemas

### La tarea no se ejecuta automáticamente

1. **Verificar que la tarea/cron existe:**
   - Windows: `schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"`
   - Linux/Mac: `crontab -l`

2. **Verificar los logs:**
   - Windows: `type logs\notificaciones_task.log`
   - Linux/Mac: `cat logs/notificaciones_cron.log`

3. **Ejecutar manualmente para ver errores:**
   ```bash
   python manage.py generar_notificaciones_recordatorio
   ```

### No se generan notificaciones

1. **Verificar que existen registros elegibles:**
   ```bash
   python manage.py generar_notificaciones_recordatorio --dry-run
   ```

2. **Verificar que los registros tienen más de 5 días:**
   ```python
   from laboratorio.models import Germinacion, Polinizacion
   from datetime import date, timedelta
   
   fecha_limite = date.today() - timedelta(days=5)
   
   germinaciones = Germinacion.objects.filter(
       estado_germinacion='INICIAL',
       fecha_siembra__lte=fecha_limite
   )
   print(f"Germinaciones elegibles: {germinaciones.count()}")
   ```

3. **Verificar que los registros tienen usuario creador:**
   ```python
   germinaciones_sin_usuario = Germinacion.objects.filter(
       estado_germinacion='INICIAL',
       creado_por__isnull=True
   )
   print(f"Germinaciones sin usuario: {germinaciones_sin_usuario.count()}")
   ```

### Permisos insuficientes (Linux/Mac)

Si el cron job no funciona por permisos:

1. **Verificar permisos del script:**
   ```bash
   ls -la scripts/setup_cron_notificaciones.sh
   chmod +x scripts/setup_cron_notificaciones.sh
   ```

2. **Verificar permisos de manage.py:**
   ```bash
   ls -la manage.py
   chmod +x manage.py
   ```

## 📚 Documentación Adicional

- **Guía Completa:** `NOTIFICACIONES_RECORDATORIO.md`
- **Inicio Rápido:** `QUICK_START_NOTIFICACIONES.md`
- **Resumen:** `RESUMEN_NOTIFICACIONES_RECORDATORIO.md`

## ✅ Checklist de Instalación

- [ ] Comando funciona en modo dry-run
- [ ] Tarea/cron configurada
- [ ] Tarea/cron verificada
- [ ] Logs creados y accesibles
- [ ] Prueba manual exitosa
- [ ] Notificaciones visibles en el frontend

## 🎉 ¡Instalación Completada!

El sistema de notificaciones está listo para usar. Las notificaciones se generarán automáticamente según la configuración establecida.

**Próximos pasos:**
1. Esperar a que se ejecute la tarea automática
2. Verificar las notificaciones en el frontend
3. Ajustar configuración si es necesario

---

**Fecha de instalación:** _______________
**Configurado por:** _______________
**Horario de ejecución:** _______________
**Días límite:** _______________
