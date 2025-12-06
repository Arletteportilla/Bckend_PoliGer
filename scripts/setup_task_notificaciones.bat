@echo off
REM Script para configurar tarea programada en Windows para notificaciones de recordatorio
REM Este script debe ejecutarse como Administrador

echo ==========================================
echo Configurando Tarea Programada para Notificaciones
echo ==========================================
echo.

REM Obtener el directorio del proyecto
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set MANAGE_PY=%PROJECT_DIR%\manage.py

REM Verificar que existe manage.py
if not exist "%MANAGE_PY%" (
    echo Error: No se encontro manage.py en %PROJECT_DIR%
    pause
    exit /b 1
)

echo Proyecto encontrado en: %PROJECT_DIR%
echo.

REM Buscar Python
where python >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    set PYTHON_CMD=python
) else (
    where python3 >nul 2>nul
    if %ERRORLEVEL% EQU 0 (
        set PYTHON_CMD=python3
    ) else (
        echo Error: No se encontro Python en el sistema
        pause
        exit /b 1
    )
)

echo Python encontrado: %PYTHON_CMD%
echo.

REM Crear directorio de logs si no existe
if not exist "%PROJECT_DIR%\logs" mkdir "%PROJECT_DIR%\logs"

REM Crear el script que ejecutará la tarea
set TASK_SCRIPT=%PROJECT_DIR%\scripts\run_notificaciones.bat
echo @echo off > "%TASK_SCRIPT%"
echo cd /d "%PROJECT_DIR%" >> "%TASK_SCRIPT%"
echo %PYTHON_CMD% manage.py generar_notificaciones_recordatorio ^>^> logs\notificaciones_task.log 2^>^&1 >> "%TASK_SCRIPT%"

echo Script de tarea creado en: %TASK_SCRIPT%
echo.

REM Configurar la tarea programada
echo Configurando tarea programada...
echo La tarea se ejecutara todos los dias a las 9:00 AM
echo.

REM Eliminar tarea existente si existe
schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F >nul 2>nul

REM Crear nueva tarea
schtasks /Create /TN "PoliGer_Notificaciones_Recordatorio" /TR "\"%TASK_SCRIPT%\"" /SC DAILY /ST 09:00 /RU "%USERNAME%" /RL HIGHEST /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo Tarea programada configurada exitosamente
    echo ==========================================
    echo.
    echo Nombre de la tarea: PoliGer_Notificaciones_Recordatorio
    echo Frecuencia: Diaria a las 9:00 AM
    echo Logs: %PROJECT_DIR%\logs\notificaciones_task.log
    echo.
    echo Para ver las tareas programadas:
    echo   schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"
    echo.
    echo Para ejecutar la tarea manualmente:
    echo   schtasks /Run /TN "PoliGer_Notificaciones_Recordatorio"
    echo.
    echo Para eliminar la tarea:
    echo   schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F
    echo.
) else (
    echo.
    echo Error al crear la tarea programada
    echo Asegurate de ejecutar este script como Administrador
    echo.
)

echo ==========================================
echo Configuracion completada
echo ==========================================
echo.
pause
