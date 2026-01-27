"""
Comando de Django para generar alertas de revisión automáticas
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date
from laboratorio.core.models import Polinizacion, Germinacion, Notification
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Genera alertas de revisión para polinizaciones y germinaciones que necesitan ser revisadas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecutar en modo de prueba sin crear notificaciones reales',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        hoy = timezone.now().date()
        
        self.stdout.write(
            self.style.SUCCESS(f'🔍 Generando alertas de revisión para {hoy}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('⚠️ Modo de prueba activado - No se crearán notificaciones reales')
            )

        # Generar alertas para polinizaciones
        alertas_polinizacion = self.generar_alertas_polinizacion(hoy, dry_run)
        
        # Generar alertas para germinaciones
        alertas_germinacion = self.generar_alertas_germinacion(hoy, dry_run)
        
        total_alertas = alertas_polinizacion + alertas_germinacion
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Proceso completado:\n'
                f'   - Alertas de polinización: {alertas_polinizacion}\n'
                f'   - Alertas de germinación: {alertas_germinacion}\n'
                f'   - Total de alertas generadas: {total_alertas}'
            )
        )

    def generar_alertas_polinizacion(self, hoy, dry_run=False):
        """Genera alertas para polinizaciones que necesitan revisión"""
        # Buscar polinizaciones que necesitan revisión hoy
        polinizaciones_pendientes = Polinizacion.objects.filter(
            fecha_proxima_revision__lte=hoy,
            alerta_revision_enviada=False,
            estado_polinizacion__in=['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO']
        )
        
        alertas_creadas = 0
        
        for polinizacion in polinizaciones_pendientes:
            try:
                # Determinar el usuario destinatario
                usuario_destinatario = polinizacion.creado_por
                if not usuario_destinatario:
                    # Buscar por responsable si no hay creado_por
                    try:
                        usuario_destinatario = User.objects.get(username=polinizacion.responsable)
                    except User.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠️ No se encontró usuario para polinización {polinizacion.numero}'
                            )
                        )
                        continue
                
                # Calcular días transcurridos
                dias_transcurridos = (hoy - polinizacion.fecha_creacion.date()).days if polinizacion.fecha_creacion else 0
                
                # Crear mensaje personalizado
                titulo = f"🌸 Revisión de Polinización Pendiente"
                mensaje = (
                    f"Es hora de revisar la polinización {polinizacion.codigo or polinizacion.numero}.\n\n"
                    f"📊 Estado actual: {polinizacion.get_estado_polinizacion_display()}\n"
                    f"📈 Progreso: {polinizacion.progreso_polinizacion}%\n"
                    f"🌱 Especie: {polinizacion.madre_genero} {polinizacion.madre_especie}\n"
                    f"📅 Creada hace: {dias_transcurridos} días\n"
                    f"👤 Responsable: {polinizacion.responsable}\n\n"
                    f"💡 Revisa el estado y actualiza el progreso según corresponda."
                )
                
                if not dry_run:
                    # Crear la notificación
                    notificacion = Notification.objects.create(
                        usuario=usuario_destinatario,
                        polinizacion=polinizacion,
                        tipo='RECORDATORIO_REVISION',
                        titulo=titulo,
                        mensaje=mensaje,
                        detalles_adicionales={
                            'tipo_registro': 'polinizacion',
                            'registro_id': polinizacion.numero,
                            'fecha_creacion': polinizacion.fecha_creacion.isoformat() if polinizacion.fecha_creacion else None,
                            'fecha_revision_programada': polinizacion.fecha_proxima_revision.isoformat(),
                            'dias_transcurridos': dias_transcurridos,
                            'estado_actual': polinizacion.estado_polinizacion,
                            'progreso_actual': polinizacion.progreso_polinizacion
                        }
                    )
                    
                    # Marcar como enviada
                    polinizacion.alerta_revision_enviada = True
                    polinizacion.save()
                    
                    logger.info(f"Alerta de revisión creada para polinización {polinizacion.numero}")
                
                alertas_creadas += 1
                
                self.stdout.write(
                    f'📧 {"[DRY-RUN] " if dry_run else ""}Alerta creada para polinización {polinizacion.numero} '
                    f'(Usuario: {usuario_destinatario.username})'
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error creando alerta para polinización {polinizacion.numero}: {e}'
                    )
                )
                logger.error(f"Error creando alerta para polinización {polinizacion.numero}: {e}")
        
        return alertas_creadas

    def generar_alertas_germinacion(self, hoy, dry_run=False):
        """Genera alertas para germinaciones que necesitan revisión"""
        # Buscar germinaciones que necesitan revisión hoy
        germinaciones_pendientes = Germinacion.objects.filter(
            fecha_proxima_revision__lte=hoy,
            alerta_revision_enviada=False,
            estado_germinacion__in=['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO']
        )
        
        alertas_creadas = 0
        
        for germinacion in germinaciones_pendientes:
            try:
                # Determinar el usuario destinatario
                usuario_destinatario = germinacion.creado_por
                if not usuario_destinatario:
                    # Buscar por responsable si no hay creado_por
                    try:
                        usuario_destinatario = User.objects.get(username=germinacion.responsable)
                    except User.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f'⚠️ No se encontró usuario para germinación {germinacion.id}'
                            )
                        )
                        continue
                
                # Calcular días transcurridos
                dias_transcurridos = (hoy - germinacion.fecha_creacion.date()).days if germinacion.fecha_creacion else 0
                
                # Crear mensaje personalizado
                titulo = f"🌱 Revisión de Germinación Pendiente"
                mensaje = (
                    f"Es hora de revisar la germinación {germinacion.codigo}.\n\n"
                    f"📊 Estado actual: {germinacion.get_estado_germinacion_display()}\n"
                    f"📈 Progreso: {germinacion.progreso_germinacion}%\n"
                    f"🌿 Especie: {germinacion.genero} {germinacion.especie_variedad}\n"
                    f"📅 Creada hace: {dias_transcurridos} días\n"
                    f"👤 Responsable: {germinacion.responsable}\n"
                    f"🧪 Cápsulas: {germinacion.no_capsulas}\n\n"
                    f"💡 Revisa el estado de las cápsulas y actualiza el progreso según corresponda."
                )
                
                if not dry_run:
                    # Crear la notificación
                    notificacion = Notification.objects.create(
                        usuario=usuario_destinatario,
                        germinacion=germinacion,
                        tipo='RECORDATORIO_REVISION',
                        titulo=titulo,
                        mensaje=mensaje,
                        detalles_adicionales={
                            'tipo_registro': 'germinacion',
                            'registro_id': germinacion.id,
                            'fecha_creacion': germinacion.fecha_creacion.isoformat() if germinacion.fecha_creacion else None,
                            'fecha_revision_programada': germinacion.fecha_proxima_revision.isoformat(),
                            'dias_transcurridos': dias_transcurridos,
                            'estado_actual': germinacion.estado_germinacion,
                            'progreso_actual': germinacion.progreso_germinacion
                        }
                    )
                    
                    # Marcar como enviada
                    germinacion.alerta_revision_enviada = True
                    germinacion.save()
                    
                    logger.info(f"Alerta de revisión creada para germinación {germinacion.id}")
                
                alertas_creadas += 1
                
                self.stdout.write(
                    f'📧 {"[DRY-RUN] " if dry_run else ""}Alerta creada para germinación {germinacion.codigo} '
                    f'(Usuario: {usuario_destinatario.username})'
                )
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'❌ Error creando alerta para germinación {germinacion.id}: {e}'
                    )
                )
                logger.error(f"Error creando alerta para germinación {germinacion.id}: {e}")
        
        return alertas_creadas