"""
Servicio base con funcionalidades comunes
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """
    Servicio base que proporciona funcionalidades comunes
    para todos los servicios de negocio
    """
    
    def __init__(self, model: Type[models.Model]):
        self.model = model
    
    def get_all(self, user: Optional[User] = None, **filters) -> List[models.Model]:
        """Obtiene todos los registros con filtros opcionales"""
        queryset = self.model.objects.all()
        
        if filters:
            queryset = queryset.filter(**filters)
        
        # Aplicar filtros de usuario si es necesario
        if user and hasattr(self.model, 'creado_por'):
            queryset = self._apply_user_filter(queryset, user)
        
        return list(queryset)
    
    def get_by_id(self, id: int, user: Optional[User] = None) -> Optional[models.Model]:
        """Obtiene un registro por ID"""
        try:
            obj = self.model.objects.get(pk=id)
            
            # Verificar permisos si es necesario
            if user and hasattr(obj, 'creado_por'):
                self._check_user_permission(obj, user)
            
            return obj
        except self.model.DoesNotExist:
            return None
    
    def create(self, data: Dict[str, Any], user: Optional[User] = None) -> models.Model:
        """Crea un nuevo registro"""
        # Validar datos
        validated_data = self._validate_data(data, is_create=True)
        
        # Asignar usuario si es necesario
        if user and hasattr(self.model, 'creado_por'):
            validated_data['creado_por'] = user
        
        # Crear objeto
        obj = self.model(**validated_data)
        obj.full_clean()  # Validación del modelo
        obj.save()
        
        logger.info(f"Creado {self.model.__name__} con ID {obj.pk}")
        return obj
    
    def update(self, id: int, data: Dict[str, Any], user: Optional[User] = None) -> Optional[models.Model]:
        """Actualiza un registro existente"""
        obj = self.get_by_id(id, user)
        if not obj:
            return None
        
        # Validar datos
        validated_data = self._validate_data(data, is_create=False, instance=obj)
        
        # Actualizar campos
        for field, value in validated_data.items():
            setattr(obj, field, value)
        
        obj.full_clean()  # Validación del modelo
        obj.save()
        
        logger.info(f"Actualizado {self.model.__name__} con ID {obj.pk}")
        return obj
    
    def delete(self, id: int, user: Optional[User] = None) -> bool:
        """Elimina un registro"""
        obj = self.get_by_id(id, user)
        if not obj:
            return False
        
        obj.delete()
        logger.info(f"Eliminado {self.model.__name__} con ID {id}")
        return True
    
    def _apply_user_filter(self, queryset, user: User):
        """Aplica filtros basados en el usuario"""
        # Por defecto, no aplicar filtros adicionales
        # Los servicios específicos pueden sobrescribir este método
        return queryset
    
    def _check_user_permission(self, obj, user: User):
        """Verifica permisos del usuario sobre el objeto"""
        # Por defecto, permitir acceso
        # Los servicios específicos pueden sobrescribir este método
        pass
    
    @abstractmethod
    def _validate_data(self, data: Dict[str, Any], is_create: bool = True, instance=None) -> Dict[str, Any]:
        """
        Valida y limpia los datos antes de crear/actualizar
        Debe ser implementado por cada servicio específico
        """
        pass


class CacheableService(BaseService):
    """
    Servicio base con capacidades de cache
    """
    
    def __init__(self, model: Type[models.Model], cache_timeout: int = 300):
        super().__init__(model)
        self.cache_timeout = cache_timeout
    
    def get_cached_all(self, cache_key: str, user: Optional[User] = None, **filters):
        """Obtiene todos los registros con cache"""
        from django.core.cache import cache
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        data = self.get_all(user=user, **filters)
        cache.set(cache_key, data, self.cache_timeout)
        return data
    
    def invalidate_cache(self, cache_key: str):
        """Invalida el cache"""
        from django.core.cache import cache
        cache.delete(cache_key)


class PaginatedService(BaseService):
    """
    Servicio base con capacidades de paginación
    """
    
    def get_paginated(self, page: int = 1, page_size: int = 20, user: Optional[User] = None, **filters):
        """Obtiene registros paginados"""
        from django.core.paginator import Paginator
        from django.db.models import Q
        
        queryset = self.model.objects.all()
        
        # Aplicar filtros específicos
        if filters:
            # Manejar búsqueda general
            search = filters.pop('search', None)
            if search:
                # Crear filtro de búsqueda dinámico basado en los campos del modelo
                search_fields = self._get_search_fields()
                if search_fields:
                    search_query = Q()
                    for field in search_fields:
                        search_query |= Q(**{f"{field}__icontains": search})
                    queryset = queryset.filter(search_query)
            
            # Aplicar otros filtros
            for key, value in filters.items():
                if value:
                    queryset = queryset.filter(**{key: value})
        
        if user and hasattr(self.model, 'creado_por'):
            queryset = self._apply_user_filter(queryset, user)
        
        # Ordenar por fecha de creación descendente por defecto
        if hasattr(self.model, 'fecha_creacion'):
            queryset = queryset.order_by('-fecha_creacion')
        elif hasattr(self.model, 'id'):
            queryset = queryset.order_by('-id')
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': list(page_obj),
            'total_count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    
    def _get_search_fields(self):
        """Obtiene los campos de búsqueda para el modelo"""
        # Campos comunes de búsqueda
        common_fields = ['codigo', 'especie', 'genero', 'responsable']
        
        # Verificar qué campos existen en el modelo
        model_fields = [field.name for field in self.model._meta.fields]
        search_fields = [field for field in common_fields if field in model_fields]
        
        # Agregar campos específicos según el modelo
        if self.model.__name__ == 'Polinizacion':
            specific_fields = [
                'planta_madre_codigo', 'planta_padre_codigo', 'nueva_planta_codigo',
                'planta_madre_especie', 'planta_padre_especie', 'nueva_planta_especie',
                'tipo_polinizacion', 'ubicacion'
            ]
            search_fields.extend([field for field in specific_fields if field in model_fields])
        
        return search_fields