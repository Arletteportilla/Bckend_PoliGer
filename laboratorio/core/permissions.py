# SISTEMA DE PERMISOS PERSONALIZADOS PARA RBAC
# ============================================================================
from rest_framework import permissions
from rest_framework.permissions import BasePermission
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.http import JsonResponse

class RoleBasedPermission(BasePermission):
    """
    Permiso base para verificar roles de usuario
    """
    required_roles = []
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Verificar si el usuario tiene perfil
        if not hasattr(request.user, 'profile'):
            return False
        
        # Verificar si el usuario está activo
        if not request.user.profile.activo:
            return False
        
        # Verificar si el rol del usuario está en los roles requeridos
        return request.user.profile.rol in self.required_roles

class CanViewGerminaciones(RoleBasedPermission):
    """Permiso para ver germinaciones - Solo TIPO_1, TIPO_3, TIPO_4"""
    required_roles = ['TIPO_1', 'TIPO_3', 'TIPO_4']


class CanCreateGerminaciones(RoleBasedPermission):
    """Permiso para crear germinaciones - Solo TIPO_1, TIPO_3, TIPO_4"""
    required_roles = ['TIPO_1', 'TIPO_3', 'TIPO_4']


class CanEditGerminaciones(RoleBasedPermission):
    """Permiso para editar germinaciones - Solo TIPO_1, TIPO_3, TIPO_4"""
    required_roles = ['TIPO_1', 'TIPO_3', 'TIPO_4']


class CanViewPolinizaciones(RoleBasedPermission):
    """Permiso para ver polinizaciones - Solo TIPO_1, TIPO_2, TIPO_4"""
    required_roles = ['TIPO_1', 'TIPO_2', 'TIPO_4']


class CanCreatePolinizaciones(RoleBasedPermission):
    """Permiso para crear polinizaciones - Solo TIPO_1, TIPO_2, TIPO_4"""
    required_roles = ['TIPO_1', 'TIPO_2', 'TIPO_4']


class CanEditPolinizaciones(RoleBasedPermission):
    """Permiso para editar polinizaciones - Solo TIPO_1, TIPO_2, TIPO_4"""
    required_roles = ['TIPO_1', 'TIPO_2', 'TIPO_4']


class CanViewReportes(RoleBasedPermission):
    """Permiso para ver reportes"""
    required_roles = ['TIPO_1', 'TIPO_4']


class CanGenerateReportes(RoleBasedPermission):
    """Permiso para generar reportes"""
    required_roles = ['TIPO_1', 'TIPO_4']


class IsAdministrator(RoleBasedPermission):
    """Permiso solo para administradores"""
    required_roles = ['TIPO_4']


class CanExportData(RoleBasedPermission):
    """Permiso para exportar datos"""
    required_roles = ['TIPO_1', 'TIPO_4']


# ============================================================================
# DECORADORES PARA VISTAS BASADAS EN FUNCIONES
# ============================================================================

def require_role(allowed_roles):
    """
    Decorador que requiere que el usuario tenga uno de los roles especificados
    
    Usage:
        @require_role(['TIPO_1', 'TIPO_4'])
        def my_view(request):
            pass
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                from rest_framework.response import Response
                from rest_framework import status
                return Response({'error': 'Usuario no autenticado'}, status=status.HTTP_401_UNAUTHORIZED)
            
            if not hasattr(request.user, 'profile'):
                from rest_framework.response import Response
                from rest_framework import status
                return Response({'error': 'Usuario sin perfil configurado'}, status=status.HTTP_403_FORBIDDEN)
            
            if not request.user.profile.activo:
                from rest_framework.response import Response
                from rest_framework import status
                return Response({'error': 'Usuario inactivo'}, status=status.HTTP_403_FORBIDDEN)
            
            if request.user.profile.rol not in allowed_roles:
                from rest_framework.response import Response
                from rest_framework import status
                return Response({
                    'error': 'No tienes permisos para acceder a este recurso',
                    'required_roles': allowed_roles,
                    'user_role': request.user.profile.rol
                }, status=status.HTTP_403_FORBIDDEN)
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def require_germinacion_access(action='view'):
    """
    Decorador específico para acceso a germinaciones - Solo TIPO_1, TIPO_3, TIPO_4
    
    Args:
        action: 'view', 'create', 'editar'
    """
    role_mapping = {
        'view': ['TIPO_1', 'TIPO_3', 'TIPO_4'],
        'create': ['TIPO_1', 'TIPO_3', 'TIPO_4'],
        'edit': ['TIPO_1', 'TIPO_3', 'TIPO_4'],
    }
    
    allowed_roles = role_mapping.get(action, [])
    return require_role(allowed_roles)


def require_polinizacion_access(action='view'):
    """
    Decorador específico para acceso a polinizaciones - Solo TIPO_1, TIPO_2, TIPO_4
    
    Args:
        action: 'view', 'create', 'edit'
    """
    role_mapping = {
        'view': ['TIPO_1', 'TIPO_2', 'TIPO_4'],
        'create': ['TIPO_1', 'TIPO_2', 'TIPO_4'],
        'edit': ['TIPO_1', 'TIPO_2', 'TIPO_4'],
    }
    
    allowed_roles = role_mapping.get(action, [])
    return require_role(allowed_roles)


def require_admin():
    """Decorador que requiere permisos de administrador"""
    return require_role(['TIPO_4'])


def require_reports_access():
    """Decorador que requiere acceso a reportes"""
    return require_role(['TIPO_1', 'TIPO_4'])


# ============================================================================
# MIXINS PARA VIEWSETS
# ============================================================================

class RoleBasedViewSetMixin:
    """
    Mixin que agrega verificación de roles a los ViewSets
    """
    role_permissions = {}  # Debe ser definido en cada ViewSet
    
    def get_permissions(self):
        """
        Retorna los permisos basados en la acción y el rol
        """
        permission_list = [permissions.IsAuthenticated()]
        
        action = self.action
        if action in self.role_permissions:
            permission_class = self.role_permissions[action]
            permission_list.append(permission_class())
        
        return permission_list
    
    def check_object_permissions(self, request, obj):
        """
        Verifica permisos a nivel de objeto
        """
        super().check_object_permissions(request, obj)
        
        # Verificar si el usuario puede acceder a este objeto específico
        # Por ejemplo, solo puede editar sus propios registros (excepto admin)
        if hasattr(obj, 'creado_por') and obj.creado_por:
            if (request.user.profile.rol not in ['TIPO_4'] and 
                obj.creado_por != request.user):
                raise PermissionDenied("Solo puedes editar tus propios registros")


# ============================================================================
# UTILIDADES PARA VERIFICACIÓN DE PERMISOS
# ============================================================================

def user_has_role(user, required_roles):
    """
    Verifica si un usuario tiene uno de los roles requeridos
    
    Args:
        user: Usuario de Django
        required_roles: Lista de roles permitidos
    
    Returns:
        bool: True si el usuario tiene el rol, False en caso contrario
    """
    if not user or not user.is_authenticated:
        return False
    
    if not hasattr(user, 'profile'):
        return False
    
    if not user.profile.activo:
        return False
    
    return user.profile.rol in required_roles


def get_user_permissions(user):
    """
    Obtiene todos los permisos de un usuario
    
    Args:
        user: Usuario de Django
    
    Returns:
        dict: Diccionario con los permisos del usuario
    """
    if not user or not user.is_authenticated:
        return {}
    
    if not hasattr(user, 'profile'):
        return {}
    
    return user.profile.get_permisos_detallados()


def filter_queryset_by_role(queryset, user, model_name):
    """
    Filtra un queryset basado en el rol del usuario
    
    Args:
        queryset: QuerySet a filtrar
        user: Usuario actual
        model_name: Nombre del modelo ('germinacion', 'polinizacion')
    
    Returns:
        QuerySet filtrado
    """
    if not user or not user.is_authenticated:
        return queryset.none()
    
    if not hasattr(user, 'profile'):
        return queryset.none()
    
    # Los administradores y usuarios con acceso completo ven todo
    if user.profile.rol in ['TIPO_4', 'TIPO_1']:
        return queryset
    
    # Para otros roles, solo ven sus propios registros
    if model_name == 'germinacion':
        if user.profile.puede_ver_germinaciones:
            return queryset.filter(usuario_creador=user)
    elif model_name == 'polinizacion':
        if user.profile.puede_ver_polinizaciones:
            return queryset.filter(creado_por=user)
    
    return queryset.none()