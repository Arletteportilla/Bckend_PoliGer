"""
Management command para completar el campo 'genero' en Germinaciones
basándose en las coincidencias de especie con la tabla Polinizaciones.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from laboratorio.core.models import Germinacion, Polinizacion


class Command(BaseCommand):
    help = 'Completa el campo genero en Germinaciones basándose en las especies de Polinizaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular la operación sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('=== MODO SIMULACIÓN (dry-run) ===\n'))

        # Obtener germinaciones con genero vacío o nulo
        germinaciones_sin_genero = Germinacion.objects.filter(
            Q(genero__isnull=True) | Q(genero='')
        ).exclude(
            Q(especie_variedad__isnull=True) | Q(especie_variedad='')
        )

        total_germinaciones = germinaciones_sin_genero.count()
        self.stdout.write(f'Germinaciones sin género (con especie): {total_germinaciones}\n')

        if total_germinaciones == 0:
            self.stdout.write(self.style.SUCCESS('No hay germinaciones que actualizar.'))
            return

        # Crear un diccionario de especie -> género desde Polinizaciones
        # Buscar en todos los campos de especie disponibles
        especie_genero_map = {}

        # Obtener todas las polinizaciones con especie y género válidos
        polinizaciones = Polinizacion.objects.all()

        for pol in polinizaciones:
            # Campo legacy especie -> genero
            if pol.especie and pol.genero:
                especie_clean = pol.especie.strip().lower()
                if especie_clean and especie_clean not in especie_genero_map:
                    especie_genero_map[especie_clean] = pol.genero.strip()

            # madre_especie -> madre_genero
            if pol.madre_especie and pol.madre_genero:
                especie_clean = pol.madre_especie.strip().lower()
                if especie_clean and especie_clean not in especie_genero_map:
                    especie_genero_map[especie_clean] = pol.madre_genero.strip()

            # padre_especie -> padre_genero
            if pol.padre_especie and pol.padre_genero:
                especie_clean = pol.padre_especie.strip().lower()
                if especie_clean and especie_clean not in especie_genero_map:
                    especie_genero_map[especie_clean] = pol.padre_genero.strip()

            # nueva_especie -> nueva_genero
            if pol.nueva_especie and pol.nueva_genero:
                especie_clean = pol.nueva_especie.strip().lower()
                if especie_clean and especie_clean not in especie_genero_map:
                    especie_genero_map[especie_clean] = pol.nueva_genero.strip()

        self.stdout.write(f'Especies únicas encontradas en Polinizaciones: {len(especie_genero_map)}\n')

        # Procesar germinaciones
        actualizadas = 0
        no_encontradas = []

        for ger in germinaciones_sin_genero:
            especie_ger = ger.especie_variedad.strip().lower() if ger.especie_variedad else ''

            if especie_ger in especie_genero_map:
                genero_encontrado = especie_genero_map[especie_ger]

                if dry_run:
                    self.stdout.write(
                        f'  [SIMULADO] {ger.codigo}: "{ger.especie_variedad}" -> Género: "{genero_encontrado}"'
                    )
                else:
                    ger.genero = genero_encontrado
                    ger.save(update_fields=['genero'])
                    self.stdout.write(
                        self.style.SUCCESS(f'  [OK] {ger.codigo}: "{ger.especie_variedad}" -> Genero: "{genero_encontrado}"')
                    )
                actualizadas += 1
            else:
                no_encontradas.append({
                    'codigo': ger.codigo,
                    'especie': ger.especie_variedad
                })

        # Resumen
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(f'\nRESUMEN:'))
        self.stdout.write(f'  - Total germinaciones procesadas: {total_germinaciones}')
        self.stdout.write(f'  - Actualizadas con género: {actualizadas}')
        self.stdout.write(f'  - No encontradas en Polinizaciones: {len(no_encontradas)}')

        if no_encontradas:
            self.stdout.write(self.style.WARNING('\nEspecies NO encontradas en Polinizaciones:'))
            # Mostrar especies únicas no encontradas
            especies_unicas = set(item['especie'] for item in no_encontradas if item['especie'])
            for especie in sorted(especies_unicas):
                self.stdout.write(f'  - "{especie}"')

        if dry_run:
            self.stdout.write(self.style.WARNING('\n*** Este fue un dry-run. Ejecuta sin --dry-run para aplicar los cambios. ***'))
