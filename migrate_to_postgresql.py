#!/usr/bin/env python
"""
Script para migrar de SQLite a PostgreSQL
Verifica la configuración y ejecuta las migraciones necesarias
"""
import os
import sys
import subprocess
from pathlib import Path

# Colores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_step(step, message):
    print(f"\n{Colors.BLUE}{Colors.BOLD}[Paso {step}]{Colors.END} {message}")

def print_success(message):
    print(f"{Colors.GREEN}[OK]{Colors.END} {message}")

def print_warning(message):
    print(f"{Colors.YELLOW}[!]{Colors.END} {message}")

def print_error(message):
    print(f"{Colors.RED}[X]{Colors.END} {message}")

def run_command(command, description):
    """Ejecuta un comando y retorna True si fue exitoso"""
    print(f"\n  → {description}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(f"    {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Error: {e}")
        if e.stderr:
            print(f"    {e.stderr.strip()}")
        return False

def main():
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}  MIGRACIÓN A POSTGRESQL - PROYECTO POLIGER{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

    # Paso 1: Verificar configuración
    print_step(1, "Verificando configuración del proyecto")

    if not os.path.exists('.env'):
        print_error("Archivo .env no encontrado")
        sys.exit(1)

    print_success("Archivo .env encontrado")

    # Configurar stdout para UTF-8 en Windows
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

    # Leer configuración
    with open('.env', 'r') as f:
        env_content = f.read()

    if 'DB_ENGINE=postgresql' in env_content:
        print_success("Configuración de PostgreSQL activa")
    else:
        print_error("DB_ENGINE no está configurado como 'postgresql' en .env")
        sys.exit(1)

    # Verificar credenciales
    config = {}
    for line in env_content.split('\n'):
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            config[key.strip()] = value.strip()

    print(f"\n  Configuracion detectada:")
    print(f"    • Base de datos: {config.get('DB_NAME', 'N/A')}")
    print(f"    • Usuario: {config.get('DB_USER', 'N/A')}")
    print(f"    • Host: {config.get('DB_HOST', 'N/A')}")
    print(f"    • Puerto: {config.get('DB_PORT', 'N/A')}")

    # Paso 2: Verificar psycopg2
    print_step(2, "Verificando instalación de psycopg2")

    try:
        import psycopg2
        print_success(f"psycopg2 instalado (versión {psycopg2.__version__})")
    except ImportError:
        print_warning("psycopg2 no está instalado")
        print("\n  Instalando psycopg2-binary...")
        if run_command("pip install psycopg2-binary==2.9.9", "Instalando psycopg2-binary"):
            print_success("psycopg2-binary instalado exitosamente")
        else:
            print_error("Error al instalar psycopg2-binary")
            sys.exit(1)

    # Paso 3: Verificar conexión a PostgreSQL
    print_step(3, "Verificando conexión a PostgreSQL")

    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname='postgres',  # Conectar a DB por defecto
            user=config.get('DB_USER', 'postgres'),
            password=config.get('DB_PASSWORD', ''),
            host=config.get('DB_HOST', 'localhost'),
            port=config.get('DB_PORT', '5432')
        )
        conn.close()
        print_success("Conexión a PostgreSQL exitosa")
    except Exception as e:
        print_error(f"No se pudo conectar a PostgreSQL: {e}")
        print("\n  Por favor, verifica que:")
        print("    1. PostgreSQL esté instalado y ejecutándose")
        print("    2. Las credenciales en .env sean correctas")
        print("    3. El usuario tenga permisos suficientes")
        sys.exit(1)

    # Paso 4: Verificar/Crear base de datos
    print_step(4, f"Verificando base de datos '{config.get('DB_NAME', 'poliger_db')}'")

    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname='postgres',
            user=config.get('DB_USER', 'postgres'),
            password=config.get('DB_PASSWORD', ''),
            host=config.get('DB_HOST', 'localhost'),
            port=config.get('DB_PORT', '5432')
        )
        conn.autocommit = True
        cursor = conn.cursor()

        # Verificar si la BD existe
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (config.get('DB_NAME', 'poliger_db'),)
        )

        if cursor.fetchone():
            print_success(f"Base de datos '{config.get('DB_NAME')}' ya existe")
        else:
            print_warning(f"Base de datos '{config.get('DB_NAME')}' no existe")
            print(f"\n  Creando base de datos...")
            cursor.execute(f"CREATE DATABASE {config.get('DB_NAME', 'poliger_db')}")
            print_success(f"Base de datos '{config.get('DB_NAME')}' creada exitosamente")

        cursor.close()
        conn.close()
    except Exception as e:
        print_error(f"Error al verificar/crear base de datos: {e}")
        sys.exit(1)

    # Paso 5: Ejecutar migraciones
    print_step(5, "Ejecutando migraciones de Django")

    if not run_command("python manage.py makemigrations", "Generando nuevas migraciones si es necesario"):
        print_warning("No se pudieron generar nuevas migraciones (puede ser normal si no hay cambios)")

    if run_command("python manage.py migrate", "Aplicando migraciones a PostgreSQL"):
        print_success("Migraciones aplicadas exitosamente")
    else:
        print_error("Error al aplicar migraciones")
        sys.exit(1)

    # Paso 6: Verificar tablas creadas
    print_step(6, "Verificando tablas en la base de datos")

    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=config.get('DB_NAME', 'poliger_db'),
            user=config.get('DB_USER', 'postgres'),
            password=config.get('DB_PASSWORD', ''),
            host=config.get('DB_HOST', 'localhost'),
            port=config.get('DB_PORT', '5432')
        )
        cursor = conn.cursor()

        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print_success(f"Se encontraron {len(tables)} tablas en la base de datos")

        # Mostrar tablas importantes
        important_tables = ['laboratorio_polinizacion', 'laboratorio_germinacion']
        print("\n  Tablas principales:")
        for table in tables:
            table_name = table[0]
            if any(imp in table_name for imp in important_tables):
                print(f"    [OK] {table_name}")

        cursor.close()
        conn.close()
    except Exception as e:
        print_warning(f"No se pudieron verificar las tablas: {e}")

    # Paso 7: Crear superusuario (opcional)
    print_step(7, "Configuración de superusuario")

    print("\n  ¿Deseas crear un superusuario para acceder al admin de Django?")
    response = input("  (s/n): ").lower().strip()

    if response == 's':
        print("\n  Ejecuta el siguiente comando manualmente:")
        print(f"    {Colors.YELLOW}python manage.py createsuperuser{Colors.END}")
    else:
        print_success("Puedes crear un superusuario después con: python manage.py createsuperuser")

    # Resumen final
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}  [OK] MIGRACION COMPLETADA EXITOSAMENTE{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

    print("\n  Proximos pasos:")
    print("    1. Verificar que el servidor Django inicie correctamente:")
    print(f"       {Colors.YELLOW}python manage.py runserver{Colors.END}")
    print("\n    2. Acceder al admin de Django:")
    print(f"       {Colors.YELLOW}http://127.0.0.1:8000/admin/{Colors.END}")
    print("\n    3. Probar los endpoints de la API:")
    print(f"       {Colors.YELLOW}http://127.0.0.1:8000/api/{Colors.END}")

    print(f"\n  Tu proyecto ahora usa PostgreSQL!")
    print()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}[!] Proceso interrumpido por el usuario{Colors.END}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}[X] Error inesperado: {e}{Colors.END}")
        sys.exit(1)
