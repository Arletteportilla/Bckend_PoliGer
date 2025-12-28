"""
Servicio de negocio para Germinaciones
"""
from typing import Dict, Any, List, Optional
from django.contrib.auth.models import User
from django.db.models import Q
from datetime import date, datetime
from django.core.exceptions import ValidationError
import logging

from ..models import Germinacion
from .base_service import BaseService, PaginatedService, CacheableService
from ..utils.validation_utils import ValidationHelper, validate_codigo, validate_date_field, validate_positive_integer, validate_text_field

logger = logging.getLogger(__name__)


class GerminacionService(PaginatedService, CacheableService):
    """
    Servicio de negocio para manejar operaciones de Germinación
    """
    
    def __init__(self):
        super().__init__(Germinacion, cache_timeout=600)  # 10 minutos de cache
    
    def _validate_data(self, data: Dict[str, Any], is_create: bool = True, instance=None) -> Dict[str, Any]:
        """Valida y limpia los datos de germinación"""
        validated_data = data.copy()
        validator = ValidationHelper()
        
        # Campos obligatorios
        if is_create:
            required_fields = {
                'codigo': 'El código es obligatorio',
                'especie_variedad': 'La especie/variedad es obligatoria',
                'fecha_siembra': 'La fecha de siembra es obligatoria',
                'cantidad_solicitada': 'La cantidad solicitada es obligatoria',
                'responsable': 'El responsable es obligatorio'
            }
            validator.validate_required_fields(data, required_fields)
        
        # Validar fechas
        if 'fecha_siembra' in data and data['fecha_siembra']:
            try:
                validated_data['fecha_siembra'] = validate_date_field(
                    data['fecha_siembra'], 'fecha de siembra', allow_future=True
                )
            except ValidationError as e:
                validator.add_error('fecha_siembra', str(e))
        
        if 'fecha_polinizacion' in data and data['fecha_polinizacion']:
            try:
                validated_data['fecha_polinizacion'] = validate_date_field(
                    data['fecha_polinizacion'], 'fecha de polinización', allow_future=False
                )
            except ValidationError as e:
                validator.add_error('fecha_polinizacion', str(e))
        
        # Validar coherencia de fechas
        if 'fecha_siembra' in validated_data and 'fecha_polinizacion' in validated_data:
            validator.validate_date_coherence(
                validated_data,
                [('fecha_polinizacion', 'fecha_siembra', 'La fecha de polinización no puede ser posterior a la fecha de siembra')]
            )
        
        # Validar números positivos
        if 'no_capsulas' in data:
            try:
                validated_data['no_capsulas'] = validate_positive_integer(
                    data['no_capsulas'], 'número de cápsulas', max_value=10000
                )
            except ValidationError as e:
                validator.add_error('no_capsulas', str(e))
        
        if 'cantidad_solicitada' in data:
            try:
                validated_data['cantidad_solicitada'] = validate_positive_integer(
                    data['cantidad_solicitada'], 'cantidad solicitada', max_value=1000000
                )
            except ValidationError as e:
                validator.add_error('cantidad_solicitada', str(e))
        
        # Validar código (sin validar unicidad - se permiten códigos duplicados)
        if 'codigo' in data:
            if data['codigo']:
                try:
                    validated_data['codigo'] = validate_codigo(data['codigo'])
                    # NO validar unicidad - se permiten códigos duplicados en germinaciones
                except ValidationError as e:
                    validator.add_error('codigo', str(e))
            elif is_create:
                # En creación, el código es obligatorio
                validator.add_error('codigo', 'El código es obligatorio')
        
        # Validar campos de texto
        text_fields = {
            'especie_variedad': (100, is_create),
            'responsable': (100, is_create),
            'percha': (50, False),
            'genero': (50, False)
        }
        
        for field, (max_length, required) in text_fields.items():
            if field in data:
                try:
                    validated_data[field] = validate_text_field(
                        data[field], field.replace('_', ' '), max_length, required
                    )
                except ValidationError as e:
                    validator.add_error(field, str(e))
        
        # Lanzar errores si los hay
        validator.raise_if_errors()
        
        return validated_data
    
    def _apply_user_filter(self, queryset, user: User):
        """Aplica filtros basados en el rol del usuario"""
        # Los administradores ven todo
        if hasattr(user, 'profile') and user.profile.rol == 'TIPO_4':
            return queryset
        
        # Otros usuarios solo ven sus propias germinaciones
        return queryset.filter(creado_por=user)
    
    def get_mis_germinaciones(self, user: User, search: Optional[str] = None, dias_recientes: Optional[int] = None, excluir_importadas: bool = False) -> List[Germinacion]:
        """Obtiene las germinaciones del usuario actual

        Args:
            user: Usuario actual
            search: Término de búsqueda opcional
            dias_recientes: Si se proporciona, filtra solo germinaciones de los últimos N días
            excluir_importadas: Si es True, excluye las germinaciones importadas desde archivos CSV/Excel
        """
        # SOLO filtrar por creado_por (no por responsable)
        # Esto evita mostrar datos importados masivamente
        queryset = Germinacion.objects.filter(creado_por=user)

        # Excluir germinaciones importadas desde CSV/Excel si se especifica
        if excluir_importadas:
            queryset = queryset.filter(Q(archivo_origen__isnull=True) | Q(archivo_origen=''))

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
                Q(especie_variedad__icontains=search) |
                Q(observaciones__icontains=search)
            )

        return list(queryset.order_by('-fecha_creacion'))
    
    def get_mis_germinaciones_paginated(self, user: User, page: int = 1, page_size: int = 20, search: Optional[str] = None, dias_recientes: Optional[int] = None, excluir_importadas: bool = False):
        """Obtiene las germinaciones del usuario actual con paginación

        Args:
            user: Usuario actual
            page: Número de página
            page_size: Tamaño de página
            search: Término de búsqueda opcional
            dias_recientes: Si se proporciona, filtra solo germinaciones de los últimos N días
            excluir_importadas: Si es True, excluye las germinaciones importadas desde archivos CSV/Excel
        """
        from django.core.paginator import Paginator

        # SOLO filtrar por creado_por (no por responsable)
        # Esto evita mostrar datos importados masivamente
        queryset = Germinacion.objects.filter(creado_por=user)

        # Excluir germinaciones importadas desde CSV/Excel si se especifica
        if excluir_importadas:
            queryset = queryset.filter(Q(archivo_origen__isnull=True) | Q(archivo_origen=''))

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
                Q(especie_variedad__icontains=search) |
                Q(observaciones__icontains=search)
            )

        # Ordenar por fecha de creación descendente
        queryset = queryset.order_by('-fecha_creacion')
        
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
    
    def get_codigos_unicos(self) -> List[str]:
        """Obtiene códigos únicos para autocompletado"""
        cache_key = 'germinacion_codigos_unicos'
        
        def get_data():
            return list(
                Germinacion.objects
                .exclude(codigo='')
                .exclude(codigo__isnull=True)
                .values_list('codigo', flat=True)
                .distinct()
                .order_by('codigo')
            )
        
        return self.get_cached_data(cache_key, get_data)
    
    def get_codigos_con_especies(self) -> List[Dict[str, str]]:
        """Obtiene códigos con sus especies para autocompletado"""
        cache_key = 'germinacion_codigos_con_especies'
        
        def get_data():
            return list(
                Germinacion.objects
                .exclude(codigo='')
                .exclude(codigo__isnull=True)
                .values('codigo', 'especie_variedad', 'genero')
                .distinct()
                .order_by('codigo')
            )
        
        cached_data = self.get_cached_data(cache_key, get_data)
        return [
            {
                'codigo': item['codigo'],
                'especie': item['especie_variedad'] or '',
                'genero': item['genero'] or ''
            }
            for item in cached_data
        ]
    
    def get_germinacion_by_codigo(self, codigo: str) -> Optional[Dict[str, str]]:
        """Busca una germinación por código
        
        NOTA: En germinaciones se permiten códigos duplicados, por lo que este método
        retorna la primera germinación encontrada con ese código (para autocompletado).
        """
        try:
            # Usar .first() en lugar de .get() porque se permiten códigos duplicados
            germinacion = Germinacion.objects.filter(codigo=codigo).first()
            
            if germinacion:
                return {
                    'codigo': germinacion.codigo,
                    'especie': germinacion.especie_variedad or '',
                    'genero': germinacion.genero or '',
                    'permite_duplicados': True  # Indicar que se permiten duplicados
                }
            return None
        except Exception as e:
            logger.error(f"Error buscando germinación por código {codigo}: {e}")
            return None
    
    def get_germinacion_by_especie(self, especie: str) -> Optional[Dict[str, str]]:
        """Busca una germinación por especie/variedad para autocompletar código
        
        Retorna la primera germinación encontrada con esa especie (para autocompletado).
        """
        try:
            # Buscar por especie exacta primero
            germinacion = Germinacion.objects.filter(especie_variedad__iexact=especie).first()
            
            # Si no encuentra exacta, buscar que contenga la especie
            if not germinacion:
                germinacion = Germinacion.objects.filter(especie_variedad__icontains=especie).first()
            
            if germinacion:
                return {
                    'codigo': germinacion.codigo,
                    'especie': germinacion.especie_variedad or '',
                    'genero': germinacion.genero or '',
                    'permite_duplicados': True
                }
            return None
        except Exception as e:
            logger.error(f"Error buscando germinación por especie {especie}: {e}")
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
    
    def create(self, data: Dict[str, Any], user: Optional[User] = None) -> Germinacion:
        """Crea una nueva germinación con lógica específica"""
        # Asegurar que el responsable esté asignado
        if not data.get('responsable') and user:
            full_name = f"{user.first_name} {user.last_name}".strip()
            data['responsable'] = full_name if full_name else user.username
        
        # Calcular días de polinización automáticamente
        if data.get('fecha_ingreso') and data.get('fecha_polinizacion'):
            fecha_ingreso = data['fecha_ingreso']
            fecha_pol = data['fecha_polinizacion']
            
            if isinstance(fecha_ingreso, str):
                fecha_ingreso = datetime.strptime(fecha_ingreso, '%Y-%m-%d').date()
            if isinstance(fecha_pol, str):
                fecha_pol = datetime.strptime(fecha_pol, '%Y-%m-%d').date()
            
            data['dias_polinizacion'] = (fecha_ingreso - fecha_pol).days
        
        return super().create(data, user)
    
    def invalidate_related_caches(self):
        """Invalida caches relacionados cuando se modifica una germinación"""
        cache_keys = [
            'germinacion_codigos_unicos',
            'germinacion_codigos_con_especies'
        ]
        
        for key in cache_keys:
            self.invalidate_cache(key)


# Instancia global del servicio
germinacion_service = GerminacionService()