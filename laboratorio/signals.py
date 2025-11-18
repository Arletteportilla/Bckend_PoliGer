"""
Signals para crear notificaciones automáticas
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Germinacion, Polinizacion
from .services.notification_service import notification_service
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Germinacion)
def crear_notificacion_germinacion(sender, instance, created, **kwargs):
    """
    Crea una notificación automática cuando se crea una nueva germinación
    """
    if created and instance.creado_por:
        try:
            notification_service.crear_notificacion_germinacion(
                usuario=instance.creado_por,
                germinacion=instance,
                tipo='NUEVA_GERMINACION'
            )
            logger.info(f"Notificacion creada para germinacion {instance.codigo}")
        except Exception as e:
            logger.error(f"Error al crear notificacion de germinacion: {e}")

@receiver(post_save, sender=Polinizacion)
def crear_notificacion_polinizacion(sender, instance, created, **kwargs):
    """
    Crea una notificación automática cuando se crea una nueva polinización
    """
    if created and instance.creado_por:
        try:
            notification_service.crear_notificacion_polinizacion(
                usuario=instance.creado_por,
                polinizacion=instance,
                tipo='NUEVA_POLINIZACION'
            )
            logger.info(f"Notificacion creada para polinizacion {instance.codigo}")
        except Exception as e:
            logger.error(f"Error al crear notificacion de polinizacion: {e}")
