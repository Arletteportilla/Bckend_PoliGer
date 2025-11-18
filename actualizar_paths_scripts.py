#!/usr/bin/env python
"""
Script para actualizar los paths en todos los scripts reorganizados
"""
from pathlib import Path

def actualizar_script(archivo):
    """Actualiza un script para que funcione desde su nueva ubicación"""
    print(f"📝 Actualizando: {archivo}")
    
    with open(archivo, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    # Buscar el patrón de importación de Django
    if 'os.environ.setdefault' in contenido and 'django.setup()' in contenido:
        # Calcular cuántos niveles subir
        niveles = len(Path(archivo).relative_to('BACK/backend' if 'BACK/backend' in str(archivo) else '.').parts) - 1
        parent_path = '.parent' * niveles
        
        # Buscar y reemplazar el bloque de importación
        lineas = contenido.split('\n')
        nuevas_lineas = []
        django_setup_encontrado = False
        
        for i, linea in enumerate(lineas):
            if 'import os' in linea and not django_setup_encontrado:
                # Agregar imports necesarios
                nuevas_lineas.append('import os')
                nuevas_lineas.append('import sys')
                nuevas_lineas.append('import django')
                nuevas_lineas.append('from pathlib import Path')
                nuevas_lineas.append('')
                nuevas_lineas.append('# Agregar el directorio raíz del backend al path')
                nuevas_lineas.append(f'backend_root = Path(__file__){parent_path}')
                nuevas_lineas.append('sys.path.insert(0, str(backend_root))')
                nuevas_lineas.append('')
                
                # Saltar las siguientes líneas de import hasta django.setup()
                j = i + 1
                while j < len(lineas) and 'django.setup()' not in lineas[j]:
                    if 'import django' not in lineas[j] and lineas[j].strip():
                        if 'os.environ' in lineas[j]:
                            nuevas_lineas.append(lineas[j])
                    j += 1
                
                if j < len(lineas):
                    nuevas_lineas.append(lineas[j])  # django.setup()
                    django_setup_encontrado = True
                    
                # Continuar desde después de django.setup()
                for k in range(j + 1, len(lineas)):
                    nuevas_lineas.append(lineas[k])
                break
            else:
                if not django_setup_encontrado:
                    nuevas_lineas.append(linea)
        
        # Escribir el archivo actualizado
        with open(archivo, 'w', encoding='utf-8') as f:
            f.write('\n'.join(nuevas_lineas))
        
        print(f"   ✅ Actualizado correctamente")
        return True
    else:
        print(f"   ⚠️  No requiere actualización")
        return False

def main():
    """Función principal"""
    print("=" * 80)
    print("ACTUALIZANDO PATHS EN SCRIPTS REORGANIZADOS")
    print("=" * 80)
    print()
    
    # Scripts que necesitan actualización
    scripts = [
        'scripts/management/gestionar_usuarios.py',
        'scripts/data/importar_germinaciones.py',
        'scripts/data/analizar_csv.py',
        'scripts/ml/train_all_models.py',
        'scripts/utils/ver_notificaciones.py',
        'tests/test_notificaciones_sistema.py',
    ]
    
    actualizados = 0
    for script in scripts:
        if Path(script).exists():
            if actualizar_script(script):
                actualizados += 1
        else:
            print(f"⚠️  No encontrado: {script}")
    
    print()
    print("=" * 80)
    print(f"✅ ACTUALIZACIÓN COMPLETADA: {actualizados} archivos actualizados")
    print("=" * 80)
    print()
    print("🎯 Ahora puedes ejecutar los scripts desde cualquier ubicación:")
    print("   python scripts/utils/ver_notificaciones.py")
    print("   python scripts/management/gestionar_usuarios.py")
    print("   etc.")

if __name__ == '__main__':
    main()
