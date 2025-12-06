"""
Comando para generar notificaciones de recordatorio para germinaciones y polinizaciones
que llevan más de 5 días en estado INICIAL
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from laboratorio.models import Germinacion, Polinizacion, Notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera notificaciones de recordatorio para registros en estado INICIAL después de 5 días'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=5,
            help='Número de días después de los cuales generar recordatorio (default: 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin crear notificaciones'
        )

    def handle(self, *args, **options):
        dias_limite = options['dias']
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'Generando notificaciones de recordatorio\n'
            f'Días límite: {dias_limite}\n'
            f'Modo: {"DRY RUN (simulación)" if dry_run else "PRODUCCIÓN"}\n'
            f'{"="*70}\n'
        ))
        
        # Calcular fecha límite (hace X días)
        fecha_limite = date.today() - timedelta(days=dias_limite)
        
        # Procesar germinaciones
        notificaciones_germinacion = self._procesar_germinaciones(fecha_limite, dry_run)
        
        # Procesar polinizaciones
        notificaciones_polinizacion = self._procesar_polinizaciones(fecha_limite, dry_run)
        
        # Resumen
        total = notificaciones_germinacion + notificaciones_polinizacion
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'RESUMEN:\n'
            f'  - Notificaciones de germinación: {notificaciones_germinacion}\n'
            f'  - Notificaciones de polinización: {notificaciones_polinizacion}\n'
            f'  - Total: {total}\n'
            f'{"="*70}\n'
        ))
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  Modo DRY RUN: No se crearon notificaciones reales\n'
            ))

    def _procesar_germinaciones(self, fecha_limite, dry_run):
        """Procesa germinaciones en estado INICIAL"""
        self.stdout.write('\n📋 Procesando germinaciones...\n')
        
        # Buscar germinaciones en estado INICIAL creadas antes de la fecha límite
        germinaciones = Germinacion.objects.filter(
            estado_germinacion='INICIAL',
            fecha_siembra__lte=fecha_limite,
            creado_por__isnull=False
        ).select_related('creado_por')
        
        count = 0
        for germ in germinaciones:
            # Verificar si ya existe una notificación de recordatorio reciente (últimas 24 horas)
            notificacion_reciente = Notification.objects.filter(
                usuario=germ.creado_por,
                germinacion=germ,
                tipo='RECORDATORIO_REVISION',
                fecha_creacion__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if notificacion_reciente:
                self.stdout.write(self.style.WARNING(
                    f'  ⏭️  Germinación {germ.codigo} - Ya tiene notificación reciente'
                ))
                continue
            
            dias_transcurridos = (date.today() - germ.fecha_siembra).days if germ.fecha_siembra else 0
            
            self.stdout.write(self.style.SUCCESS(
                f'  ✅ Germinación {germ.codigo} - {dias_transcurridos} días en INICIAL'
            ))
            
            if not dry_run:
                self._crear_notificacion_germinacion(germ, dias_transcurridos)
            
            count += 1
        
        return count

    def _procesar_polinizaciones(self, fecha_limite, dry_run):
        """Procesa polinizaciones en estado INICIAL"""
        self.stdout.write('\n🌸 Procesando polinizaciones...\n')
        
        # Buscar polinizaciones en estado INICIAL creadas antes de la fecha límite
        polinizaciones = Polinizacion.objects.filter(
            estado_polinizacion='INICIAL',
            fechapol__lte=fecha_limite,
            creado_por__isnull=False
        ).select_related('creado_por')
        
        count = 0
        for pol in polinizaciones:
            # Verificar si ya existe una notificación de recordatorio reciente (últimas 24 horas)
            notificacion_reciente = Notification.objects.filter(
                usuario=pol.creado_por,
                polinizacion=pol,
                tipo='RECORDATORIO_REVISION',
                fecha_creacion__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if notificacion_reciente:
                self.stdout.write(self.style.WARNING(
                    f'  ⏭️  Polinización {pol.codigo} - Ya tiene notificación reciente'
                ))
                continue
            
            dias_transcurridos = (date.today() - pol.fechapol).days if pol.fechapol else 0
            
            self.stdout.write(self.style.SUCCESS(
                f'  ✅ Polinización {pol.codigo} - {dias_transcurridos} días en INICIAL'
            ))
            
            if not dry_run:
                self._crear_notificacion_polinizacion(pol, dias_transcurridos)
            
            count += 1
        
        return count

    def _crear_notificacion_germinacion(self, germinacion, dias_transcurridos):
        """Crea una notificación de recordatorio para una germinación"""
        try:
            titulo = f"⏰ Recordatorio: Germinación {germinacion.codigo} lleva {dias_transcurridos} días sin iniciar"
            
            mensaje = (
                f"La germinación {germinacion.codigo} de {germinacion.genero} {germinacion.especie_variedad} "
                f"lleva {dias_transcurridos} días en estado INICIAL.\n\n"
                f"📅 Fecha de siembra: {germinacion.fecha_siembra.strftime('%d/%m/%Y') if germinacion.fecha_siembra else 'N/A'}\n"
            )
            
            if germinacion.prediccion_fecha_estimada:
                dias_restantes = (germinacion.prediccion_fecha_estimada - date.today()).days
                mensaje += (
                    f"🔮 Fecha estimada de germinación: {germinacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')}\n"
                    f"⏳ Días restantes: {dias_restantes}\n\n"
                )
            
            mensaje += "💡 Considera iniciar el proceso de seguimiento para un mejor control."
            
            detalles = {
                'germinacion_id': germinacion.id,
                'codigo': germinacion.codigo,
                'genero': germinacion.genero,
                'especie': germinacion.especie_variedad,
                'fecha_siembra': str(germinacion.fecha_siembra) if germinacion.fecha_siembra else None,
                'dias_transcurridos': dias_transcurridos,
                'estado': germinacion.estado_germinacion,
                'tipo_recordatorio': 'estado_inicial_prolongado'
            }
            
            Notification.objects.create(
                usuario=germinacion.creado_por,
                germinacion=germinacion,
                tipo='RECORDATORIO_REVISION',
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )
            
            logger.info(f"Notificación de recordatorio creada para germinación {germinacion.id}")
            
        except Exception as e:
            logger.error(f"Error creando notificación para germinación {germinacion.id}: {e}")
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))

    def _crear_notificacion_polinizacion(self, polinizacion, dias_transcurridos):
        """Crea una notificación de recordatorio para una polinización"""
        try:
            titulo = f"⏰ Recordatorio: Polinización {polinizacion.codigo} lleva {dias_transcurridos} días sin iniciar"
            
            mensaje = (
                f"La polinización {polinizacion.codigo} tipo {polinizacion.tipo_polinizacion} "
                f"lleva {dias_transcurridos} días en estado INICIAL.\n\n"
                f"📅 Fecha de polinización: {polinizacion.fechapol.strftime('%d/%m/%Y') if polinizacion.fechapol else 'N/A'}\n"
            )
            
            if polinizacion.madre_especie:
                mensaje += f"🌱 Madre: {polinizacion.madre_genero} {polinizacion.madre_especie}\n"
            
            if polinizacion.padre_especie and polinizacion.tipo_polinizacion != 'SELF':
                mensaje += f"🌱 Padre: {polinizacion.padre_genero} {polinizacion.padre_especie}\n"
            
            if polinizacion.prediccion_fecha_estimada:
                dias_restantes = (polinizacion.prediccion_fecha_estimada - date.today()).days
                mensaje += (
                    f"\n🔮 Fecha estimada de maduración: {polinizacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')}\n"
                    f"⏳ Días restantes: {dias_restantes}\n\n"
                )
            
            mensaje += "💡 Considera iniciar el proceso de seguimiento para un mejor control."
            
            detalles = {
                'polinizacion_id': polinizacion.numero,
                'codigo': polinizacion.codigo,
                'tipo_polinizacion': polinizacion.tipo_polinizacion,
                'madre_especie': polinizacion.madre_especie,
                'padre_especie': polinizacion.padre_especie,
                'fecha_polinizacion': str(polinizacion.fechapol) if polinizacion.fechapol else None,
                'dias_transcurridos': dias_transcurridos,
                'estado': polinizacion.estado_polinizacion,
                'tipo_recordatorio': 'estado_inicial_prolongado'
            }
            
            Notification.objects.create(
                usuario=polinizacion.creado_por,
                polinizacion=polinizacion,
                tipo='RECORDATORIO_REVISION',
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )
            
            logger.info(f"Notificación de recordatorio creada para polinización {polinizacion.numero}")
            
        except Exception as e:
            logger.error(f"Error creando notificación para polinización {polinizacion.numero}: {e}")
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))
