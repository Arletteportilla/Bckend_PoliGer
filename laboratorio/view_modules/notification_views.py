"""
Vistas para Notificaciones
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
import logging

from ..models import Notification
from ..serializers import NotificationSerializer
from ..services.notification_service import notification_service

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    ViewSet para Notificaciones
    """
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar notificaciones por usuario"""
        return Notification.objects.filter(
            usuario=self.request.user
        ).select_related(
            'usuario', 'germinacion', 'polinizacion'
        ).order_by('-fecha_creacion')
    
    def list(self, request, *args, **kwargs):
        """Lista las notificaciones del usuario con paginación"""
        try:
            solo_no_leidas = request.GET.get('solo_no_leidas', 'false').lower() == 'true'
            incluir_archivadas = request.GET.get('incluir_archivadas', 'false').lower() == 'true'

            # Usar queryset optimizado con select_related
            queryset = self.get_queryset()

            if solo_no_leidas:
                queryset = queryset.filter(leida=False)

            if not incluir_archivadas:
                queryset = queryset.filter(archivada=False)

            # Paginación: limitar a las más recientes
            page_size = min(int(request.GET.get('page_size', 50)), 100)
            page = max(int(request.GET.get('page', 1)), 1)
            offset = (page - 1) * page_size

            total = queryset.count()
            notificaciones = queryset[offset:offset + page_size]

            serializer = self.get_serializer(notificaciones, many=True)

            return Response({
                'count': total,
                'page': page,
                'page_size': page_size,
                'total_pages': (total + page_size - 1) // page_size if total > 0 else 1,
                'results': serializer.data
            })

        except Exception as e:
            logger.error(f"Error obteniendo notificaciones: {e}")
            return Response(
                {'error': 'Error obteniendo notificaciones'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='marcar-leida')
    def marcar_leida(self, request, pk=None):
        """Marca una notificación como leída"""
        try:
            success = notification_service.marcar_como_leida(
                notificacion_id=pk,
                usuario=request.user
            )
            
            if success:
                return Response({'message': 'Notificación marcada como leída'})
            else:
                return Response(
                    {'error': 'Notificación no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error marcando notificación como leída: {e}")
            return Response(
                {'error': 'Error marcando notificación como leída'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'], url_path='marcar-todas-leidas')
    def marcar_todas_leidas(self, request):
        """Marca todas las notificaciones como leídas"""
        try:
            count = notification_service.marcar_todas_como_leidas(usuario=request.user)
            
            return Response({
                'message': f'{count} notificaciones marcadas como leídas',
                'count': count
            })
            
        except Exception as e:
            logger.error(f"Error marcando todas las notificaciones como leídas: {e}")
            return Response(
                {'error': 'Error marcando notificaciones como leídas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='toggle-favorita')
    def toggle_favorita(self, request, pk=None):
        """Marca/desmarca una notificación como favorita"""
        try:
            es_favorita = notification_service.toggle_favorita(
                notificacion_id=pk,
                usuario=request.user
            )
            
            return Response({
                'message': 'Notificación actualizada',
                'favorita': es_favorita
            })
            
        except Exception as e:
            logger.error(f"Error cambiando estado de favorita: {e}")
            return Response(
                {'error': 'Error actualizando notificación'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='archivar')
    def archivar(self, request, pk=None):
        """Archiva una notificación"""
        try:
            success = notification_service.archivar(
                notificacion_id=pk,
                usuario=request.user
            )
            
            if success:
                return Response({'message': 'Notificación archivada'})
            else:
                return Response(
                    {'error': 'Notificación no encontrada'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            logger.error(f"Error archivando notificación: {e}")
            return Response(
                {'error': 'Error archivando notificación'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        """Obtiene estadísticas de notificaciones del usuario"""
        try:
            stats = notification_service.obtener_estadisticas(usuario=request.user)
            
            return Response(stats)
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return Response(
                {'error': 'Error obteniendo estadísticas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='alertas')
    def alertas(self, request):
        """Obtiene alertas pendientes del usuario"""
        try:
            alertas = notification_service.obtener_alertas_pendientes(usuario=request.user)
            
            return Response({
                'alertas': alertas,
                'total': len(alertas)
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo alertas: {e}")
            return Response(
                {'error': 'Error obteniendo alertas'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='registros-pendientes')
    def registros_pendientes(self, request):
        """Obtiene registros en estado INICIAL que requieren revisión"""
        try:
            dias_limite = int(request.GET.get('dias', 5))
            
            registros = notification_service.obtener_registros_pendientes_revision(
                usuario=request.user,
                dias_limite=dias_limite
            )
            
            return Response(registros)
            
        except Exception as e:
            logger.error(f"Error obteniendo registros pendientes: {e}")
            return Response(
                {'error': 'Error obteniendo registros pendientes'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
