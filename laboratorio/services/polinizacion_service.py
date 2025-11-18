"""
Servicio de negocio para Polinizaciones
"""
from typing import Dict, Any, List, Optional
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import date, datetime
from django.core.exceptions import ValidationError
import logging

from ..models import Polinizacion
from .base_service import BaseService, PaginatedService, CacheableService
from ..utils.validation_utils import ValidationHelper, validate_codigo, validate_date_field, validate_positive_integer, validate_text_field

logger = logging.getLogger(__name__)


class PolinizacionService(PaginatedService, CacheableService):
    """
    Servicio de negocio para manejar operaciones de Polinización
    """
    
    def __init__(self):
        super().__init__(Polinizacion, cache_timeout=600)  # 10 minutos de cache
    
    def _validate_data(self, data: Dict[str, Any], is_create: bool = True, instance=None) -> Dict[str, Any]:
        """Valida y limpia los datos de polinización"""
        validated_data = data.copy()
        validator = ValidationHelper()
        
        # Validar fecha de polinización (obligatoria)
        if 'fechapol' in data and data['fechapol']:
            try:
                fechapol = validate_date_field(data['fechapol'], 'fecha de polinización', allow_future=True)
                # No permitir fechas muy futuras (más de 1 año)
                if fechapol > date.today().replace(year=date.today().year + 1):
                    validator.add_error('fechapol', 'La fecha de polinización no puede ser más de 1 año en el futuro')
                else:
                    validated_data['fechapol'] = fechapol
            except ValidationError as e:
                validator.add_error('fechapol', str(e))
        elif is_create:
            validator.add_error('fechapol', 'La fecha de polinización es obligatoria')
        
        # Validar fecha de maduración
        if 'fechamad' in data and data['fechamad']:
            try:
                validated_data['fechamad'] = validate_date_field(
                    data['fechamad'], 'fecha de maduración', allow_future=True
                )
            except ValidationError as e:
                validator.add_error('fechamad', str(e))
        
        # Validar coherencia de fechas
        if 'fechapol' in validated_data and 'fechamad' in validated_data:
            if validated_data['fechamad'] <= validated_data['fechapol']:
                validator.add_error('fechamad', 'La fecha de maduración debe ser posterior a la fecha de polinización')
        
        # Validar campos de texto
        text_fields = {
            'genero': (50, False),
            'especie': (100, False),
            'responsable': (100, False)
        }
        
        for field, (max_length, required) in text_fields.items():
            if field in data:
                try:
                    validated_data[field] = validate_text_field(
                        data[field], field.replace('_', ' '), max_length, required
                    )
                except ValidationError as e:
                    validator.add_error(field, str(e))
        
        # Validar cantidades
        if 'cantidad' in data:
            try:
                validated_data['cantidad'] = validate_positive_integer(
                    data['cantidad'], 'cantidad', max_value=1000000
                )
            except ValidationError as e:
                validator.add_error('cantidad', str(e))
        
        if 'cantidad_capsulas' in data:
            try:
                validated_data['cantidad_capsulas'] = validate_positive_integer(
                    data['cantidad_capsulas'], 'cantidad de cápsulas'
                )
            except ValidationError as e:
                validator.add_error('cantidad_capsulas', str(e))
        
        # Validar código único
        if 'codigo' in data:
            if data['codigo']:
                try:
                    validated_data['codigo'] = validate_codigo(data['codigo'])
                    # Validar unicidad del código
                    validator.validate_codigo_unique(validated_data['codigo'], Polinizacion, instance)
                except ValidationError as e:
                    validator.add_error('codigo', str(e))
            # El código no es obligatorio en polinizaciones (se genera automáticamente)
        
        # Lanzar errores si los hay
        validator.raise_if_errors()
        
        return validated_data
    
    def _apply_user_filter(self, queryset, user: User):
        """Aplica filtros basados en el rol del usuario"""
        # Los administradores ven todo
        if hasattr(user, 'profile') and user.profile.rol == 'TIPO_4':
            return queryset
        
        # Otros usuarios solo ven sus propias polinizaciones
        return queryset.filter(creado_por=user)
    
    def get_mis_polinizaciones(self, user: User, search: Optional[str] = None, dias_recientes: Optional[int] = None) -> List[Polinizacion]:
        """Obtiene las polinizaciones del usuario actual
        
        Args:
            user: Usuario actual
            search: Término de búsqueda opcional
            dias_recientes: Si se proporciona, filtra solo polinizaciones de los últimos N días
        """
        # SOLO filtrar por creado_por (no por responsable)
        # Excluir datos importados del CSV (archivo_origen no vacío)
        queryset = Polinizacion.objects.filter(
            creado_por=user,
            archivo_origen=''
        )
        
        # Filtrar por fecha si se especifica
        if dias_recientes:
            from datetime import timedelta
            from django.utils import timezone
            fecha_limite = timezone.now() - timedelta(days=dias_recientes)
            queryset = queryset.filter(fecha_creacion__gte=fecha_limite)
        
        # Aplicar búsqueda si se proporciona
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(genero__icontains=search) |
                Q(especie__icontains=search) |
                Q(madre_genero__icontains=search) |
                Q(madre_especie__icontains=search) |
                Q(padre_genero__icontains=search) |
                Q(padre_especie__icontains=search) |
                Q(nueva_genero__icontains=search) |
                Q(nueva_especie__icontains=search) |
                Q(ubicacion_nombre__icontains=search) |
                Q(observaciones__icontains=search)
            )
        
        return list(queryset.order_by('-fecha_creacion', '-fechapol'))
    
    def get_mis_polinizaciones_paginated(self, user: User, page: int = 1, page_size: int = 20, search: Optional[str] = None, dias_recientes: Optional[int] = None):
        """Obtiene las polinizaciones del usuario actual con paginación
        
        Args:
            user: Usuario actual
            page: Número de página
            page_size: Tamaño de página
            search: Término de búsqueda opcional
            dias_recientes: Si se proporciona, filtra solo polinizaciones de los últimos N días
        """
        from django.core.paginator import Paginator
        
        # SOLO filtrar por creado_por (no por responsable)
        # Excluir datos importados del CSV (archivo_origen no vacío)
        queryset = Polinizacion.objects.filter(
            creado_por=user,
            archivo_origen=''
        )
        
        # Filtrar por fecha si se especifica
        if dias_recientes:
            from datetime import timedelta
            from django.utils import timezone
            fecha_limite = timezone.now() - timedelta(days=dias_recientes)
            queryset = queryset.filter(fecha_creacion__gte=fecha_limite)
        
        # Aplicar búsqueda si se proporciona
        if search:
            queryset = queryset.filter(
                Q(codigo__icontains=search) |
                Q(genero__icontains=search) |
                Q(especie__icontains=search) |
                Q(madre_genero__icontains=search) |
                Q(madre_especie__icontains=search) |
                Q(padre_genero__icontains=search) |
                Q(padre_especie__icontains=search) |
                Q(nueva_genero__icontains=search) |
                Q(nueva_especie__icontains=search) |
                Q(ubicacion_nombre__icontains=search) |
                Q(observaciones__icontains=search)
            )
        
        # Ordenar por fecha de creación descendente
        queryset = queryset.order_by('-fecha_creacion', '-fechapol')
        
        # Paginar
        paginator = Paginator(queryset, page_size)
        page_obj = paginator.get_page(page)
        
        return {
            'results': list(page_obj),
            'count': paginator.count,
            'total_pages': paginator.num_pages,
            'current_page': page,
            'page_size': page_size,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
            'next': page if page_obj.has_next() else None,
            'previous': page - 1 if page_obj.has_previous() else None
        }
    
    def get_codigos_nuevas_plantas(self) -> List[str]:
        """Obtiene códigos de nuevas plantas para autocompletado"""
        cache_key = 'polinizacion_codigos_nuevas_plantas'
        
        def get_data():
            return list(
                Polinizacion.objects
                .exclude(nueva_codigo='')
                .exclude(nueva_codigo__isnull=True)
                .values_list('nueva_codigo', flat=True)
                .distinct()
                .order_by('nueva_codigo')
            )
        
        cached_data = self.get_cached_data(cache_key, get_data)
        return cached_data
    
    def get_codigos_con_especies(self) -> List[Dict[str, str]]:
        """Obtiene códigos con sus especies para autocompletado"""
        cache_key = 'polinizacion_codigos_con_especies'
        
        def get_data():
            return list(
                Polinizacion.objects
                .exclude(nueva_codigo='')
                .exclude(nueva_codigo__isnull=True)
                .values('nueva_codigo', 'nueva_especie', 'nueva_genero')
                .distinct()
                .order_by('nueva_codigo')
            )
        
        cached_data = self.get_cached_data(cache_key, get_data)
        return [
            {
                'codigo': item['nueva_codigo'],
                'especie': item['nueva_especie'] or '',
                'genero': item['nueva_genero'] or ''
            }
            for item in cached_data
        ]
    
    def get_polinizacion_by_codigo_nueva_planta(self, codigo: str) -> Optional[Dict[str, str]]:
        """Busca una polinización por código de nueva planta"""
        try:
            polinizacion = Polinizacion.objects.get(nueva_codigo=codigo)
            return {
                'codigo': polinizacion.nueva_codigo,
                'especie': polinizacion.nueva_especie or '',
                'genero': polinizacion.nueva_genero or ''
            }
        except Polinizacion.DoesNotExist:
            return None
    
    def get_cached_data(self, cache_key: str, data_func):
        """Obtiene datos con cache"""
        from django.core.cache import cache
        
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            return cached_data
        
        data = data_func()
        cache.set(cache_key, data, self.cache_timeout)
        return data
    
    def create(self, data: Dict[str, Any], user: Optional[User] = None) -> Polinizacion:
        """Crea una nueva polinización con lógica específica"""
        # Asegurar que el responsable esté asignado
        if not data.get('responsable') and user:
            full_name = f"{user.first_name} {user.last_name}".strip()
            data['responsable'] = full_name if full_name else user.username
        
        # Generar código automático si no se proporciona
        if not data.get('codigo'):
            data['codigo'] = self._generate_codigo()
        
        return super().create(data, user)
    
    def _generate_codigo(self) -> str:
        """Genera un código automático para la polinización"""
        from django.utils import timezone
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        return f"POL-{timestamp}"
    
    def invalidate_related_caches(self):
        """Invalida caches relacionados cuando se modifica una polinización"""
        cache_keys = [
            'polinizacion_codigos_nuevas_plantas',
            'polinizacion_codigos_con_especies'
        ]
        
        for key in cache_keys:
            self.invalidate_cache(key)


# Instancia global del servicio
polinizacion_service = PolinizacionService()