"""
Comando para iniciar el scheduler de tareas automáticas.

Este scheduler ejecuta:
1. Envío de recordatorios de 5 días - cada hora
2. Verificación de alertas de revisión - diariamente a las 8:00 AM

IMPORTANTE: Este comando debe ejecutarse como proceso separado o
configurarse para iniciar automáticamente con el servidor.

Formas de ejecutar:
1. Manual: python manage.py iniciar_scheduler
2. Con supervisord/systemd en producción
3. Con Docker como proceso separado
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler import util
import logging
import sys

logger = logging.getLogger(__name__)


def enviar_recordatorios_job():
    """
    Job que ejecuta el comando de recordatorios automáticos.
    Se ejecuta cada hora para verificar registros pendientes.
    """
    from django.core.management import call_command
    from io import StringIO

    logger.info("=" * 50)
    logger.info("🔄 Ejecutando envío de recordatorios automáticos...")
    logger.info("=" * 50)

    try:
        out = StringIO()
        call_command('enviar_recordatorios_automaticos', stdout=out)
        resultado = out.getvalue()
        logger.info(f"✅ Recordatorios completados:\n{resultado}")
    except Exception as e:
        logger.error(f"❌ Error en envío de recordatorios: {e}")


def verificar_alertas_revision_job():
    """
    Job que ejecuta verificación de alertas de revisión.
    Se ejecuta diariamente a las 8:00 AM.
    """
    from django.core.management import call_command
    from io import StringIO

    logger.info("=" * 50)
    logger.info("🔔 Ejecutando verificación de alertas de revisión...")
    logger.info("=" * 50)

    try:
        out = StringIO()
        call_command('generar_alertas_revision', stdout=out)
        resultado = out.getvalue()
        logger.info(f"✅ Alertas de revisión completadas:\n{resultado}")
    except Exception as e:
        logger.error(f"❌ Error en alertas de revisión: {e}")


class Command(BaseCommand):
    help = 'Inicia el scheduler de tareas automáticas para notificaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--intervalo',
            type=int,
            default=60,
            help='Intervalo en minutos para verificar recordatorios (default: 60)'
        )
        parser.add_argument(
            '--hora-revision',
            type=int,
            default=8,
            help='Hora del día para alertas de revisión (default: 8)'
        )
        parser.add_argument(
            '--ejecutar-ahora',
            action='store_true',
            help='Ejecuta los jobs inmediatamente al iniciar'
        )

    def handle(self, *args, **options):
        intervalo_minutos = options['intervalo']
        hora_revision = options['hora_revision']
        ejecutar_ahora = options['ejecutar_ahora']

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'🚀 INICIANDO SCHEDULER DE NOTIFICACIONES\n'
            f'{"="*70}\n'
            f'Intervalo de recordatorios: cada {intervalo_minutos} minutos\n'
            f'Hora de alertas de revisión: {hora_revision}:00\n'
            f'Zona horaria: {settings.TIME_ZONE}\n'
            f'{"="*70}\n'
        ))

        # Crear scheduler
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)

        # Usar DjangoJobStore para persistir jobs
        try:
            scheduler.add_jobstore(DjangoJobStore(), "default")
        except Exception as e:
            logger.warning(f"No se pudo usar DjangoJobStore, usando memoria: {e}")

        # Job 1: Recordatorios de 5 días (cada X minutos)
        scheduler.add_job(
            enviar_recordatorios_job,
            trigger=IntervalTrigger(minutes=intervalo_minutos),
            id='enviar_recordatorios',
            name='Envío de recordatorios automáticos',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )

        self.stdout.write(self.style.SUCCESS(
            f'✅ Job programado: Recordatorios cada {intervalo_minutos} min'
        ))

        # Job 2: Alertas de revisión (diariamente a las X:00)
        scheduler.add_job(
            verificar_alertas_revision_job,
            trigger=CronTrigger(hour=hora_revision, minute=0),
            id='alertas_revision',
            name='Alertas de revisión diarias',
            replace_existing=True,
            max_instances=1,
            coalesce=True
        )

        self.stdout.write(self.style.SUCCESS(
            f'✅ Job programado: Alertas de revisión a las {hora_revision}:00'
        ))

        # Ejecutar inmediatamente si se solicita
        if ejecutar_ahora:
            self.stdout.write(self.style.WARNING(
                '\n🔄 Ejecutando jobs inmediatamente...\n'
            ))
            enviar_recordatorios_job()
            verificar_alertas_revision_job()

        # Iniciar scheduler
        scheduler.start()

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'🟢 SCHEDULER ACTIVO\n'
            f'{"="*70}\n'
            f'Presiona Ctrl+C para detener\n'
        ))

        # Mantener el proceso corriendo
        try:
            import time
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.stdout.write(self.style.WARNING('\n🛑 Deteniendo scheduler...'))
            scheduler.shutdown()
            self.stdout.write(self.style.SUCCESS('✅ Scheduler detenido correctamente'))
