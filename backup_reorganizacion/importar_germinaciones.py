"""
Script para importar datos de germinaciones desde CSV a PostgreSQL
Uso: python importar_germinaciones.py
"""
import os
import sys
import django
import csv
from datetime import datetime
import re

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.core.models import Germinacion
from django.contrib.auth.models import User

def limpiar_valor(valor):
    """Limpia valores 'nan', espacios en blanco y valores nulos"""
    if not valor or valor.strip() in ['', 'nan', 'null', 'None', '-']:
        return None
    return valor.strip()

def parsear_fecha(fecha_str):
    """Convierte string de fecha DD/MM/YYYY a objeto date"""
    if not fecha_str or fecha_str.strip() in ['', '-', 'nan']:
        return None

    try:
        # Intentar varios formatos de fecha
        for formato in ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d']:
            try:
                fecha_obj = datetime.strptime(fecha_str.strip(), formato)
                # Si el año es mayor a 2100, probablemente se interpretó mal (ej: 2025 como 2025)
                if fecha_obj.year > 2100:
                    # Restar 100 años si es formato de 2 dígitos mal interpretado
                    fecha_obj = fecha_obj.replace(year=fecha_obj.year - 100)
                return fecha_obj.date()
            except ValueError:
                continue
        print(f"[!] No se pudo parsear la fecha: {fecha_str}")
        return None
    except Exception as e:
        print(f"[!] Error parseando fecha '{fecha_str}': {e}")
        return None

def parsear_ubicacion(ubicacion_str):
    """
    Parsea la ubicación en formato 'P-116 N-D'
    Retorna (percha, nivel)
    """
    if not ubicacion_str or ubicacion_str.strip() in ['', 'P-', '-']:
        return None, None

    # Ejemplo: "P-116 N-D" -> percha="P-116", nivel="N-D"
    # Ejemplo: "P-101 N-A" -> percha="P-101", nivel="N-A"
    ubicacion_str = ubicacion_str.strip()

    # Buscar patrón P-XXX N-X
    match = re.match(r'(P-\d+)\s*(N-[A-Z])?', ubicacion_str)
    if match:
        percha = match.group(1) if match.group(1) else None
        nivel = match.group(2) if match.group(2) else None
        return percha, nivel

    # Si no coincide, devolver todo como percha
    return ubicacion_str, None

def normalizar_clima(clima_str):
    """Normaliza los valores de clima al formato del modelo"""
    if not clima_str:
        return 'I'  # Default

    clima_map = {
        'Intermedio': 'I',
        'IW': 'IW',
        'IC': 'IC',
        'Warm': 'W',
        'Cool': 'C',
        'I': 'I',
        'W': 'W',
        'C': 'C',
    }

    return clima_map.get(clima_str.strip(), 'I')

def normalizar_estado_capsula(estado_str):
    """Normaliza el estado de cápsula"""
    if not estado_str:
        return 'CERRADA'

    estado_str = estado_str.strip().upper()

    if 'CERR' in estado_str:
        return 'CERRADA'
    elif 'ABIERT' in estado_str:
        return 'ABIERTA'
    elif 'SEMI' in estado_str:
        return 'SEMIABIERTA'

    return 'CERRADA'  # Default

def importar_germinaciones(archivo_csv, limpiar_existentes=False):
    """
    Importa germinaciones desde un archivo CSV

    Args:
        archivo_csv: Ruta al archivo CSV
        limpiar_existentes: Si es True, elimina todas las germinaciones existentes
    """

    if limpiar_existentes:
        respuesta = input("[!] ¿Estás seguro de que quieres eliminar TODAS las germinaciones existentes? (si/no): ")
        if respuesta.lower() == 'si':
            count = Germinacion.objects.all().count()
            Germinacion.objects.all().delete()
            print(f"[OK] {count} germinaciones eliminadas")
        else:
            print("[*] Cancelado")
            return

    # Obtener usuario admin para asignar como creador
    try:
        usuario_sistema = User.objects.filter(is_superuser=True).first()
        if not usuario_sistema:
            usuario_sistema = User.objects.first()
    except:
        usuario_sistema = None

    print(f"[*] Abriendo archivo: {archivo_csv}")

    registros_creados = 0
    registros_actualizados = 0
    registros_error = 0

    with open(archivo_csv, 'r', encoding='utf-8-sig') as f:
        # Leer CSV con delimitador punto y coma
        reader = csv.DictReader(f, delimiter=';')

        total_lineas = sum(1 for _ in open(archivo_csv, 'r', encoding='utf-8-sig')) - 1
        print(f"[*] Total de registros a procesar: {total_lineas}")

        for idx, row in enumerate(reader, start=1):
            try:
                # Extraer datos del CSV
                codigo = limpiar_valor(row.get('CODIGO'))

                if not codigo:
                    print(f"[!] Línea {idx}: Sin código, omitiendo...")
                    registros_error += 1
                    continue

                # Parsear fechas
                fecha_siembra = parsear_fecha(row.get('F.SIEMBRA'))
                fecha_germinacion = parsear_fecha(row.get('F.GERMI'))

                # Parsear ubicación
                percha, nivel = parsear_ubicacion(row.get('UBICACI'))

                # Extraer otros campos
                especie_variedad = limpiar_valor(row.get('ESPECIE'))
                clima = normalizar_clima(row.get('CLIMA'))
                responsable = limpiar_valor(row.get('RESPONSABLE'))
                estado_capsulas = normalizar_estado_capsula(row.get('E.CAPSU'))

                # Convertir valores numéricos
                try:
                    semilla_vana = int(row.get('S.VANA', 0)) if row.get('S.VANA', '').strip() else 0
                except:
                    semilla_vana = 0

                try:
                    semillas_stock = int(row.get('S.STOCK', 0)) if row.get('S.STOCK', '').strip() else 0
                except:
                    semillas_stock = 0

                try:
                    cantidad_solicitada = int(row.get('C.SOLIC', 0)) if row.get('C.SOLIC', '').strip() else 0
                except:
                    cantidad_solicitada = 0

                try:
                    disponibles = int(row.get('DISPONE', 0)) if row.get('DISPONE', '').strip() else 0
                except:
                    disponibles = 0

                # Verificar si ya existe este registro específico (mismo código, fecha y ubicación)
                germinacion_existe = Germinacion.objects.filter(
                    codigo=codigo,
                    fecha_siembra=fecha_siembra,
                    percha=percha,
                    nivel=nivel
                ).first()

                if germinacion_existe:
                    # Actualizar registro existente (mismo código, misma fecha, misma ubicación)
                    germinacion_existe.especie_variedad = especie_variedad or germinacion_existe.especie_variedad
                    germinacion_existe.clima = clima
                    germinacion_existe.responsable = responsable or germinacion_existe.responsable
                    germinacion_existe.semilla_vana = semilla_vana
                    germinacion_existe.semillas_stock = semillas_stock
                    germinacion_existe.cantidad_solicitada = cantidad_solicitada
                    germinacion_existe.disponibles = disponibles
                    germinacion_existe.fecha_germinacion = fecha_germinacion or germinacion_existe.fecha_germinacion
                    germinacion_existe.estado_capsulas = estado_capsulas
                    germinacion_existe.estado_capsula = estado_capsulas

                    germinacion_existe.save()
                    registros_actualizados += 1

                    if idx % 500 == 0:
                        print(f"[*] Procesados {idx}/{total_lineas} registros... (Actualizado: {codigo})")
                else:
                    # Crear nuevo registro (permite múltiples siembras del mismo código)
                    germinacion = Germinacion.objects.create(
                        codigo=codigo,
                        fecha_siembra=fecha_siembra,
                        especie_variedad=especie_variedad,
                        clima=clima,
                        percha=percha,
                        nivel=nivel,
                        responsable=responsable,
                        semilla_vana=semilla_vana,
                        semillas_stock=semillas_stock,
                        cantidad_solicitada=cantidad_solicitada,
                        disponibles=disponibles,
                        fecha_germinacion=fecha_germinacion,
                        estado_capsulas=estado_capsulas,
                        estado_capsula=estado_capsulas,  # También llenar el campo sin 's'
                        creado_por=usuario_sistema,
                    )
                    registros_creados += 1

                    if idx % 500 == 0:
                        print(f"[*] Procesados {idx}/{total_lineas} registros... (Creado: {codigo})")

            except Exception as e:
                print(f"[ERROR] Línea {idx}: {e}")
                registros_error += 1
                continue

    print("\n" + "="*60)
    print("[OK] Importación completada")
    print(f"    - Registros creados: {registros_creados}")
    print(f"    - Registros actualizados: {registros_actualizados}")
    print(f"    - Errores: {registros_error}")
    print(f"    - Total en BD: {Germinacion.objects.count()}")
    print("="*60)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Importar germinaciones desde CSV')
    parser.add_argument('--archivo', default='data/GERMINACION.csv', help='Ruta al archivo CSV')
    parser.add_argument('--limpiar', action='store_true', help='Eliminar germinaciones existentes antes de importar')

    args = parser.parse_args()

    archivo_csv = os.path.join(os.path.dirname(__file__), args.archivo)

    if not os.path.exists(archivo_csv):
        print(f"[ERROR] No se encontró el archivo: {archivo_csv}")
        sys.exit(1)

    print("[*] Iniciando importación de germinaciones...")
    print(f"[*] Archivo: {archivo_csv}")
    print(f"[*] Limpiar existentes: {'SÍ' if args.limpiar else 'NO'}")
    print("-" * 60)

    importar_germinaciones(archivo_csv, limpiar_existentes=args.limpiar)
