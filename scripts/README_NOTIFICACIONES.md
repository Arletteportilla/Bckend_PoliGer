# Scripts de Notificaciones de Recordatorio

Este directorio contiene los scripts necesarios para configurar y ejecutar el sistema de notificaciones de recordatorio.

## 📁 Archivos

### `setup_task_notificaciones.bat` (Windows)
Script para configurar una tarea programada en Windows.

**Uso:**
```cmd
# Ejecutar como Administrador
setup_task_notificaciones.bat
```

**Qué hace:**
- Crea el script `run_notificaciones.bat`
- Configura una tarea programada llamada "PoliGer_Notificaciones_Recordatorio"
- La tarea se ejecuta diariamente a las 9:00 AM
- Los logs se guardan en `logs\notificaciones_task.log`

### `setup_cron_notificaciones.sh` (Linux/Mac)
Script para configurar un cron job en Linux/Mac.

**Uso:**
```bash
chmod +x setup_cron_notificaciones.sh
./setup_cron_notificaciones.sh
```

**Qué hace:**
- Configura un cron job que se ejecuta diariamente a las 9:00 AM
- Los logs se guardan en `logs/notificaciones_cron.log`

### `generar_notificaciones.py` (Multiplataforma)
Script Python para ejecutar el comando de forma más sencilla.

**Uso:**
```bash
# Modo simulación
python generar_notificaciones.py --dry-run

# Modo producción
python generar_notificaciones.py

# Con días personalizados
python generar_notificaciones.py --dias 7
```

### `run_notificaciones.bat` (Generado automáticamente)
Script generado por `setup_task_notificaciones.bat` que ejecuta el comando.

**No editar manualmente** - Se genera automáticamente durante la configuración.

## 🚀 Inicio Rápido

### Windows
1. Abrir CMD/PowerShell como Administrador
2. Navegar al directorio del proyecto
3. Ejecutar: `scripts\setup_task_notificaciones.bat`

### Linux/Mac
1. Abrir terminal
2. Navegar al directorio del proyecto
3. Ejecutar: `chmod +x scripts/setup_cron_notificaciones.sh && ./scripts/setup_cron_notificaciones.sh`

## 📊 Verificación

### Windows
```cmd
# Ver tarea programada
schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"

# Ejecutar manualmente
schtasks /Run /TN "PoliGer_Notificaciones_Recordatorio"

# Ver logs
type ..\logs\notificaciones_task.log
```

### Linux/Mac
```bash
# Ver cron jobs
crontab -l

# Ver logs
cat ../logs/notificaciones_cron.log
```

## 🔧 Personalización

Ver la documentación completa en:
- `../INSTALACION_NOTIFICACIONES.md`
- `../NOTIFICACIONES_RECORDATORIO.md`

## 🗑️ Desinstalación

### Windows
```cmd
schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F
```

### Linux/Mac
```bash
crontab -e
# Eliminar la línea del cron job
```

## 📞 Soporte

Para más información, consulta la documentación en el directorio padre.
