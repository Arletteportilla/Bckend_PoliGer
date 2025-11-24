"""
Comando para calcular predicciones faltantes en germinaciones existentes
"""
from django.core.management.base import BaseCommand
from laboratorio.models import Germinacion
from laboratorio.services.prediccion_service import prediccion_service
from datetime import datetime


class Command(BaseCommand):
    help = 'Calcula predicciones faltantes para germinaciones existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limitar el número de germinaciones a procesar'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recalcular incluso si ya tienen predicción'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        force = options['force']

        self.stdout.write('=' * 70)
        self.stdout.write('   CALCULANDO PREDICCIONES FALTANTES')
        self.stdout.write('=' * 70)
        self.stdout.write('')

        # Filtrar germinaciones
        if force:
            germinaciones = Germinacion.objects.filter(fecha_siembra__isnull=False)
            self.stdout.write(f'Modo FORCE: Recalculando todas las germinaciones con fecha_siembra')
        else:
            germinaciones = Germinacion.objects.filter(
                fecha_siembra__isnull=False,
                prediccion_fecha_estimada__isnull=True
            )
            self.stdout.write(f'Calculando solo germinaciones sin predicción')

        if limit:
            germinaciones = germinaciones[:limit]
            self.stdout.write(f'Limitado a {limit} germinaciones')

        total = germinaciones.count()
        self.stdout.write(f'\nTotal a procesar: {total}')
        self.stdout.write('')

        if total == 0:
            self.stdout.write(self.style.WARNING('No hay germinaciones para procesar'))
            return

        procesadas = 0
        exitosas = 0
        fallidas = 0

        for germinacion in germinaciones:
            procesadas += 1
            
            try:
                # Preparar datos para predicción
                data = {
                    'especie': germinacion.especie_variedad or '',
                    'genero': germinacion.genero or '',
                    'fecha_siembra': germinacion.fecha_siembra.strftime('%Y-%m-%d'),
                    'clima': germinacion.clima or 'I',
                }

                # Calcular predicción
                resultado = prediccion_service.calcular_prediccion_germinacion(data)

                # Guardar en la germinación
                germinacion.prediccion_dias_estimados = resultado.get('dias_estimados')
                germinacion.prediccion_confianza = resultado.get('confianza')
                germinacion.prediccion_fecha_estimada = resultado.get('fecha_estimada')
                germinacion.prediccion_tipo = resultado.get('metodo', 'HEURISTIC')
                germinacion.save()

                exitosas += 1
                
                if procesadas % 10 == 0:
                    self.stdout.write(f'Procesadas: {procesadas}/{total} ({exitosas} exitosas, {fallidas} fallidas)')

            except Exception as e:
                fallidas += 1
                self.stdout.write(self.style.ERROR(f'Error en {germinacion.codigo}: {str(e)}'))

        self.stdout.write('')
        self.stdout.write('=' * 70)
        self.stdout.write(self.style.SUCCESS('   PROCESO COMPLETADO'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'\nTotal procesadas: {procesadas}')
        self.stdout.write(self.style.SUCCESS(f'Exitosas: {exitosas}'))
        if fallidas > 0:
            self.stdout.write(self.style.ERROR(f'Fallidas: {fallidas}'))
        self.stdout.write('')
