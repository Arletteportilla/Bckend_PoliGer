from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Polinizacion, Germinacion
from .serializers import PolinizacionSerializer, GerminacionSerializer
import logging

logger = logging.getLogger(__name__)

class CalendarViewSet(viewsets.ViewSet):
    """
    ViewSet para manejar eventos del calendario de procesos
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def events(self, request):
        """
        Obtener eventos del calendario con filtros opcionales
        """
        try:
            # Parámetros de filtrado
            start_date = request.query_params.get('start_date')
            end_date = request.query_params.get('end_date')
            date = request.query_params.get('date')
            status_filter = request.query_params.get('status')
            predicted_only = request.query_params.get('predicted_only', 'false').lower() == 'true'
            
            logger.info(f"📅 CalendarViewSet.events - Parámetros: start_date={start_date}, end_date={end_date}, date={date}, status={status_filter}, predicted_only={predicted_only}")
            
            events = []
            
            # Obtener polinizaciones
            polinizaciones = self._get_polinizaciones(
                start_date, end_date, date, status_filter, predicted_only
            )
            events.extend(polinizaciones)
            
            # Obtener germinaciones
            germinaciones = self._get_germinaciones(
                start_date, end_date, date, status_filter, predicted_only
            )
            events.extend(germinaciones)
            
            # Ordenar por fecha
            events.sort(key=lambda x: x['date'])
            
            logger.info(f"📅 CalendarViewSet.events - Total eventos encontrados: {len(events)}")
            
            return Response(events)
            
        except Exception as e:
            logger.error(f"❌ CalendarViewSet.events - Error: {str(e)}")
            return Response(
                {'error': 'Error al obtener eventos del calendario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _get_polinizaciones(self, start_date, end_date, date, status_filter, predicted_only):
        """
        Obtener polinizaciones como eventos del calendario
        """
        try:
            queryset = Polinizacion.objects.all()
            
            # Aplicar filtros de fecha
            if date:
                # Eventos para una fecha específica
                queryset = queryset.filter(fechapol=date)
            elif start_date and end_date:
                # Eventos en un rango de fechas
                queryset = queryset.filter(
                    fechapol__gte=start_date,
                    fechapol__lte=end_date
                )
            
            # Filtro de estado
            if status_filter:
                queryset = queryset.filter(estado=status_filter)
            
            # Filtro de predicciones
            if predicted_only:
                queryset = queryset.filter(
                    Q(prediccion_fecha_estimada__isnull=False) |
                    Q(prediccion_tipo__isnull=False)
                )
            
            logger.info(f"📅 CalendarViewSet._get_polinizaciones - Polinizaciones encontradas: {queryset.count()}")
            
            events = []
            for polinizacion in queryset:
                event = {
                    'id': f"pol_{polinizacion.numero}",
                    'type': 'pollination',
                    'date': polinizacion.fechapol.isoformat(),
                    'subtype': polinizacion.tipo_polinizacion,
                    'title': f"Polinización {polinizacion.tipo_polinizacion} - {polinizacion.nueva_especie or polinizacion.especie}",
                    'description': f"Polinización {polinizacion.tipo_polinizacion} programada",
                    'species': polinizacion.nueva_especie or polinizacion.especie or 'No especificada',
                    'technician': polinizacion.responsable or 'No asignado',
                    'status': polinizacion.estado,
                    'estimated_days': polinizacion.prediccion_dias_estimados or 180,  # Valor por defecto
                    'priority': self._determine_priority(polinizacion),
                    'is_predicted': bool(polinizacion.prediccion_fecha_estimada or polinizacion.prediccion_tipo),
                    # Campos específicos del backend
                    'codigo': polinizacion.codigo,
                    'responsable': polinizacion.responsable,
                    'ubicacion': polinizacion.ubicacion_nombre or polinizacion.ubicacion,
                    'cantidad': polinizacion.cantidad_capsulas,
                    'observaciones': polinizacion.observaciones,
                    # Campos de predicción
                    'prediccion_dias_estimados': polinizacion.prediccion_dias_estimados,
                    'prediccion_confianza': float(polinizacion.prediccion_confianza) if polinizacion.prediccion_confianza else None,
                    'prediccion_fecha_estimada': polinizacion.prediccion_fecha_estimada.isoformat() if polinizacion.prediccion_fecha_estimada else None,
                    'prediccion_tipo': polinizacion.prediccion_tipo,
                }
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ CalendarViewSet._get_polinizaciones - Error: {str(e)}")
            return []

    def _get_germinaciones(self, start_date, end_date, date, status_filter, predicted_only):
        """
        Obtener germinaciones como eventos del calendario
        """
        try:
            queryset = Germinacion.objects.all()
            
            # Aplicar filtros de fecha
            if date:
                # Eventos para una fecha específica
                queryset = queryset.filter(
                    Q(fecha_siembra=date) |
                    Q(fecha_polinizacion=date) |
                    Q(fecha_ingreso=date)
                )
            elif start_date and end_date:
                # Eventos en un rango de fechas
                queryset = queryset.filter(
                    Q(fecha_siembra__gte=start_date, fecha_siembra__lte=end_date) |
                    Q(fecha_polinizacion__gte=start_date, fecha_polinizacion__lte=end_date) |
                    Q(fecha_ingreso__gte=start_date, fecha_ingreso__lte=end_date)
                )
            
            # Filtro de estado
            if status_filter:
                queryset = queryset.filter(etapa_actual=status_filter)
            
            # Filtro de predicciones (las germinaciones no tienen predicciones directas, pero pueden estar relacionadas con polinizaciones predichas)
            if predicted_only:
                queryset = queryset.filter(
                    Q(polinizacion__prediccion_fecha_estimada__isnull=False) |
                    Q(polinizacion__prediccion_tipo__isnull=False)
                )
            
            logger.info(f"📅 CalendarViewSet._get_germinaciones - Germinaciones encontradas: {queryset.count()}")
            
            events = []
            for germinacion in queryset:
                # Determinar la fecha principal del evento
                event_date = germinacion.fecha_siembra or germinacion.fecha_polinizacion or germinacion.fecha_ingreso
                if not event_date:
                    continue
                
                # Determinar el tipo de evento basado en la etapa
                event_type = self._get_germinacion_event_type(germinacion)
                
                event = {
                    'id': f"germ_{germinacion.id}",
                    'type': 'germination',
                    'date': event_date.isoformat(),
                    'subtype': event_type,
                    'title': f"Germinación {event_type} - {germinacion.especie_variedad or germinacion.nombre}",
                    'description': f"Proceso de germinación en etapa {event_type}",
                    'species': germinacion.especie_variedad or germinacion.nombre or 'No especificada',
                    'technician': germinacion.responsable or 'No asignado',
                    'status': germinacion.etapa_actual or 'INGRESADO',
                    'estimated_days': self._get_germinacion_estimated_days(germinacion),
                    'priority': self._determine_priority(germinacion),
                    'is_predicted': bool(germinacion.polinizacion and (
                        germinacion.polinizacion.prediccion_fecha_estimada or 
                        germinacion.polinizacion.prediccion_tipo
                    )),
                    # Campos específicos del backend
                    'codigo': germinacion.codigo,
                    'responsable': germinacion.responsable,
                    'ubicacion': germinacion.percha or germinacion.finca,
                    'cantidad': germinacion.cantidad_solicitada or germinacion.no_capsulas,
                    'observaciones': germinacion.observaciones,
                    # Campos de predicción (heredados de la polinización relacionada)
                    'prediccion_dias_estimados': germinacion.polinizacion.prediccion_dias_estimados if germinacion.polinizacion else None,
                    'prediccion_confianza': float(germinacion.polinizacion.prediccion_confianza) if germinacion.polinizacion and germinacion.polinizacion.prediccion_confianza else None,
                    'prediccion_fecha_estimada': germinacion.polinizacion.prediccion_fecha_estimada.isoformat() if germinacion.polinizacion and germinacion.polinizacion.prediccion_fecha_estimada else None,
                    'prediccion_tipo': germinacion.polinizacion.prediccion_tipo if germinacion.polinizacion else None,
                }
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"❌ CalendarViewSet._get_germinaciones - Error: {str(e)}")
            return []

    def _get_germinacion_event_type(self, germinacion):
        """
        Determinar el tipo de evento de germinación basado en la etapa
        """
        etapa = germinacion.etapa_actual or 'INGRESADO'
        
        if etapa == 'INGRESADO':
            return 'sowing'
        elif etapa == 'EN_PROCESO':
            return 'transfer'
        elif etapa == 'LISTA':
            return 'adaptation'
        else:
            return 'sowing'

    def _get_germinacion_estimated_days(self, germinacion):
        """
        Obtener días estimados para germinación
        """
        if germinacion.dias_polinizacion:
            return germinacion.dias_polinizacion
        
        # Si tiene polinización relacionada con predicción
        if germinacion.polinizacion and germinacion.polinizacion.prediccion_dias_estimados:
            return germinacion.polinizacion.prediccion_dias_estimados
        
        # Valor por defecto basado en el tipo
        return 90

    def _determine_priority(self, obj):
        """
        Determinar prioridad basada en diferentes factores
        """
        today = timezone.now().date()
        
        # Obtener fecha del evento
        if hasattr(obj, 'fechapol'):
            event_date = obj.fechapol
        elif hasattr(obj, 'fecha_siembra'):
            event_date = obj.fecha_siembra
        elif hasattr(obj, 'fecha_polinizacion'):
            event_date = obj.fecha_polinizacion
        else:
            event_date = today
        
        if not event_date:
            return 'low'
        
        days_until_event = (event_date - today).days
        
        # Si está retrasado
        if days_until_event < 0:
            return 'high'
        
        # Si es una predicción con alta confianza
        if hasattr(obj, 'prediccion_confianza') and obj.prediccion_confianza and obj.prediccion_confianza > 80:
            return 'high'
        
        # Si está próximo (menos de 7 días)
        if days_until_event <= 7:
            return 'high'
        
        # Si está próximo (menos de 30 días)
        if days_until_event <= 30:
            return 'medium'
        
        return 'low'

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """
        Obtener estadísticas del calendario
        """
        try:
            today = timezone.now().date()
            
            # Estadísticas de polinizaciones
            polinizaciones_pendientes = Polinizacion.objects.filter(estado='INGRESADO').count()
            polinizaciones_proceso = Polinizacion.objects.filter(estado='EN_PROCESO').count()
            polinizaciones_completadas = Polinizacion.objects.filter(estado__in=['LISTA', 'LISTO']).count()
            polinizaciones_retrasadas = Polinizacion.objects.filter(
                fechapol__lt=today,
                estado__in=['INGRESADO', 'EN_PROCESO']
            ).count()
            polinizaciones_predichas = Polinizacion.objects.filter(
                Q(prediccion_fecha_estimada__isnull=False) |
                Q(prediccion_tipo__isnull=False)
            ).count()
            
            # Estadísticas de germinaciones
            germinaciones_pendientes = Germinacion.objects.filter(etapa_actual='INGRESADO').count()
            germinaciones_proceso = Germinacion.objects.filter(etapa_actual='EN_PROCESO').count()
            germinaciones_completadas = Germinacion.objects.filter(etapa_actual='LISTA').count()
            germinaciones_retrasadas = Germinacion.objects.filter(
                Q(fecha_siembra__lt=today) | Q(fecha_polinizacion__lt=today),
                etapa_actual__in=['INGRESADO', 'EN_PROCESO']
            ).count()
            germinaciones_predichas = Germinacion.objects.filter(
                polinizacion__prediccion_fecha_estimada__isnull=False
            ).count()
            
            # Totales
            stats = {
                'pending': polinizaciones_pendientes + germinaciones_pendientes,
                'in_progress': polinizaciones_proceso + germinaciones_proceso,
                'completed': polinizaciones_completadas + germinaciones_completadas,
                'delayed': polinizaciones_retrasadas + germinaciones_retrasadas,
                'overdue': polinizaciones_retrasadas + germinaciones_retrasadas,  # Mismo que delayed por ahora
                'predicted': polinizaciones_predichas + germinaciones_predichas,
            }
            
            logger.info(f"📅 CalendarViewSet.stats - Estadísticas: {stats}")
            
            return Response(stats)
            
        except Exception as e:
            logger.error(f"❌ CalendarViewSet.stats - Error: {str(e)}")
            return Response(
                {'error': 'Error al obtener estadísticas del calendario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
