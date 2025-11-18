import csv
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from laboratorio.models import (
    Genero, Especie, Variedad, Ubicacion, Polinizacion, 
    Germinacion, SeguimientoGerminacion
)

class Command(BaseCommand):
    help = 'Importa datos de polinizaciones y germinaciones desde archivos CSV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--polinizaciones',
            type=str,
            help='Ruta al archivo CSV de polinizaciones'
        )
        parser.add_argument(
            '--germinaciones',
            type=str,
            help='Ruta al archivo CSV de germinaciones'
        )
        parser.add_argument(
            '--user',
            type=str,
            default='admin',
            help='Usuario que será asignado como responsable (default: admin)'
        )

    def handle(self, *args, **options):
        # Obtener o crear usuario
        try:
            user = User.objects.get(username=options['user'])
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f'Usuario {options["user"]} no encontrado. Creando usuario...')
            )
            user = User.objects.create_user(
                username=options['user'],
                email=f'{options["user"]}@example.com',
                password='temp_password_123'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Usuario {options["user"]} creado exitosamente')
            )

        # Importar polinizaciones si se proporciona el archivo
        if options['polinizaciones']:
            self.import_polinizaciones(options['polinizaciones'], user)

        # Importar germinaciones si se proporciona el archivo
        if options['germinaciones']:
            self.import_germinaciones(options['germinaciones'], user)

    def import_polinizaciones(self, file_path, user):
        """Importa datos de polinizaciones desde un archivo CSV"""
        if not os.path.exists(file_path):
            raise CommandError(f'El archivo {file_path} no existe')

        self.stdout.write(f'Importando polinizaciones desde {file_path}...')

        imported_count = 0
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row_num, row in enumerate(reader, start=2):  # Empezar en 2 porque la fila 1 es el header
                    try:
                        # Crear o obtener género
                        genero, created = Genero.objects.get_or_create(
                            nombre=row.get('genero', '').strip()
                        )
                        
                        # Crear o obtener especie
                        especie, created = Especie.objects.get_or_create(
                            nombre=row.get('especie', '').strip(),
                            genero=genero
                        )
                        
                        # Crear o obtener variedad
                        variedad, created = Variedad.objects.get_or_create(
                            nombre=row.get('variedad', '').strip(),
                            especie=especie,
                            defaults={
                                'temporada_inicio': row.get('temporada_inicio', 'PRIMAVERA'),
                                'temporada_polinizacion': row.get('temporada_polinizacion', 'PRIMAVERA'),
                                'dias_germinacion_min': int(row.get('dias_germinacion_min', 30)),
                                'dias_germinacion_max': int(row.get('dias_germinacion_max', 60))
                            }
                        )
                        
                        # Crear o obtener ubicación
                        ubicacion = None
                        if row.get('ubicacion'):
                            ubicacion, created = Ubicacion.objects.get_or_create(
                                nombre=row.get('ubicacion', '').strip()
                            )
                        
                        # Procesar fechas
                        fecha_pol = datetime.strptime(row.get('fecha_pol', ''), '%Y-%m-%d').date()
                        fecha_mad = None
                        if row.get('fecha_mad'):
                            fecha_mad = datetime.strptime(row.get('fecha_mad', ''), '%Y-%m-%d').date()
                        
                        fecha_siembra = None
                        if row.get('fecha_siembra'):
                            fecha_siembra = datetime.strptime(row.get('fecha_siembra', ''), '%Y-%m-%d').date()
                        
                        fecha_replante = None
                        if row.get('fecha_replante'):
                            fecha_replante = datetime.strptime(row.get('fecha_replante', ''), '%Y-%m-%d').date()
                        
                        # Crear polinización
                        polinizacion = Polinizacion.objects.create(
                            fecha_pol=fecha_pol,
                            fecha_mad=fecha_mad,
                            codigo=row.get('codigo', '').strip(),
                            variedad=variedad,
                            ubicacion=ubicacion,
                            responsable=user,
                            cantidad=int(row.get('cantidad', 1)),
                            disponible=row.get('disponible', 'True').lower() == 'true',
                            archivo_origen=row.get('archivo_origen', ''),
                            fecha_siembra=fecha_siembra,
                            fecha_replante=fecha_replante,
                            clima=row.get('clima', ''),
                            cantidad_solicitada=int(row.get('cantidad_solicitada', 0)),
                            estado=row.get('estado', 'EN_PROCESO'),
                            observaciones=row.get('observaciones', '')
                        )
                        
                        imported_count += 1
                        self.stdout.write(f'  ✓ Polinización {polinizacion.codigo} importada')
                        
                    except Exception as e:
                        error_msg = f"Error en fila {row_num}: {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ {error_msg}')
                        )

        except Exception as e:
            raise CommandError(f'Error leyendo el archivo CSV: {str(e)}')

        # Mostrar resumen
        self.stdout.write(
            self.style.SUCCESS(f'\nImportación completada: {imported_count} polinizaciones importadas')
        )
        if errors:
            self.stdout.write(
                self.style.WARNING(f'{len(errors)} errores encontrados')
            )

    def import_germinaciones(self, file_path, user):
        """Importa datos de germinaciones desde un archivo CSV"""
        if not os.path.exists(file_path):
            raise CommandError(f'El archivo {file_path} no existe')

        self.stdout.write(f'Importando germinaciones desde {file_path}...')

        imported_count = 0
        errors = []

        try:
            with open(file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        # Buscar polinización por código si se proporciona
                        polinizacion = None
                        if row.get('codigo_polinizacion'):
                            try:
                                polinizacion = Polinizacion.objects.get(
                                    codigo=row.get('codigo_polinizacion', '').strip()
                                )
                            except Polinizacion.DoesNotExist:
                                self.stdout.write(
                                    self.style.WARNING(f'  ⚠ Polinización {row.get("codigo_polinizacion")} no encontrada')
                                )
                        
                        # Procesar fechas
                        fecha_ingreso = datetime.strptime(row.get('fecha_ingreso', ''), '%Y-%m-%d').date()
                        fecha_polinizacion = datetime.strptime(row.get('fecha_polinizacion', ''), '%Y-%m-%d').date()
                        
                        # Calcular días desde polinización
                        dias_polinizacion = (fecha_ingreso - fecha_polinizacion).days
                        
                        # Crear germinación
                        germinacion = Germinacion.objects.create(
                            fecha_ingreso=fecha_ingreso,
                            fecha_polinizacion=fecha_polinizacion,
                            dias_polinizacion=dias_polinizacion,
                            nombre=row.get('nombre', '').strip(),
                            detalles_padres=row.get('detalles_padres', ''),
                            tipo_polinizacion=row.get('tipo_polinizacion', ''),
                            finca=row.get('finca', ''),
                            numero_vivero=row.get('numero_vivero', ''),
                            numero_capsulas=int(row.get('numero_capsulas', 0)),
                            estado_capsulas=row.get('estado_capsulas', 'BUENO'),
                            cantidad_solicitada=int(row.get('cantidad_solicitada', 0)),
                            entrega_capsulas=row.get('entrega_capsulas', ''),
                            recibe_capsulas=row.get('recibe_capsulas', ''),
                            etapa_actual=row.get('etapa_actual', 'SIEMBRA'),
                            polinizacion=polinizacion,
                            observaciones=row.get('observaciones', '')
                        )
                        
                        imported_count += 1
                        self.stdout.write(f'  ✓ Germinación {germinacion.nombre} importada')
                        
                    except Exception as e:
                        error_msg = f"Error en fila {row_num}: {str(e)}"
                        errors.append(error_msg)
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ {error_msg}')
                        )

        except Exception as e:
            raise CommandError(f'Error leyendo el archivo CSV: {str(e)}')

        # Mostrar resumen
        self.stdout.write(
            self.style.SUCCESS(f'\nImportación completada: {imported_count} germinaciones importadas')
        )
        if errors:
            self.stdout.write(
                self.style.WARNING(f'{len(errors)} errores encontrados')
            ) 