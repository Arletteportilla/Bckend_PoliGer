# -*- coding: utf-8 -*-
"""
Marca los registros importados históricamente como 'historico'
en el campo archivo_origen, para que no sean contados en
los conteos de reentrenamiento del sistema.

Uso:
    python manage.py marcar_datos_historicos --fecha-corte 2025-12-01
    python manage.py marcar_datos_historicos --fecha-corte 2025-12-01 --dry-run

Los registros con fecha_creacion anterior a --fecha-corte y archivo_origen=''
se consideran históricos y se les asigna archivo_origen='historico'.
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils import timezone
import datetime


class Command(BaseCommand):
    help = 'Marca registros importados históricamente para excluirlos del reentrenamiento.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha-corte',
            type=str,
            required=True,
            help='Fecha de corte YYYY-MM-DD. Registros creados ANTES de esta fecha se marcan como históricos.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Muestra cuántos registros se afectarían sin aplicar cambios.',
        )

    def handle(self, *args, **options):
        fecha_str = options['fecha_corte']
        dry_run = options['dry_run']

        try:
            fecha_corte = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').replace(
                tzinfo=timezone.get_current_timezone()
            )
        except ValueError:
            raise CommandError(f'Fecha inválida: {fecha_str}. Use formato YYYY-MM-DD.')

        from laboratorio.core.models import Polinizacion, Germinacion

        pol_qs = Polinizacion.objects.filter(
            archivo_origen='',
            fecha_creacion__lt=fecha_corte,
        )
        germ_qs = Germinacion.objects.filter(
            archivo_origen='',
            fecha_creacion__lt=fecha_corte,
        )

        pol_count = pol_qs.count()
        germ_count = germ_qs.count()

        self.stdout.write(f'Registros a marcar como históricos:')
        self.stdout.write(f'  Polinizaciones: {pol_count}')
        self.stdout.write(f'  Germinaciones:  {germ_count}')

        if dry_run:
            self.stdout.write(self.style.WARNING('(Dry-run: no se realizaron cambios)'))
            return

        if pol_count == 0 and germ_count == 0:
            self.stdout.write(self.style.WARNING('No hay registros para marcar.'))
            return

        pol_updated = pol_qs.update(archivo_origen='historico')
        germ_updated = germ_qs.update(archivo_origen='historico')

        self.stdout.write(self.style.SUCCESS(
            f'Marcados como historico: {pol_updated} polinizaciones, {germ_updated} germinaciones.'
        ))
        self.stdout.write(self.style.SUCCESS(
            'Los conteos de reentrenamiento ahora mostrarán solo registros del sistema.'
        ))
