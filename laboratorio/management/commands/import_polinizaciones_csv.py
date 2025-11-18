import csv
import os
import re
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from laboratorio.models import Polinizacion

class Command(BaseCommand):
    help = 'Importa polinizaciones desde datos_combinados_limpios.csv'

    def parsear_ubicacion(self, ubicacion):
        """Parsea la ubicación y extrae vivero, mesa y pared"""
        if not ubicacion:
            return None, None, None

        ubicacion = ubicacion.strip()
        vivero = None
        mesa = None
        pared = None

        # Buscar vivero (V-X donde X es uno o más dígitos)
        match_vivero = re.search(r'V-\d+', ubicacion, re.IGNORECASE)
        if match_vivero:
            vivero = match_vivero.group(0).upper()

        # Buscar mesa (M-XY donde X es dígito(s) e Y es letra(s))
        match_mesa = re.search(r'M-\d+[A-Z]+', ubicacion, re.IGNORECASE)
        if match_mesa:
            mesa = match_mesa.group(0).upper()

        # Buscar pared (P-X o P-XY donde X es dígito(s) opcional e Y es letra(s))
        # Debe tener al menos un dígito o una letra después de P-
        match_pared = re.search(r'P-(?:\d+[A-Z]*|[A-Z]+)', ubicacion, re.IGNORECASE)
        if match_pared:
            pared = match_pared.group(0).upper()
        # También buscar formato P-N-X (como P-111 N-C)
        elif re.search(r'P-\d+', ubicacion, re.IGNORECASE):
            match_pared = re.search(r'P-\d+', ubicacion, re.IGNORECASE)
            if match_pared:
                pared = match_pared.group(0).upper()

        return vivero, mesa, pared

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/datos_combinados_limpios.csv',
            help='Ruta al archivo CSV de polinizaciones (relativa a BASE_DIR)'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Usuario que será asignado como creador (default: admin)'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Actualizar registros existentes basados en el código'
        )

    def parse_date(self, date_str):
        """Parsea fechas en diferentes formatos"""
        if not date_str or date_str.strip() == '':
            return None

        date_str = date_str.strip()

        # Formatos posibles
        formats = [
            '%d-%b-%y',  # 08-oct-10
            '%d-%B-%y',  # 08-October-10
            '%Y-%m-%d',  # 2010-10-08
            '%d/%m/%Y',  # 08/10/2010
            '%m/%d/%Y',  # 10/08/2010
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        self.stdout.write(
            self.style.WARNING(f'  [!] No se pudo parsear fecha: {date_str}')
        )
        return None

    def handle(self, *args, **options):
        # Obtener usuario
        try:
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            raise CommandError(f'Usuario {options["user"]} no encontrado')

        # Construir ruta del archivo
        from django.conf import settings
        file_path = os.path.join(settings.BASE_DIR, options['file'])

        if not os.path.exists(file_path):
            raise CommandError(f'El archivo {file_path} no existe')

        self.stdout.write(f'\nImportando polinizaciones desde {file_path}...')
        self.stdout.write(f'Usuario: {user.username}\n')

        imported_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)

                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Leer campos del CSV
                        codigo = row.get('codigo', '').strip()
                        genero = row.get('genero', '').strip()
                        especie = row.get('especie', '').strip()
                        ubicacion = row.get('ubicacion', '').strip()
                        responsable = row.get('responsable', '').strip()
                        cantidad = row.get('cantidad', '1').strip()
                        disponible_str = row.get('disponible', '0').strip()
                        archivo_origen = row.get('archivo_origen', '').strip()

                        # Validar código (campo requerido)
                        if not codigo:
                            self.stdout.write(
                                self.style.WARNING(f'  [!] Fila {row_num}: Sin codigo, omitiendo')
                            )
                            skipped_count += 1
                            continue

                        # Parsear fechas
                        fechapol = self.parse_date(row.get('fechapol', ''))
                        fechamad = self.parse_date(row.get('fechamad', ''))

                        # Parsear cantidad y disponible
                        try:
                            cantidad_int = int(cantidad) if cantidad else 1
                        except ValueError:
                            cantidad_int = 1

                        try:
                            disponible_bool = int(disponible_str) == 1
                        except ValueError:
                            disponible_bool = False

                        # Parsear ubicación en vivero, mesa y pared
                        vivero, mesa, pared = self.parsear_ubicacion(ubicacion)

                        # Preparar datos para crear
                        data = {
                            'fechapol': fechapol,
                            'fechamad': fechamad,
                            'genero': genero,
                            'especie': especie,
                            'ubicacion': ubicacion,
                            'vivero': vivero or '',
                            'mesa': mesa or '',
                            'pared': pared or '',
                            'responsable': responsable,
                            'cantidad': cantidad_int,
                            'disponible': disponible_bool,
                            'archivo_origen': archivo_origen,
                            'creado_por': user,
                        }

                        # Crear nuevo registro (permitir duplicados)
                        polinizacion = Polinizacion.objects.create(
                            codigo=codigo,
                            **data
                        )
                        imported_count += 1

                        # Mostrar progreso cada 1000 registros
                        if imported_count % 1000 == 0:
                            self.stdout.write(
                                self.style.SUCCESS(f'  [+] Importados {imported_count} registros...')
                            )

                    except Exception as e:
                        error_msg = f"Error en fila {row_num} (codigo: {row.get('codigo', 'N/A')}): {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(
                            self.style.ERROR(f'  [X] {error_msg}')
                        )

        except Exception as e:
            raise CommandError(f'Error leyendo el archivo CSV: {str(e)}')

        # Mostrar resumen
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS(f'Importacion completada:')
        )
        self.stdout.write(f'  * {imported_count} polinizaciones nuevas importadas')
        if options['update']:
            self.stdout.write(f'  * {updated_count} polinizaciones actualizadas')
        self.stdout.write(f'  * {skipped_count} registros omitidos')

        if errors:
            self.stdout.write(
                self.style.WARNING(f'  * {len(errors)} errores encontrados')
            )
            self.stdout.write('\nPrimeros 5 errores:')
            for error in errors[:5]:
                self.stdout.write(f'    - {error}')

        self.stdout.write('='*60 + '\n')
