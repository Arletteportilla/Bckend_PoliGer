"""
Servicios para el sistema de laboratorio
"""
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Notification, Germinacion, Polinizacion


class NotificationService:
    """Servicio para gestionar notificaciones"""
    
    @staticmethod
    def crear_notificacion_nueva_germinacion(germinacion):
        """Crea una notificación para nueva germinación"""
        try:
            if germinacion.creado_por:
                Notification.objects.create(
                    usuario=germinacion.creado_por,
                    germinacion=germinacion,
                    tipo='NUEVA_GERMINACION',
                    titulo='Nueva Germinación Creada',
                    mensaje=f'Se ha creado una nueva germinación: {germinacion.codigo or germinacion.nombre}'
                )
        except Exception:
            pass  # Silenciar errores de notificaciones
    
    @staticmethod
    def crear_notificacion_estado_actualizado(germinacion, estado_anterior):
        """Crea una notificación para cambio de estado"""
        try:
            if germinacion.creado_por:
                Notification.objects.create(
                    usuario=germinacion.creado_por,
                    germinacion=germinacion,
                    tipo='ESTADO_ACTUALIZADO',
                    titulo='Estado de Germinación Actualizado',
                    mensaje=f'La germinación {germinacion.codigo or germinacion.nombre} cambió de {estado_anterior} a {germinacion.etapa_actual}'
                )
        except Exception:
            pass  # Silenciar errores de notificaciones
    
    @staticmethod
    def crear_notificacion_polinizacion(usuario, polinizacion, tipo):
        """Crea una notificación para polinización"""
        try:
            titulos = {
                'NUEVA_POLINIZACION': 'Nueva Polinización Creada',
                'ESTADO_POLINIZACION_ACTUALIZADO': 'Estado de Polinización Actualizado'
            }
            
            mensajes = {
                'NUEVA_POLINIZACION': f'Se ha creado una nueva polinización: {polinizacion.codigo}',
                'ESTADO_POLINIZACION_ACTUALIZADO': f'La polinización {polinizacion.codigo} cambió de estado a {polinizacion.estado}'
            }
            
            Notification.objects.create(
                usuario=usuario,
                polinizacion=polinizacion,
                tipo=tipo,
                titulo=titulos.get(tipo, 'Notificación de Polinización'),
                mensaje=mensajes.get(tipo, f'Actualización en polinización {polinizacion.codigo}')
            )
        except Exception:
            pass  # Silenciar errores de notificaciones
    
    @staticmethod
    def crear_recordatorio_revision(germinacion):
        """Crea un recordatorio de revisión"""
        try:
            if germinacion.creado_por:
                Notification.objects.create(
                    usuario=germinacion.creado_por,
                    germinacion=germinacion,
                    tipo='RECORDATORIO_REVISION',
                    titulo='Recordatorio de Revisión',
                    mensaje=f'Es hora de revisar la germinación: {germinacion.codigo or germinacion.nombre}'
                )
        except Exception:
            pass  # Silenciar errores de notificaciones
    
    @staticmethod
    def limpiar_notificaciones_antiguas(dias=30):
        """Limpia notificaciones antiguas"""
        try:
            fecha_limite = timezone.now() - timezone.timedelta(days=dias)
            notificaciones_antiguas = Notification.objects.filter(
                fecha_creacion__lt=fecha_limite,
                leida=True
            )
            count = notificaciones_antiguas.count()
            notificaciones_antiguas.delete()
            return count
        except Exception:
            return 0