#!/bin/bash

# Script para configurar cron job para notificaciones de recordatorio
# Este script debe ejecutarse con permisos de administrador

echo "=========================================="
echo "Configurando Cron Job para Notificaciones"
echo "=========================================="
echo ""

# Obtener el directorio del proyecto
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MANAGE_PY="$PROJECT_DIR/manage.py"

# Verificar que existe manage.py
if [ ! -f "$MANAGE_PY" ]; then
    echo "❌ Error: No se encontró manage.py en $PROJECT_DIR"
    exit 1
fi

echo "✅ Proyecto encontrado en: $PROJECT_DIR"
echo ""

# Obtener el path de Python (puede ser python3 o python)
PYTHON_CMD=$(which python3 2>/dev/null || which python 2>/dev/null)

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ Error: No se encontró Python en el sistema"
    exit 1
fi

echo "✅ Python encontrado en: $PYTHON_CMD"
echo ""

# Crear el comando cron
# Se ejecutará todos los días a las 9:00 AM
CRON_COMMAND="0 9 * * * cd $PROJECT_DIR && $PYTHON_CMD $MANAGE_PY generar_notificaciones_recordatorio >> $PROJECT_DIR/logs/notificaciones_cron.log 2>&1"

echo "Comando cron a configurar:"
echo "$CRON_COMMAND"
echo ""

# Crear directorio de logs si no existe
mkdir -p "$PROJECT_DIR/logs"

# Preguntar al usuario si desea continuar
read -p "¿Desea agregar este cron job? (s/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Ss]$ ]]; then
    # Agregar el cron job
    (crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -
    
    echo ""
    echo "✅ Cron job agregado exitosamente"
    echo ""
    echo "El comando se ejecutará todos los días a las 9:00 AM"
    echo "Los logs se guardarán en: $PROJECT_DIR/logs/notificaciones_cron.log"
    echo ""
    echo "Para ver los cron jobs actuales, ejecuta: crontab -l"
    echo "Para editar los cron jobs, ejecuta: crontab -e"
    echo "Para eliminar este cron job, ejecuta: crontab -e y elimina la línea correspondiente"
    echo ""
else
    echo ""
    echo "❌ Operación cancelada"
    echo ""
    echo "Si deseas configurar el cron job manualmente, ejecuta:"
    echo "  crontab -e"
    echo ""
    echo "Y agrega la siguiente línea:"
    echo "  $CRON_COMMAND"
    echo ""
fi

echo "=========================================="
echo "Configuración completada"
echo "=========================================="
