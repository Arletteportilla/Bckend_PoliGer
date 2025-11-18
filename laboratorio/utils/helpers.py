"""
Utilidades para el sistema de laboratorio
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configurar logger
logger = logging.getLogger(__name__)

class AuditLogger:
    """Logger para auditoría de acciones del sistema"""
    
    @staticmethod
    def log_user_action(user, action: str, model: str, object_id: Optional[int] = None, details: Dict[str, Any] = None):
        """
        Registra acciones de usuario para auditoría
        
        Args:
            user: Usuario que realiza la acción
            action: Tipo de acción (CREATE, UPDATE, DELETE, VIEW)
            model: Modelo afectado (Germinacion, Polinizacion, etc.)
            object_id: ID del objeto afectado
            details: Detalles adicionales de la acción
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user.username if user else 'Anonymous',
            'user_id': user.id if user else None,
            'action': action,
            'model': model,
            'object_id': object_id,
            'details': details or {}
        }
        
        logger.info(f"AUDIT: {log_entry}")
        return log_entry
    
    @staticmethod
    def log_permission_denied(user, action: str, resource: str, reason: str = ""):
        """Registra intentos de acceso denegados"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'user': user.username if user else 'Anonymous',
            'action': 'PERMISSION_DENIED',
            'resource': resource,
            'attempted_action': action,
            'reason': reason
        }
        
        logger.warning(f"PERMISSION_DENIED: {log_entry}")
        return log_entry

class ValidationUtils:
    """Utilidades para validación de datos"""
    
    @staticmethod
    def validate_date_range(start_date, end_date):
        """Valida que el rango de fechas sea válido"""
        if start_date and end_date:
            if start_date > end_date:
                raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")
        return True
    
    @staticmethod
    def validate_positive_number(value, field_name: str):
        """Valida que un número sea positivo"""
        if value is not None and value < 0:
            raise ValueError(f"{field_name} debe ser un número positivo")
        return True
    
    @staticmethod
    def sanitize_string(value: str, max_length: int = 255) -> str:
        """Sanitiza y limita la longitud de strings"""
        if not value:
            return ""
        
        # Remover caracteres especiales peligrosos
        sanitized = value.strip()
        
        # Limitar longitud
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized

class PerformanceUtils:
    """Utilidades para optimización de performance"""
    
    @staticmethod
    def optimize_queryset(queryset, select_related=None, prefetch_related=None):
        """Optimiza querysets con select_related y prefetch_related"""
        if select_related:
            queryset = queryset.select_related(*select_related)
        
        if prefetch_related:
            queryset = queryset.prefetch_related(*prefetch_related)
        
        return queryset
    
    @staticmethod
    def paginate_results(queryset, page_size: int = 20, page: int = 1):
        """Pagina resultados para mejorar performance"""
        from django.core.paginator import Paginator
        
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': list(page_obj),
            'count': paginator.count,
            'num_pages': paginator.num_pages,
            'current_page': page,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        }