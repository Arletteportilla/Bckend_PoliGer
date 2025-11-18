from django.core.management.base import BaseCommand
import pandas as pd
from laboratorio.core.models import Polinizacion, Germinacion
from django.contrib.auth.models import User
from django.utils.dateparse import parse_date
import numpy as np

class Command(BaseCommand):
    help = 'Reimporta los datos desde los CSV, eliminando los datos existentes en las tablas.'

    def handle(self, *args, **options):
        # Eliminar datos existentes
        Polinizacion.objects.all().delete()
        Germinacion.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Datos existentes eliminados.'))

        # Obtener un superusuario para asignar a los registros
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            self.stdout.write(self.style.WARNING('No se encontró un superusuario. Los registros se crearán sin un creador asignado.'))

        # Cargar y procesar datos de Polinización
        try:
            df_polinizacion = pd.read_csv('data/datos_combinados_limpios.csv')
            self.stdout.write(self.style.SUCCESS(f'Datos de polinización cargados: {len(df_polinizacion)} filas.'))

            codigos_usados = set()
            for _, row in df_polinizacion.iterrows():
                # Limpieza y conversión de fechas
                fechapol = parse_date(row['fechapol']) if pd.notna(row['fechapol']) else None
                fechamad = parse_date(row['fechamad']) if pd.notna(row['fechamad']) else None

                codigo = row.get('codigo', '')
                if codigo in codigos_usados:
                    i = 1
                    while f'{codigo}_{i}' in codigos_usados:
                        i += 1
                    codigo = f'{codigo}_{i}'
                codigos_usados.add(codigo)

                disponible_val = row.get('disponible', True)
                if isinstance(disponible_val, str):
                    disponible = disponible_val.lower() in ['t', 'true', '1', '-1', '-2']
                else:
                    disponible = bool(disponible_val)

                Polinizacion.objects.create(
                    fechapol=fechapol,
                    fechamad=fechamad,
                    codigo=codigo,
                    responsable=row.get('responsable', ''),
                    disponible=disponible,
                    genero=row.get('genero', ''),
                    especie=row.get('especie', ''),
                    ubicacion=row.get('ubicacion', ''),
                    cantidad=row.get('cantidad', 1),
                    archivo_origen=row.get('archivo_origen', ''),
                    creado_por=admin_user
                )
            self.stdout.write(self.style.SUCCESS('Datos de polinización importados correctamente.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("Error: El archivo 'data/datos_combinados_limpios.csv' no fue encontrado."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al importar datos de polinización: {e}"))

        # Cargar y procesar datos de Germinación
        try:
            df_germinacion = pd.read_csv('data/Germinacion_Consolidado - Consolidado.csv')
            self.stdout.write(self.style.SUCCESS(f'Datos de germinación cargados: {len(df_germinacion)} filas.'))

            for _, row in df_germinacion.iterrows():
                # Limpieza y conversión de fechas
                fecha_ingreso = parse_date(row['FECHA DE INGRESO']) if pd.notna(row['FECHA DE INGRESO']) else None
                fecha_polinizacion = parse_date(row['FECHA DE POLINIZACIÓN']) if pd.notna(row['FECHA DE POLINIZACIÓN']) else None
                dias_polinizacion = row.get('No_dias_pol', None)
                if pd.isna(dias_polinizacion):
                    dias_polinizacion = None
                
                numero_capsulas = row.get('No_CAPSULAS', None)
                if pd.isna(numero_capsulas):
                    numero_capsulas = None

                Germinacion.objects.create(
                    fecha_ingreso=fecha_ingreso,
                    fecha_polinizacion=fecha_polinizacion,
                    dias_polinizacion=dias_polinizacion,
                    nombre=row.get('NOMBRE', ''),
                    detalles_padres=row.get('DETALLES DE PADRES DEL HIBRIDO', ''),
                    tipo_polinizacion=row.get('TIPO POLINIZ', ''),
                    finca=row.get('FINCA', ''),
                    numero_vivero=row.get('No_VIVERO', ''),
                    numero_capsulas=numero_capsulas,
                    estado_capsula=row.get('ESTADO DE CAPSULAS', ''),
                    entrega_capsulas=row.get('ENTREGA CAPSULAS', ''),
                    recibe_capsulas=row.get('RECIBE CAPSULAS', ''),
                    etapa_actual=row.get('Etapa', ''),
                    creado_por=admin_user
                )
            self.stdout.write(self.style.SUCCESS('Datos de germinación importados correctamente.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("Error: El archivo 'data/Germinacion_Consolidado - Consolidado.csv' no fue encontrado."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error al importar datos de germinación: {e}"))