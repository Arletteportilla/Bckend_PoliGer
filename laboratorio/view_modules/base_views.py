"""
Vistas base y mixins para el laboratorio
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class OptimizedPagination(PageNumberPagination):
    """Paginación optimizada"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class BaseServiceViewSet(viewsets.ModelViewSet):
    """
    ViewSet base que utiliza servicios de negocio
    """
    service_class = None
    pagination_class = OptimizedPagination
    permission_classes = [IsAuthenticated]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.service_class:
            self.service = self.service_class()
    
    def get_queryset(self):
        """Obtiene queryset usando el servicio"""
        if hasattr(self.service, 'get_all'):
            return self.service.get_all(user=self.request.user)
        return super().get_queryset()
    
    def list(self, request, *args, **kwargs):
        """Lista registros usando el servicio"""
        try:
            if hasattr(self.service, 'get_paginated'):
                page = int(request.GET.get('page', 1))
                page_size = int(request.GET.get('page_size', 20))
                
                # Extraer filtros de los parámetros de consulta
                filters = {}
                for key, value in request.GET.items():
                    if key not in ['page', 'page_size'] and value:
                        filters[key] = value
                
                result = self.service.get_paginated(
                    page=page,
                    page_size=page_size,
                    user=request.user,
                    **filters
                )
                
                return Response({
                    'count': result['total_count'],
                    'total_count': result['total_count'],
                    'total_pages': result['total_pages'],
                    'current_page': page,
                    'page_size': page_size,
                    'has_next': result['has_next'],
                    'has_previous': result['has_previous'],
                    'next': f"?page={page + 1}" if result['has_next'] else None,
                    'previous': f"?page={page - 1}" if result['has_previous'] else None,
                    'results': self.get_serializer(result['results'], many=True).data
                })
            else:
                # Fallback al comportamiento estándar
                return super().list(request, *args, **kwargs)
        
        except Exception as e:
            logger.error(f"Error en list: {e}")
            return Response(
                {'error': 'Error obteniendo datos'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def retrieve(self, request, *args, **kwargs):
        """Obtiene un registro específico usando el servicio"""
        try:
            obj_id = kwargs.get('pk')
            obj = self.service.get_by_id(obj_id, user=request.user)
            
            if not obj:
                return Response(
                    {'error': 'Registro no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            serializer = self.get_serializer(obj)
            return Response(serializer.data)
        
        except Exception as e:
            logger.error(f"Error en retrieve: {e}")
            return Response(
                {'error': 'Error obteniendo registro'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def create(self, request, *args, **kwargs):
        """Crea un registro usando el servicio"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            
            obj = self.service.create(serializer.validated_data, user=request.user)
            
            # Invalidar caches relacionados si el servicio lo soporta
            if hasattr(self.service, 'invalidate_related_caches'):
                self.service.invalidate_related_caches()
            
            response_serializer = self.get_serializer(obj)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error en create: {e}")
            return Response(
                {'error': 'Error creando registro'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Actualiza un registro usando el servicio"""
        try:
            obj_id = kwargs.get('pk')
            partial = kwargs.pop('partial', False)
            
            serializer = self.get_serializer(data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            
            obj = self.service.update(obj_id, serializer.validated_data, user=request.user)
            
            if not obj:
                return Response(
                    {'error': 'Registro no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Invalidar caches relacionados si el servicio lo soporta
            if hasattr(self.service, 'invalidate_related_caches'):
                self.service.invalidate_related_caches()
            
            response_serializer = self.get_serializer(obj)
            return Response(response_serializer.data)
        
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error en update: {e}")
            return Response(
                {'error': 'Error actualizando registro'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Elimina un registro usando el servicio"""
        try:
            obj_id = kwargs.get('pk')
            success = self.service.delete(obj_id, user=request.user)
            
            if not success:
                return Response(
                    {'error': 'Registro no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Invalidar caches relacionados si el servicio lo soporta
            if hasattr(self.service, 'invalidate_related_caches'):
                self.service.invalidate_related_caches()
            
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        except Exception as e:
            logger.error(f"Error en destroy: {e}")
            return Response(
                {'error': 'Error eliminando registro'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ErrorHandlerMixin:
    """
    Mixin para manejo consistente de errores
    """
    
    def handle_error(self, error, default_message="Error en la operación"):
        """Maneja errores de forma consistente"""
        if isinstance(error, ValidationError):
            if hasattr(error, 'message_dict'):
                return Response(error.message_dict, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)
        
        logger.error(f"{default_message}: {error}")
        return Response(
            {'error': default_message},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class CacheInvalidationMixin:
    """
    Mixin para invalidación de cache
    """
    
    def invalidate_caches(self, cache_keys):
        """Invalida múltiples caches"""
        from django.core.cache import cache
        
        for key in cache_keys:
            cache.delete(key)
            logger.info(f"Cache invalidado: {key}")


class SearchMixin:
    """
    Mixin para funcionalidad de búsqueda
    """
    
    def apply_search(self, queryset, search_term, search_fields):
        """Aplica búsqueda en múltiples campos"""
        if not search_term or not search_fields:
            return queryset
        
        from django.db.models import Q
        
        search_query = Q()
        for field in search_fields:
            search_query |= Q(**{f"{field}__icontains": search_term})
        
        return queryset.filter(search_query)