"""
Filtros personalizados para los modelos de la API
"""
from django_filters import rest_framework as filters
from laboratorio.core.models import Germinacion, Polinizacion


class GerminacionFilter(filters.FilterSet):
    """
    Filtros para el modelo Germinacion
    Permite filtrar por múltiples campos con diferentes tipos de búsqueda
    """

    # Filtros de texto (búsqueda parcial case-insensitive)
    codigo = filters.CharFilter(field_name='codigo', lookup_expr='icontains')
    especie_variedad = filters.CharFilter(field_name='especie_variedad', lookup_expr='icontains')
    responsable = filters.CharFilter(field_name='responsable', lookup_expr='icontains')
    percha = filters.CharFilter(field_name='percha', lookup_expr='icontains')
    genero = filters.CharFilter(field_name='genero', lookup_expr='icontains')

    # Filtros exactos
    estado_capsulas = filters.ChoiceFilter(
        field_name='estado_capsulas',
        choices=Germinacion.ESTADOS_CAPSULAS
    )

    clima = filters.ChoiceFilter(
        field_name='clima',
        choices=Germinacion.CLIMAS
    )

    tipo_polinizacion = filters.ChoiceFilter(
        field_name='tipo_polinizacion',
        choices=Germinacion.TIPOS_POLINIZACION
    )

    # Filtros de rango de fechas
    fecha_siembra_desde = filters.DateFilter(field_name='fecha_siembra', lookup_expr='gte')
    fecha_siembra_hasta = filters.DateFilter(field_name='fecha_siembra', lookup_expr='lte')

    fecha_polinizacion_desde = filters.DateFilter(field_name='fecha_polinizacion', lookup_expr='gte')
    fecha_polinizacion_hasta = filters.DateFilter(field_name='fecha_polinizacion', lookup_expr='lte')

    fecha_creacion_desde = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='gte')
    fecha_creacion_hasta = filters.DateTimeFilter(field_name='fecha_creacion', lookup_expr='lte')

    # Filtros numéricos
    cantidad_solicitada_min = filters.NumberFilter(field_name='cantidad_solicitada', lookup_expr='gte')
    cantidad_solicitada_max = filters.NumberFilter(field_name='cantidad_solicitada', lookup_expr='lte')

    disponibles_min = filters.NumberFilter(field_name='disponibles', lookup_expr='gte')
    disponibles_max = filters.NumberFilter(field_name='disponibles', lookup_expr='lte')

    # Filtro booleano
    semilla_en_stock = filters.BooleanFilter(field_name='semilla_en_stock')

    class Meta:
        model = Germinacion
        fields = [
            'codigo',
            'especie_variedad',
            'responsable',
            'percha',
            'genero',
            'estado_capsulas',
            'clima',
            'tipo_polinizacion',
            'semilla_en_stock',
        ]


class PolinizacionFilter(filters.FilterSet):
    """
    Filtros para el modelo Polinizacion
    """

    # Filtros de texto
    codigo = filters.CharFilter(field_name='codigo', lookup_expr='icontains')
    madre_genero = filters.CharFilter(field_name='madre_genero', lookup_expr='icontains')
    padre_genero = filters.CharFilter(field_name='padre_genero', lookup_expr='icontains')
    responsable = filters.CharFilter(field_name='responsable', lookup_expr='icontains')

    # Filtros exactos
    estado = filters.ChoiceFilter(
        field_name='estado',
        choices=Polinizacion.ESTADOS_POLINIZACION
    )

    tipo_polinizacion = filters.ChoiceFilter(
        field_name='tipo_polinizacion',
        choices=Polinizacion.TIPOS_POLINIZACION
    )

    # Filtros de rango de fechas
    fechapol_desde = filters.DateFilter(field_name='fechapol', lookup_expr='gte')
    fechapol_hasta = filters.DateFilter(field_name='fechapol', lookup_expr='lte')

    fechamad_desde = filters.DateFilter(field_name='fechamad', lookup_expr='gte')
    fechamad_hasta = filters.DateFilter(field_name='fechamad', lookup_expr='lte')

    class Meta:
        model = Polinizacion
        fields = [
            'codigo',
            'madre_genero',
            'padre_genero',
            'responsable',
            'estado',
            'tipo_polinizacion',
        ]
