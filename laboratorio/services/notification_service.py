"""
Servicio de negocio para Notificaciones
"""
from typing import Dict, Any, List, Optional
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date, timedelta
import logging

from ..models import Notification, Germinacion, Polinizacion

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Servicio para manejar notificaciones del sistema
    """
    
    def crear_notificacion_germinacion(
        self, 
        usuario: User, 
        germinacion: Germinacion, 
        tipo: str = 'NUEVA_GERMINACION'
    ) -> Notification:
        """Crea una notificación para una germinación"""
        try:
            # Determinar título y mensaje según el tipo
            if tipo == 'NUEVA_GERMINACION':
                titulo = f"Nueva germinación creada: {germinacion.codigo or germinacion.nombre}"
                mensaje = f"Se ha creado una nueva germinación de {germinacion.genero} {germinacion.especie_variedad}"
                
                # Agregar información de predicción si existe
                if germinacion.prediccion_fecha_estimada:
                    dias_restantes = (germinacion.prediccion_fecha_estimada - date.today()).days
                    mensaje += f"\n\nFecha estimada de germinación: {germinacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')}"
                    mensaje += f"\nDías restantes: {dias_restantes}"
                    
            elif tipo == 'RECORDATORIO_REVISION':
                titulo = f"Recordatorio: Revisar germinación {germinacion.codigo or germinacion.nombre}"
                mensaje = f"Es momento de revisar la germinación de {germinacion.genero} {germinacion.especie_variedad}"
                
            elif tipo == 'ESTADO_ACTUALIZADO':
                titulo = f"Estado actualizado: {germinacion.codigo or germinacion.nombre}"
                mensaje = f"El estado de la germinación ha sido actualizado"
                
            else:
                titulo = f"Notificación: {germinacion.codigo or germinacion.nombre}"
                mensaje = f"Actualización sobre la germinación"
            
            # Crear detalles adicionales
            detalles = {
                'germinacion_id': germinacion.id,
                'codigo': germinacion.codigo,
                'genero': germinacion.genero,
                'especie': germinacion.especie_variedad,
                'fecha_siembra': str(germinacion.fecha_siembra) if germinacion.fecha_siembra else None,
                'prediccion_fecha_estimada': str(germinacion.prediccion_fecha_estimada) if germinacion.prediccion_fecha_estimada else None,
            }
            
            # Crear notificación
            notificacion = Notification.objects.create(
                usuario=usuario,
                germinacion=germinacion,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )
            
            logger.info(f"Notificación creada para germinación {germinacion.id}: {tipo}")
            return notificacion
            
        except Exception as e:
            logger.error(f"Error creando notificación de germinación: {e}")
            raise
    
    def crear_notificacion_polinizacion(
        self, 
        usuario: User, 
        polinizacion: Polinizacion, 
        tipo: str = 'NUEVA_POLINIZACION'
    ) -> Notification:
        """Crea una notificación para una polinización"""
        try:
            # Determinar título y mensaje según el tipo
            if tipo == 'NUEVA_POLINIZACION':
                titulo = f"Nueva polinización creada: {polinizacion.codigo}"
                mensaje = f"Se ha creado una nueva polinización tipo {polinizacion.tipo_polinizacion}"
                
                if polinizacion.madre_especie:
                    mensaje += f"\nMadre: {polinizacion.madre_genero} {polinizacion.madre_especie}"
                if polinizacion.padre_especie and polinizacion.tipo_polinizacion != 'SELF':
                    mensaje += f"\nPadre: {polinizacion.padre_genero} {polinizacion.padre_especie}"
                
                # Agregar información de predicción si existe
                if polinizacion.prediccion_fecha_estimada:
                    dias_restantes = (polinizacion.prediccion_fecha_estimada - date.today()).days
                    mensaje += f"\n\nFecha estimada de maduración: {polinizacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')}"
                    mensaje += f"\nDías restantes: {dias_restantes}"
                    
            elif tipo == 'ESTADO_POLINIZACION_ACTUALIZADO':
                titulo = f"Estado actualizado: {polinizacion.codigo}"
                mensaje = f"El estado de la polinización ha sido actualizado a: {polinizacion.estado}"
                
            else:
                titulo = f"Notificación: {polinizacion.codigo}"
                mensaje = f"Actualización sobre la polinización"
            
            # Crear detalles adicionales
            detalles = {
                'polinizacion_id': polinizacion.numero,
                'codigo': polinizacion.codigo,
                'tipo_polinizacion': polinizacion.tipo_polinizacion,
                'madre_especie': polinizacion.madre_especie,
                'padre_especie': polinizacion.padre_especie,
                'fecha_polinizacion': str(polinizacion.fechapol) if polinizacion.fechapol else None,
                'prediccion_fecha_estimada': str(polinizacion.prediccion_fecha_estimada) if polinizacion.prediccion_fecha_estimada else None,
                'estado': polinizacion.estado,
            }
            
            # Crear notificación
            notificacion = Notification.objects.create(
                usuario=usuario,
                polinizacion=polinizacion,
                tipo=tipo,
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )
            
            logger.info(f"Notificación creada para polinización {polinizacion.numero}: {tipo}")
            return notificacion
            
        except Exception as e:
            logger.error(f"Error creando notificación de polinización: {e}")
            raise
    
    def obtener_notificaciones_usuario(
        self, 
        usuario: User, 
        solo_no_leidas: bool = False,
        incluir_archivadas: bool = False
    ) -> List[Notification]:
        """Obtiene las notificaciones de un usuario"""
        queryset = Notification.objects.filter(usuario=usuario)
        
        if solo_no_leidas:
            queryset = queryset.filter(leida=False)
        
        if not incluir_archivadas:
            queryset = queryset.filter(archivada=False)
        
        return list(queryset.order_by('-fecha_creacion'))
    
    def obtener_alertas_pendientes(self, usuario: User) -> List[Dict[str, Any]]:
        """Obtiene alertas sobre germinaciones y polinizaciones próximas a vencer"""
        alertas = []
        hoy = date.today()
        
        # Alertas de germinaciones próximas a germinar
        germinaciones = Germinacion.objects.filter(
            creado_por=usuario,
            prediccion_fecha_estimada__isnull=False,
            archivo_origen=''  # Solo las creadas manualmente
        )
        
        for germ in germinaciones:
            if germ.prediccion_fecha_estimada:
                dias_restantes = (germ.prediccion_fecha_estimada - hoy).days
                
                # Alertas para germinaciones próximas (dentro de 7 días) o vencidas
                if dias_restantes <= 7:
                    tipo_alerta = 'vencida' if dias_restantes < 0 else 'proxima'
                    alertas.append({
                        'tipo': 'germinacion',
                        'id': germ.id,
                        'codigo': germ.codigo,
                        'nombre': germ.nombre,
                        'especie': f"{germ.genero} {germ.especie_variedad}",
                        'fecha_estimada': germ.prediccion_fecha_estimada,
                        'dias_restantes': dias_restantes,
                        'tipo_alerta': tipo_alerta,
                        'mensaje': f"Germinación {'vencida' if dias_restantes < 0 else 'próxima a germinar'}"
                    })
        
        # Alertas de polinizaciones próximas a madurar
        polinizaciones = Polinizacion.objects.filter(
            creado_por=usuario,
            prediccion_fecha_estimada__isnull=False,
            fechamad__isnull=True,  # Solo las que no han madurado
            archivo_origen=''  # Solo las creadas manualmente
        )
        
        for pol in polinizaciones:
            if pol.prediccion_fecha_estimada:
                dias_restantes = (pol.prediccion_fecha_estimada - hoy).days
                
                # Alertas para polinizaciones próximas (dentro de 7 días) o vencidas
                if dias_restantes <= 7:
                    tipo_alerta = 'vencida' if dias_restantes < 0 else 'proxima'
                    alertas.append({
                        'tipo': 'polinizacion',
                        'id': pol.numero,
                        'codigo': pol.codigo,
                        'especie': f"{pol.madre_genero} {pol.madre_especie}",
                        'tipo_polinizacion': pol.tipo_polinizacion,
                        'fecha_estimada': pol.prediccion_fecha_estimada,
                        'dias_restantes': dias_restantes,
                        'tipo_alerta': tipo_alerta,
                        'mensaje': f"Polinización {'vencida' if dias_restantes < 0 else 'próxima a madurar'}"
                    })
        
        # Ordenar por días restantes (las más urgentes primero)
        alertas.sort(key=lambda x: x['dias_restantes'])
        
        return alertas
    
    def marcar_como_leida(self, notificacion_id: int, usuario: User) -> bool:
        """Marca una notificación como leída"""
        try:
            notificacion = Notification.objects.get(id=notificacion_id, usuario=usuario)
            notificacion.marcar_como_leida()
            return True
        except Notification.DoesNotExist:
            logger.warning(f"Notificación {notificacion_id} no encontrada para usuario {usuario.username}")
            return False
    
    def marcar_todas_como_leidas(self, usuario: User) -> int:
        """Marca todas las notificaciones de un usuario como leídas"""
        count = Notification.objects.filter(
            usuario=usuario,
            leida=False
        ).update(
            leida=True,
            fecha_lectura=timezone.now()
        )
        return count
    
    def toggle_favorita(self, notificacion_id: int, usuario: User) -> bool:
        """Marca/desmarca una notificación como favorita"""
        try:
            notificacion = Notification.objects.get(id=notificacion_id, usuario=usuario)
            notificacion.toggle_favorita()
            return notificacion.favorita
        except Notification.DoesNotExist:
            logger.warning(f"Notificación {notificacion_id} no encontrada para usuario {usuario.username}")
            return False
    
    def archivar(self, notificacion_id: int, usuario: User) -> bool:
        """Archiva una notificación"""
        try:
            notificacion = Notification.objects.get(id=notificacion_id, usuario=usuario)
            notificacion.archivar()
            return True
        except Notification.DoesNotExist:
            logger.warning(f"Notificación {notificacion_id} no encontrada para usuario {usuario.username}")
            return False
    
    def obtener_estadisticas(self, usuario: User) -> Dict[str, int]:
        """Obtiene estadísticas de notificaciones del usuario"""
        total = Notification.objects.filter(usuario=usuario).count()
        no_leidas = Notification.objects.filter(usuario=usuario, leida=False).count()
        favoritas = Notification.objects.filter(usuario=usuario, favorita=True).count()
        archivadas = Notification.objects.filter(usuario=usuario, archivada=True).count()
        
        return {
            'total': total,
            'no_leidas': no_leidas,
            'favoritas': favoritas,
            'archivadas': archivadas
        }


# Instancia global del servicio
notification_service = NotificationService()
