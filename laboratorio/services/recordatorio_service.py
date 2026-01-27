"""
Servicio para manejo de recordatorios automáticos.

Este servicio maneja la lógica de:
1. Verificar si un registro recién creado ya necesita notificación
2. Enviar notificación inmediata si la fecha base ya pasó más de X días
3. Evitar duplicados

ESCENARIO CRÍTICO:
- Usuario crea registro HOY con fecha_base = hace 10 días
- La notificación debe enviarse INMEDIATAMENTE, no esperar al scheduler
"""
from django.utils import timezone
from django.conf import settings
from datetime import date, timedelta
import logging

from ..core.models import Notification, Germinacion, Polinizacion

logger = logging.getLogger(__name__)

# Días por defecto para recordatorio (puede configurarse en settings)
DIAS_RECORDATORIO = getattr(settings, 'NOTIFICATION_REMINDER_DAYS', 5)


class RecordatorioService:
    """Servicio para manejo de recordatorios automáticos"""

    def __init__(self, dias_recordatorio=None):
        self.dias_recordatorio = dias_recordatorio or DIAS_RECORDATORIO

    def verificar_y_notificar_germinacion(self, germinacion: Germinacion) -> bool:
        """
        Verifica si una germinación recién creada ya requiere notificación.

        Args:
            germinacion: Instancia de Germinacion recién creada

        Returns:
            True si se envió notificación, False si no era necesario
        """
        if not germinacion.fecha_siembra or not germinacion.creado_por:
            logger.debug(f"Germinación {germinacion.id}: sin fecha_siembra o creado_por")
            return False

        hoy = timezone.now().date()
        dias_transcurridos = (hoy - germinacion.fecha_siembra).days

        logger.info(
            f"Verificando germinación {germinacion.codigo}: "
            f"fecha_siembra={germinacion.fecha_siembra}, "
            f"días_transcurridos={dias_transcurridos}, "
            f"umbral={self.dias_recordatorio}"
        )

        # Si ya pasaron más de X días desde la fecha de siembra
        if dias_transcurridos >= self.dias_recordatorio:
            # Verificar que no se haya enviado ya
            if germinacion.recordatorio_5_dias_enviado:
                logger.debug(f"Germinación {germinacion.id}: recordatorio ya enviado")
                return False

            # Verificar duplicado en notificaciones
            if self._existe_notificacion(germinacion=germinacion):
                logger.debug(f"Germinación {germinacion.id}: ya existe notificación")
                return False

            # Crear notificación inmediata
            logger.info(
                f"⚡ Germinación {germinacion.codigo}: creando notificación inmediata "
                f"({dias_transcurridos} días desde siembra)"
            )

            self._crear_notificacion_germinacion(germinacion, dias_transcurridos)

            # Marcar como enviado
            germinacion.recordatorio_5_dias_enviado = True
            germinacion.save(update_fields=['recordatorio_5_dias_enviado'])

            return True

        logger.debug(
            f"Germinación {germinacion.id}: aún no requiere notificación "
            f"({dias_transcurridos} < {self.dias_recordatorio} días)"
        )
        return False

    def verificar_y_notificar_polinizacion(self, polinizacion: Polinizacion) -> bool:
        """
        Verifica si una polinización recién creada ya requiere notificación.

        Args:
            polinizacion: Instancia de Polinizacion recién creada

        Returns:
            True si se envió notificación, False si no era necesario
        """
        if not polinizacion.fechapol or not polinizacion.creado_por:
            logger.debug(f"Polinización {polinizacion.numero}: sin fechapol o creado_por")
            return False

        hoy = timezone.now().date()
        dias_transcurridos = (hoy - polinizacion.fechapol).days

        logger.info(
            f"Verificando polinización {polinizacion.codigo}: "
            f"fechapol={polinizacion.fechapol}, "
            f"días_transcurridos={dias_transcurridos}, "
            f"umbral={self.dias_recordatorio}"
        )

        # Si ya pasaron más de X días desde la fecha de polinización
        if dias_transcurridos >= self.dias_recordatorio:
            # Verificar que no se haya enviado ya
            if polinizacion.recordatorio_5_dias_enviado:
                logger.debug(f"Polinización {polinizacion.numero}: recordatorio ya enviado")
                return False

            # Verificar duplicado en notificaciones
            if self._existe_notificacion(polinizacion=polinizacion):
                logger.debug(f"Polinización {polinizacion.numero}: ya existe notificación")
                return False

            # Crear notificación inmediata
            logger.info(
                f"⚡ Polinización {polinizacion.codigo}: creando notificación inmediata "
                f"({dias_transcurridos} días desde polinización)"
            )

            self._crear_notificacion_polinizacion(polinizacion, dias_transcurridos)

            # Marcar como enviado
            polinizacion.recordatorio_5_dias_enviado = True
            polinizacion.save(update_fields=['recordatorio_5_dias_enviado'])

            return True

        logger.debug(
            f"Polinización {polinizacion.numero}: aún no requiere notificación "
            f"({dias_transcurridos} < {self.dias_recordatorio} días)"
        )
        return False

    def _existe_notificacion(self, germinacion=None, polinizacion=None) -> bool:
        """Verifica si ya existe una notificación de recordatorio de 5 días"""
        filtros = {'tipo': 'RECORDATORIO_5_DIAS'}

        if germinacion:
            filtros['germinacion'] = germinacion
        elif polinizacion:
            filtros['polinizacion'] = polinizacion
        else:
            return False

        return Notification.objects.filter(**filtros).exists()

    def _crear_notificacion_germinacion(self, germinacion, dias_transcurridos):
        """Crea notificación de recordatorio para germinación"""
        titulo = f"📋 Revisa la germinación {germinacion.codigo}"

        mensaje = (
            f"Han pasado {dias_transcurridos} días desde la siembra.\n\n"
            f"🌱 Especie: {germinacion.genero} {germinacion.especie_variedad}\n"
            f"📅 Fecha de siembra: {germinacion.fecha_siembra.strftime('%d/%m/%Y') if germinacion.fecha_siembra else 'N/A'}\n"
            f"📊 Estado actual: {germinacion.estado_germinacion}\n\n"
            f"💡 Revisa la germinación y actualiza el estado del registro."
        )

        detalles = {
            'germinacion_id': germinacion.id,
            'codigo': germinacion.codigo,
            'dias_transcurridos': dias_transcurridos,
            'tipo_recordatorio': 'recordatorio_5_dias',
            'enviado_al_crear': True,
            'fecha_envio': str(timezone.now().date())
        }

        Notification.objects.create(
            usuario=germinacion.creado_por,
            germinacion=germinacion,
            tipo='RECORDATORIO_5_DIAS',
            titulo=titulo,
            mensaje=mensaje,
            detalles_adicionales=detalles
        )

    def _crear_notificacion_polinizacion(self, polinizacion, dias_transcurridos):
        """Crea notificación de recordatorio para polinización"""
        titulo = f"📋 Revisa la polinización {polinizacion.codigo}"

        mensaje = (
            f"Han pasado {dias_transcurridos} días desde la polinización.\n\n"
            f"🌸 Tipo: {polinizacion.tipo_polinizacion}\n"
            f"📅 Fecha de polinización: {polinizacion.fechapol.strftime('%d/%m/%Y') if polinizacion.fechapol else 'N/A'}\n"
            f"📊 Estado actual: {polinizacion.estado_polinizacion}\n"
        )

        if polinizacion.madre_especie:
            mensaje += f"🌱 Madre: {polinizacion.madre_genero} {polinizacion.madre_especie}\n"

        mensaje += "\n💡 Revisa la polinización y actualiza el estado del registro."

        detalles = {
            'polinizacion_id': polinizacion.numero,
            'codigo': polinizacion.codigo,
            'dias_transcurridos': dias_transcurridos,
            'tipo_recordatorio': 'recordatorio_5_dias',
            'enviado_al_crear': True,
            'fecha_envio': str(timezone.now().date())
        }

        Notification.objects.create(
            usuario=polinizacion.creado_por,
            polinizacion=polinizacion,
            tipo='RECORDATORIO_5_DIAS',
            titulo=titulo,
            mensaje=mensaje,
            detalles_adicionales=detalles
        )


# Instancia global del servicio
recordatorio_service = RecordatorioService()
