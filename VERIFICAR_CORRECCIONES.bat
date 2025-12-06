@echo off
echo ================================================================================
echo VERIFICACION DE CORRECCIONES APLICADAS
echo ================================================================================
echo.

echo [1/3] Verificando sintaxis de archivos modificados...
python -m py_compile laboratorio\services\germinacion_service.py
if %errorlevel% neq 0 (
    echo [ERROR] Error de sintaxis en germinacion_service.py
    pause
    exit /b 1
)
echo [OK] germinacion_service.py

python -m py_compile laboratorio\services\polinizacion_service.py
if %errorlevel% neq 0 (
    echo [ERROR] Error de sintaxis en polinizacion_service.py
    pause
    exit /b 1
)
echo [OK] polinizacion_service.py
echo.

echo [2/3] Ejecutando pruebas de validacion de codigos duplicados...
python test_codigo_duplicado.py
if %errorlevel% neq 0 (
    echo [ERROR] Las pruebas de validacion fallaron
    pause
    exit /b 1
)
echo.

echo [3/3] Verificando estructura de base de datos...
python manage.py check
if %errorlevel% neq 0 (
    echo [ERROR] Hay problemas con la configuracion de Django
    pause
    exit /b 1
)
echo.

echo ================================================================================
echo TODAS LAS VERIFICACIONES PASARON EXITOSAMENTE
echo ================================================================================
echo.
echo Correcciones aplicadas:
echo   1. Sistema RBAC - Roles y permisos de usuarios
echo   2. Notificaciones - Cambio de estado desde notificaciones
echo   3. Filtrado - Mis Germinaciones/Polinizaciones por usuario
echo   4. Validacion - Codigos duplicados en germinaciones y polinizaciones
echo.
echo El sistema esta listo para usar.
echo.
pause




