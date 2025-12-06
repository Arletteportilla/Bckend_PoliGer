@echo off
echo ==========================================
echo Configuracion Rapida de Notificaciones
echo ==========================================
echo.
echo Este script configurara las notificaciones automaticas.
echo.
echo IMPORTANTE: Debes ejecutar este archivo como Administrador
echo.
pause

REM Obtener directorio actual
set CURRENT_DIR=%~dp0

echo.
echo Configurando tarea programada...
echo.

REM Crear script de ejecucion
echo @echo off > "%CURRENT_DIR%run_notificaciones.bat"
echo cd /d "%CURRENT_DIR%" >> "%CURRENT_DIR%run_notificaciones.bat"
echo python manage.py generar_notificaciones_recordatorio ^>^> logs\notificaciones_task.log 2^>^&1 >> "%CURRENT_DIR%run_notificaciones.bat"

REM Crear directorio de logs
if not exist "%CURRENT_DIR%logs" mkdir "%CURRENT_DIR%logs"

REM Eliminar tarea existente
schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F >nul 2>nul

REM Crear tarea programada (diaria a las 9:00 AM)
schtasks /Create /TN "PoliGer_Notificaciones_Recordatorio" /TR "\"%CURRENT_DIR%run_notificaciones.bat\"" /SC DAILY /ST 09:00 /RU "%USERNAME%" /RL HIGHEST /F

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo CONFIGURACION EXITOSA
    echo ==========================================
    echo.
    echo La tarea se ejecutara automaticamente todos los dias a las 9:00 AM
    echo.
    echo Para ejecutar ahora manualmente:
    echo   schtasks /Run /TN "PoliGer_Notificaciones_Recordatorio"
    echo.
    echo Para ver la tarea:
    echo   schtasks /Query /TN "PoliGer_Notificaciones_Recordatorio"
    echo.
    echo Para eliminar la tarea:
    echo   schtasks /Delete /TN "PoliGer_Notificaciones_Recordatorio" /F
    echo.
) else (
    echo.
    echo ==========================================
    echo ERROR EN LA CONFIGURACION
    echo ==========================================
    echo.
    echo Asegurate de ejecutar este archivo como Administrador:
    echo 1. Click derecho en el archivo
    echo 2. Seleccionar "Ejecutar como administrador"
    echo.
)

echo.
echo Presiona cualquier tecla para salir...
pause >nul
