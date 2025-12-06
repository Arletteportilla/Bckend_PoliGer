# Quick Start - Notificaciones de Recordatorio

## 🚀 Inicio Rápido

### 1. Probar el Comando (Modo Simulación)

```bash
# Desde el directorio BACK/backend/
python manage.py generar_notificaciones_recordatorio --dry-run
```

Esto mostrará qué notificaciones se generarían **sin crearlas realmente**.

### 2. Ejecutar el Comando (Modo Real)

```bash
python manage.py generar_notificaciones_recordatorio
```

Esto **creará las notificaciones reales** para registros con más de 5 días en estado INICIAL.

### 3. Personalizar Días Límite

```bash
# Para registros con más de 7 días
python manage.py generar_notificaciones_recordatorio --dias 7

# Para registros con más de 3 días
python manage.py generar_notificaciones_recordatorio --dias 3
```

### 4. Usar el Script Python

```bash
# Modo simulación
python scripts/generar_notificaciones.py --dry-run

# Modo real
python scripts/generar_notificaciones.py

# Con días personalizados
python scripts/generar_notificaciones.py --dias 7
```

## 📅 Configurar Ejecución Automática

### Windows

1. Ejecutar como **Administrador**:
```cmd
scripts\setup_task_notificaciones.bat
```

2. La tarea se ejecutará **diariamente a las 9:00 AM**

### Linux/Mac

1. Dar permisos:
```bash
chmod +x scripts/setup_cron_notificaciones.sh
```

2. Ejecutar:
```bash
./scripts/setup_cron_notificaciones.sh
```

3. El cron job se ejecutará **diariamente a las 9:00 AM**

## 📊 Ver Resultados

### Desde el Frontend
1. Ir a **Notificaciones**
2. Verás notificaciones con título: "⏰ Recordatorio: ..."

### Desde la API
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notificaciones/?tipo=RECORDATORIO_REVISION
```

### Ver Registros Pendientes
```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/notificaciones/registros-pendientes/
```

## 🔍 Verificar Logs

### Windows
```cmd
type logs\notificaciones_task.log
```

### Linux/Mac
```bash
cat logs/notificaciones_cron.log
```

## ❓ Preguntas Frecuentes

**P: ¿Cuándo se generan las notificaciones?**
R: Cuando un registro (germinación o polinización) lleva más de 5 días en estado INICIAL.

**P: ¿Se generan notificaciones duplicadas?**
R: No, el sistema evita duplicados automáticamente (cooldown de 24 horas).

**P: ¿Qué pasa si cambio el estado a EN_PROCESO?**
R: Las notificaciones dejan de generarse automáticamente.

**P: ¿Puedo cambiar el número de días?**
R: Sí, usa el parámetro `--dias X` al ejecutar el comando.

**P: ¿Cómo desactivo las notificaciones automáticas?**
R: 
- Windows: `schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F`
- Linux/Mac: `crontab -e` y elimina la línea correspondiente

## 📝 Ejemplo de Salida

```
======================================================================
Generando notificaciones de recordatorio
Días límite: 5
Modo: PRODUCCIÓN
======================================================================

📋 Procesando germinaciones...
  ✅ Germinación GER-2025-001 - 7 días en INICIAL
  ✅ Germinación GER-2025-002 - 6 días en INICIAL
  ⏭️  Germinación GER-2025-003 - Ya tiene notificación reciente

🌸 Procesando polinizaciones...
  ✅ Polinización POL-2025-001 - 8 días en INICIAL

======================================================================
RESUMEN:
  - Notificaciones de germinación: 2
  - Notificaciones de polinización: 1
  - Total: 3
======================================================================
```

## 🆘 Soporte

Si tienes problemas, revisa el archivo completo: `NOTIFICACIONES_RECORDATORIO.md`
