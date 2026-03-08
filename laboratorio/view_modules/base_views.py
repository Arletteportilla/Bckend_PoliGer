"""
Vistas base y mixins para el laboratorio
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.exceptions import ValidationError as DRFValidationError
from django.core.exceptions import ValidationError
from django.db import IntegrityError
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
        """Lista registros usando paginación DRF nativa"""
        try:
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

        except DRFValidationError as e:
            return Response(
                {'error': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.warning(f"IntegrityError en create: {e}")
            return Response(
                {'error': 'Registro duplicado o restricción de integridad violada'},
                status=status.HTTP_409_CONFLICT
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

        except DRFValidationError as e:
            return Response(
                {'error': e.detail},
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except IntegrityError as e:
            logger.warning(f"IntegrityError en update: {e}")
            return Response(
                {'error': 'Registro duplicado o restricción de integridad violada'},
                status=status.HTTP_409_CONFLICT
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
        
        except IntegrityError as e:
            logger.warning(f"IntegrityError en destroy: {e}")
            return Response(
                {'error': 'No se puede eliminar el registro porque tiene datos asociados'},
                status=status.HTTP_409_CONFLICT
            )
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
        if isinstance(error, (ValidationError, DRFValidationError)):
            if hasattr(error, 'message_dict'):
                return Response(error.message_dict, status=status.HTTP_400_BAD_REQUEST)
            elif hasattr(error, 'detail'):
                return Response({'error': error.detail}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'error': str(error)}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(error, IntegrityError):
            logger.warning(f"{default_message} - IntegrityError: {error}")
            return Response(
                {'error': 'Registro duplicado o restricción de integridad violada'},
                status=status.HTTP_409_CONFLICT
            )

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