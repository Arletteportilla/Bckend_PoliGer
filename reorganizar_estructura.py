#!/usr/bin/env python
"""
Script para reorganizar la estructura del proyecto Django
siguiendo las mejores prácticas
MODO SEGURO: Copia archivos en lugar de moverlos
"""
import os
import shutil
from pathlib import Path
from datetime import datetime

def crear_backup():
    """Crea un backup de los archivos antes de reorganizar"""
    print("=" * 80)
    print("CREANDO BACKUP DE SEGURIDAD")
    print("=" * 80)
    
    backup_dir = Path('backup_reorganizacion')
    if backup_dir.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = Path(f'backup_reorganizacion_{timestamp}')
    
    backup_dir.mkdir(exist_ok=True)
    
    archivos_backup = [
        'gestionar_usuarios.py',
        'importar_germinaciones.py',
        'analizar_csv.py',
        'train_all_models.py',
        'ver_notificaciones.py',
        'probar_sistema_notificaciones.py',
    ]
    
    print("\n📦 Copiando archivos al backup...")
    for archivo in archivos_backup:
        if Path(archivo).exists():
            shutil.copy2(archivo, backup_dir / archivo)
            print(f"   ✅ {archivo} → backup/")
    
    print(f"\n✅ Backup creado en: {backup_dir}/")
    print("   Si algo sale mal, puedes restaurar desde aquí.")
    return backup_dir

def crear_estructura():
    """Crea la estructura de carpetas"""
    print("=" * 80)
    print("REORGANIZANDO ESTRUCTURA DEL PROYECTO")
    print("=" * 80)
    
    # Carpetas a crear
    carpetas = [
        'scripts',
        'scripts/management',
        'scripts/data',
        'scripts/ml',
        'scripts/utils',
        'tests',
    ]
    
    print("\n📁 Creando estructura de carpetas...")
    for carpeta in carpetas:
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ {carpeta}/")
        
        # Crear __init__.py
        init_file = Path(carpeta) / '__init__.py'
        if not init_file.exists():
            init_file.touch()
            print(f"   ✅ {carpeta}/__init__.py")

def mover_archivos():
    """Mueve los archivos a sus nuevas ubicaciones (MODO SEGURO: copia primero)"""
    print("\n📦 Reorganizando archivos...")
    
    movimientos = {
        # Management
        'gestionar_usuarios.py': 'scripts/management/gestionar_usuarios.py',
        
        # Data
        'importar_germinaciones.py': 'scripts/data/importar_germinaciones.py',
        'analizar_csv.py': 'scripts/data/analizar_csv.py',
        
        # ML
        'train_all_models.py': 'scripts/ml/train_all_models.py',
        
        # Utils
        'ver_notificaciones.py': 'scripts/utils/ver_notificaciones.py',
        
        # Tests
        'probar_sistema_notificaciones.py': 'tests/test_notificaciones_sistema.py',
    }
    
    archivos_movidos = []
    
    for origen, destino in movimientos.items():
        if Path(origen).exists():
            # Primero copiar
            shutil.copy2(origen, destino)
            print(f"   ✅ Copiado: {origen} → {destino}")
            archivos_movidos.append(origen)
        else:
            print(f"   ⚠️  {origen} no encontrado (puede que ya esté movido)")
    
    return archivos_movidos

def crear_readme_tests():
    """Crea README para la carpeta tests"""
    print("\n📝 Creando documentación...")
    
    readme_content = """# 🧪 Tests del Proyecto

## Tests Disponibles

### test_notificaciones_sistema.py
Prueba completa del sistema de notificaciones automáticas.

**Uso:**
```bash
python tests/test_notificaciones_sistema.py
```

## Agregar Nuevos Tests

1. Crea un archivo `test_*.py` en esta carpeta
2. Importa los módulos necesarios
3. Escribe tus tests
4. Ejecuta con `python tests/test_nombre.py`

## Usar pytest (Recomendado)

```bash
# Instalar pytest
pip install pytest

# Ejecutar todos los tests
pytest tests/

# Ejecutar un test específico
pytest tests/test_notificaciones_sistema.py
```
"""
    
    readme_path = Path('tests/README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"   ✅ tests/README.md")

def crear_readme_scripts():
    """Crea README para la carpeta scripts"""
    readme_content = """# 🛠️ Scripts de Utilidad

## Estructura

```
scripts/
├── management/     # Gestión de usuarios y sistema
├── data/          # Importación y análisis de datos
├── ml/            # Machine Learning
└── utils/         # Utilidades generales
```

## Scripts Disponibles

### Management
- **gestionar_usuarios.py** - Gestión de usuarios del sistema

### Data
- **importar_germinaciones.py** - Importar germinaciones desde CSV
- **analizar_csv.py** - Analizar archivos CSV

### ML
- **train_all_models.py** - Entrenar todos los modelos de ML

### Utils
- **ver_notificaciones.py** - Ver notificaciones del sistema

## Uso

```bash
# Desde el directorio backend
python scripts/management/gestionar_usuarios.py
python scripts/data/importar_germinaciones.py
python scripts/ml/train_all_models.py
python scripts/utils/ver_notificaciones.py
```
"""
    
    readme_path = Path('scripts/README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"   ✅ scripts/README.md")

def verificar_estructura():
    """Verifica que la estructura esté correcta"""
    print("\n🔍 Verificando estructura...")
    
    archivos_esperados = [
        'scripts/management/gestionar_usuarios.py',
        'scripts/data/importar_germinaciones.py',
        'scripts/data/analizar_csv.py',
        'scripts/ml/train_all_models.py',
        'scripts/utils/ver_notificaciones.py',
        'tests/test_notificaciones_sistema.py',
    ]
    
    todos_ok = True
    for archivo in archivos_esperados:
        if Path(archivo).exists():
            print(f"   ✅ {archivo}")
        else:
            print(f"   ❌ {archivo} - NO ENCONTRADO")
            todos_ok = False
    
    return todos_ok

def eliminar_originales(archivos_movidos, backup_dir):
    """Elimina los archivos originales después de confirmar"""
    print("\n🗑️  Eliminando archivos originales...")
    print("   (Los archivos están respaldados en backup/)")
    
    for archivo in archivos_movidos:
        if Path(archivo).exists():
            os.remove(archivo)
            print(f"   ✅ Eliminado: {archivo}")

def main():
    """Función principal"""
    try:
        # Paso 1: Crear backup
        backup_dir = crear_backup()
        
        # Paso 2: Crear estructura
        crear_estructura()
        
        # Paso 3: Copiar archivos (no mover todavía)
        archivos_movidos = mover_archivos()
        
        # Paso 4: Crear documentación
        crear_readme_tests()
        crear_readme_scripts()
        
        # Paso 5: Verificar
        print("\n" + "=" * 80)
        if verificar_estructura():
            print("✅ REORGANIZACIÓN COMPLETADA EXITOSAMENTE")
            print("=" * 80)
            
            # Paso 6: Eliminar originales
            eliminar_originales(archivos_movidos, backup_dir)
            
            print("\n📚 Estructura final:")
            print("""
BACK/backend/
├── scripts/
│   ├── management/
│   │   └── gestionar_usuarios.py
│   ├── data/
│   │   ├── importar_germinaciones.py
│   │   └── analizar_csv.py
│   ├── ml/
│   │   └── train_all_models.py
│   └── utils/
│       └── ver_notificaciones.py
└── tests/
    └── test_notificaciones_sistema.py
            """)
            print(f"\n💾 Backup guardado en: {backup_dir}/")
            print("   Puedes eliminarlo cuando confirmes que todo funciona.")
            print("\n🎯 Próximos pasos:")
            print("   1. Prueba los scripts en sus nuevas ubicaciones")
            print("   2. Si todo funciona, elimina la carpeta de backup")
            print("   3. Actualiza DOCUMENTACION_SISTEMA.md")
        else:
            print("⚠️  REORGANIZACIÓN COMPLETADA CON ADVERTENCIAS")
            print("=" * 80)
            print("\nAlgunos archivos no se encontraron.")
            print(f"Los archivos originales están respaldados en: {backup_dir}/")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("La reorganización no se completó correctamente.")
        print(f"Tus archivos originales están seguros en: {backup_dir}/")

if __name__ == '__main__':
    main()
