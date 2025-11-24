"""
Comando para calcular predicciones faltantes de polinizaciones
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from laboratorio.models import Polinizacion
from laboratorio.services.ml_polinizacion_service import ml_polinizacion_service
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calcula predicciones de maduración para polinizaciones que no las tienen'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalcular predicciones incluso si ya existen'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limitar el número de polinizaciones a procesar'
        )

    def handle(self, *args, **options):
        force = options['force']
        limit = options['limit']

        self.stdout.write('=' * 80)
        self.stdout.write('   CÁLCULO DE PREDICCIONES DE MADURACIÓN')
        self.stdout.write('=' * 80)
        self.stdout.write('')

        # Verificar que el modelo esté cargado
        model_info = ml_polinizacion_service.get_model_info()
        if not model_info['loaded']:
            self.stdout.write(self.style.ERROR(
                '✗ Modelo de ML no está cargado. Ejecute train_polinizacion_model primero.'
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"✓ Modelo cargado: {model_info['modelo']}"
        ))
        self.stdout.write(f"  Precisión: {model_info.get('precision_percent', 'N/A')}%")
        self.stdout.write(f"  MAE: {model_info.get('mae_test', 'N/A')} días")
        self.stdout.write('')

        # Buscar polinizaciones sin predicción
        if force:
            queryset = Polinizacion.objects.filter(
                fechapol__isnull=False
            ).exclude(
                genero='',
                especie=''
            )
            self.stdout.write('Modo: Recalcular todas las predicciones')
        else:
            queryset = Polinizacion.objects.filter(
                Q(dias_maduracion_predichos__isnull=True) | Q(dias_maduracion_predichos=0),
                fechapol__isnull=False
            ).exclude(
                genero='',
                especie=''
            )
            self.stdout.write('Modo: Solo polinizaciones sin predicción')

        total = queryset.count()

        if limit:
            queryset = queryset[:limit]
            self.stdout.write(f'Limitando a {limit} polinizaciones')

        self.stdout.write(f'\nPolinizaciones a procesar: {queryset.count()} de {total}')
        self.stdout.write('')

        if queryset.count() == 0:
            self.stdout.write(self.style.SUCCESS('✓ No hay polinizaciones para procesar'))
            return

        # Procesar polinizaciones
        procesadas = 0
        exitosas = 0
        fallidas = 0

        for polinizacion in queryset:
            procesadas += 1

            try:
                # Obtener datos necesarios
                genero = polinizacion.genero or polinizacion.nueva_genero or ''
                especie = polinizacion.especie or polinizacion.nueva_especie or ''
                tipo = polinizacion.Tipo or polinizacion.tipo_polinizacion or 'SELF'
                fecha_pol = polinizacion.fechapol
                cantidad = polinizacion.cantidad or 1

                if not genero or not especie:
                    self.stdout.write(
                        f'  [{procesadas}/{queryset.count()}] '
                        f'Polinización {polinizacion.numero}: Sin género/especie - OMITIDA'
                    )
                    continue

                # Hacer predicción
                prediccion = ml_polinizacion_service.predecir_dias_maduracion(
                    genero=genero,
                    especie=especie,
                    tipo=tipo,
                    fecha_pol=fecha_pol,
                    cantidad=cantidad
                )

                if prediccion:
                    # Actualizar polinizacion
                    polinizacion.dias_maduracion_predichos = prediccion['dias_estimados']
                    polinizacion.fecha_maduracion_predicha = prediccion['fecha_estimada']
                    polinizacion.metodo_prediccion = prediccion['metodo']
                    polinizacion.confianza_prediccion = prediccion['confianza']
                    polinizacion.save()

                    exitosas += 1
                    self.stdout.write(
                        f'  [{procesadas}/{queryset.count()}] '
                        f'Polinización {polinizacion.numero}: '
                        f'{prediccion["dias_estimados"]} días '
                        f'(confianza: {prediccion["confianza"]:.1f}%) - OK'
                    )
                else:
                    fallidas += 1
                    self.stdout.write(
                        f'  [{procesadas}/{queryset.count()}] '
                        f'Polinización {polinizacion.numero}: Sin predicción - FALLIDA'
                    )

            except Exception as e:
                fallidas += 1
                self.stdout.write(
                    f'  [{procesadas}/{queryset.count()}] '
                    f'Polinización {polinizacion.numero}: Error - {str(e)}'
                )
                logger.error(f"Error procesando polinización {polinizacion.numero}: {e}")

        # Resumen
        self.stdout.write('')
        self.stdout.write('=' * 80)
        self.stdout.write('   RESUMEN')
        self.stdout.write('=' * 80)
        self.stdout.write(f'\n  Total procesadas: {procesadas}')
        self.stdout.write(self.style.SUCCESS(f'  Exitosas: {exitosas}'))
        if fallidas > 0:
            self.stdout.write(self.style.WARNING(f'  Fallidas: {fallidas}'))
        self.stdout.write('')
