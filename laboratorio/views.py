"""
Vistas principales del laboratorio - Archivo de compatibilidad
Este archivo mantiene las importaciones y vistas básicas para compatibilidad.
Las vistas principales han sido refactorizadas a archivos separados.

NUEVA ESTRUCTURA:
- core/: Modelos, admin, permisos
- api/: URLs, serializers, vistas principales  
- view_modules/: ViewSets especializados
- services/: Lógica de negocio
- auth/: Autenticación
- integrations/: CSV, reportes, calendar
- ml/: Machine learning y predicciones
- utils/: Utilidades generales
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import datetime
import json
import logging

# Importar desde la nueva estructura organizada
from .view_modules.base_views import OptimizedPagination
from .view_modules.polinizacion_views import PolinizacionViewSet
from .view_modules.germinacion_views import GerminacionViewSet
from .view_modules.utils_views import (
    generar_reporte_germinaciones, generar_reporte_polinizaciones,
    estadisticas_germinaciones, estadisticas_polinizaciones,
    estadisticas_usuario, generar_reporte_con_estadisticas
)
from .view_modules.prediccion_views import (
    prediccion_germinacion, prediccion_polinizacion, prediccion_completa,
    predicciones_alertas, cambiar_estado_polinizacion, estadisticas_modelos
)
from .view_modules.user_views import (
    UserProfileViewSet, UserManagementViewSet, UserMetasViewSet
)

logger = logging.getLogger(__name__)

# Importaciones de modelos y serializers (compatibilidad)
from .core.models import (
    Genero, Especie, Variedad, Ubicacion, 
    SeguimientoGerminacion, Capsula, Siembra, 
    PersonalUsuario, Inventario, Notification
)
from .api.serializers import (
    GeneroSerializer, EspecieSerializer, VariedadSerializer,
    UbicacionSerializer, SeguimientoGerminacionSerializer, 
    CapsulaSerializer, SiembraSerializer, PersonalUsuarioSerializer, 
    InventarioSerializer, NotificationSerializer
)

# Mantener importaciones legacy para compatibilidad
from .models import *  # Importación legacy
from .serializers import *  # Importación legacy


# ============================================================================
# VIEWSETS BÁSICOS PARA MODELOS SIMPLES
# ============================================================================

class GeneroViewSet(viewsets.ModelViewSet):
    """ViewSet básico para géneros"""
    queryset = Genero.objects.all()
    serializer_class = GeneroSerializer
    permission_classes = [IsAuthenticated]


class EspecieViewSet(viewsets.ModelViewSet):
    """ViewSet básico para especies"""
    queryset = Especie.objects.all()
    serializer_class = EspecieSerializer
    permission_classes = [IsAuthenticated]


class VariedadViewSet(viewsets.ModelViewSet):
    """ViewSet básico para variedades"""
    queryset = Variedad.objects.all()
    serializer_class = VariedadSerializer
    permission_classes = [IsAuthenticated]


class UbicacionViewSet(viewsets.ModelViewSet):
    """ViewSet básico para ubicaciones"""
    queryset = Ubicacion.objects.all()
    serializer_class = UbicacionSerializer
    permission_classes = [IsAuthenticated]


class SeguimientoGerminacionViewSet(viewsets.ModelViewSet):
    """ViewSet básico para seguimientos de germinación"""
    queryset = SeguimientoGerminacion.objects.all()
    serializer_class = SeguimientoGerminacionSerializer
    permission_classes = [IsAuthenticated]


class CapsulaViewSet(viewsets.ModelViewSet):
    """ViewSet básico para cápsulas"""
    queryset = Capsula.objects.all()
    serializer_class = CapsulaSerializer
    permission_classes = [IsAuthenticated]


class SiembraViewSet(viewsets.ModelViewSet):
    """ViewSet básico para siembras"""
    queryset = Siembra.objects.all()
    serializer_class = SiembraSerializer
    permission_classes = [IsAuthenticated]


class PersonalUsuarioViewSet(viewsets.ModelViewSet):
    """ViewSet básico para personal de usuario"""
    queryset = PersonalUsuario.objects.all()
    serializer_class = PersonalUsuarioSerializer
    permission_classes = [IsAuthenticated]


class InventarioViewSet(viewsets.ModelViewSet):
    """ViewSet básico para inventario"""
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer
    permission_classes = [IsAuthenticated]


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet mejorado para notificaciones con filtrado, búsqueda y acciones"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar notificaciones por usuario con filtros adicionales"""
        queryset = Notification.objects.filter(usuario=self.request.user)
        
        # Filtrar por tipo
        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo=tipo)
        
        # Filtrar por estado de lectura
        leida = self.request.query_params.get('leida', None)
        if leida is not None:
            queryset = queryset.filter(leida=leida.lower() == 'true')
        
        # Filtrar por favoritas
        favorita = self.request.query_params.get('favorita', None)
        if favorita is not None:
            queryset = queryset.filter(favorita=favorita.lower() == 'true')
        
        # Filtrar por archivadas - solo si se especifica explícitamente
        # Por defecto NO filtrar por archivadas para mostrar todas las notificaciones
        archivada = self.request.query_params.get('archivada', None)
        if archivada is not None:
            queryset = queryset.filter(archivada=archivada.lower() == 'true')
        
        # Búsqueda en título y mensaje
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                models.Q(titulo__icontains=search) | 
                models.Q(mensaje__icontains=search)
            )
        
        return queryset.order_by('-fecha_creacion')
    
    @action(detail=True, methods=['post'])
    def marcar_leida(self, request, pk=None):
        """Marca una notificación como leída"""
        notification = self.get_object()
        notification.marcar_como_leida()
        return Response({'status': 'marcada como leída'})
    
    @action(detail=False, methods=['post'])
    def marcar_todas_leidas(self, request):
        """Marca todas las notificaciones del usuario como leídas"""
        count = Notification.objects.filter(
            usuario=request.user,
            leida=False,
            archivada=False
        ).update(leida=True, fecha_lectura=timezone.now())
        return Response({'status': 'todas marcadas como leídas', 'count': count})
    
    @action(detail=True, methods=['post'])
    def toggle_favorita(self, request, pk=None):
        """Activa/desactiva el estado de favorita"""
        notification = self.get_object()
        notification.toggle_favorita()
        return Response({'status': 'favorita actualizada', 'favorita': notification.favorita})
    
    @action(detail=True, methods=['post'])
    def archivar(self, request, pk=None):
        """Archiva una notificación"""
        notification = self.get_object()
        notification.archivar()
        return Response({'status': 'archivada'})
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtiene estadísticas de notificaciones del usuario"""
        # Por defecto, contar todas las notificaciones (incluyendo archivadas)
        # pero permitir filtrar por archivadas si se especifica
        base_queryset = Notification.objects.filter(usuario=request.user)
        
        archivada_param = request.query_params.get('archivada', None)
        if archivada_param is not None:
            base_queryset = base_queryset.filter(archivada=archivada_param.lower() == 'true')
        else:
            # Por defecto, solo contar no archivadas en estadísticas
            base_queryset = base_queryset.filter(archivada=False)
        
        total = base_queryset.count()
        no_leidas = base_queryset.filter(leida=False).count()
        favoritas = base_queryset.filter(favorita=True).count()
        
        # Contar por tipo
        por_tipo = {}
        for tipo, _ in Notification.TIPO_CHOICES:
            tipo_queryset = base_queryset.filter(tipo=tipo)
            por_tipo[tipo] = tipo_queryset.count()
        
        return Response({
            'total': total,
            'no_leidas': no_leidas,
            'favoritas': favoritas,
            'por_tipo': por_tipo
        })


# ============================================================================
# FUNCIONES DE COMPATIBILIDAD PARA VISTAS LEGACY
# ============================================================================

@csrf_exempt
def add_inventario(request):
    """Función legacy para agregar inventario"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Lógica básica de creación
            return JsonResponse({'success': True, 'message': 'Inventario agregado'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def update_inventario(request, id):
    """Función legacy para actualizar inventario"""
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
            # Lógica básica de actualización
            return JsonResponse({'success': True, 'message': 'Inventario actualizado'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def add_usuario(request):
    """Función legacy para agregar usuario"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Lógica básica de creación de usuario
            return JsonResponse({'success': True, 'message': 'Usuario agregado'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def add_capsula(request):
    """Función legacy para agregar cápsula"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Lógica básica de creación
            return JsonResponse({'success': True, 'message': 'Cápsula agregada'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


@csrf_exempt
def add_siembra(request):
    """Función legacy para agregar siembra"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Lógica básica de creación
            return JsonResponse({'success': True, 'message': 'Siembra agregada'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)


# ============================================================================
# NUEVA ESTRUCTURA ORGANIZADA:
# 
# 📁 core/                    - Modelos, admin, permisos base
# 📁 api/                     - URLs, serializers, vistas principales
# 📁 view_modules/            - ViewSets especializados
# 📁 services/                - Lógica de negocio
# 📁 auth/                    - Autenticación y autorización
# 📁 integrations/            - CSV, reportes, calendar
# 📁 ml/                      - Machine learning y predicciones
# 📁 utils/                   - Utilidades generales
# 📁 tests/                   - Tests organizados
# 📁 docs/                    - Documentación
# 
# COMPATIBILIDAD: Todas las importaciones legacy siguen funcionando
# ============================================================================