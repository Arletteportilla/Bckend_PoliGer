"""
Vistas para gestión de usuarios y perfiles
"""
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

from ..models import UserProfile, Notification
from ..serializers import (
    UserProfileSerializer, UserWithProfileSerializer, 
    CreateUserWithProfileSerializer, UpdateUserProfileSerializer,
    UpdateUserMetasSerializer, PermissionsSerializer
)
from ..permissions import RoleBasedViewSetMixin, IsAdministrator, require_admin
from .base_views import BaseServiceViewSet, ErrorHandlerMixin

logger = logging.getLogger(__name__)


class UserProfileViewSet(RoleBasedViewSetMixin, BaseServiceViewSet, ErrorHandlerMixin):
    """ViewSet para gestión de perfiles de usuario"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    # NO definir permission_classes aquí - dejar que RoleBasedViewSetMixin lo maneje

    # Definir permisos por acción
    role_permissions = {
        'list': IsAdministrator,
        'retrieve': IsAuthenticated,
        'create': IsAdministrator,
        'update': IsAdministrator,
        'partial_update': IsAdministrator,
        'destroy': IsAdministrator,
        'mi_perfil': IsAuthenticated,
        'actualizar_mi_perfil': IsAuthenticated,
        'actualizar_metas': IsAuthenticated,
    }
    
    def get_queryset(self):
        """Filtrar perfiles según el rol del usuario"""
        user = self.request.user
        
        # Los administradores ven todos los perfiles
        if hasattr(user, 'profile') and user.profile.rol == 'TIPO_4':
            return UserProfile.objects.select_related('user').all()
        
        # Otros usuarios solo ven su propio perfil
        return UserProfile.objects.filter(user=user)
    
    @action(detail=False, methods=['get'], url_path='mi-perfil')
    def mi_perfil(self, request):
        """Obtiene el perfil del usuario actual"""
        try:
            user = request.user
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            if created:
                logger.info(f"Perfil creado automáticamente para usuario: {user.username}")
            
            serializer = UserWithProfileSerializer({
                'user': user,
                'profile': profile
            })
            
            return Response(serializer.data)
            
        except Exception as e:
            return self.handle_error(e, "Error obteniendo perfil del usuario")
    
    @action(detail=False, methods=['put', 'patch'], url_path='actualizar-mi-perfil')
    def actualizar_mi_perfil(self, request):
        """Actualiza el perfil del usuario actual"""
        try:
            user = request.user
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Usar serializer específico para actualización de perfil
            serializer = UpdateUserProfileSerializer(
                profile, 
                data=request.data, 
                partial=request.method == 'PATCH'
            )
            
            if serializer.is_valid():
                serializer.save()
                
                # Retornar perfil actualizado
                response_serializer = UserWithProfileSerializer({
                    'user': user,
                    'profile': profile
                })
                
                logger.info(f"Perfil actualizado para usuario: {user.username}")
                return Response(response_serializer.data)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return self.handle_error(e, "Error actualizando perfil del usuario")
    
    @action(detail=False, methods=['put', 'patch'], url_path='actualizar-metas')
    def actualizar_metas(self, request):
        """Actualiza las metas de rendimiento del usuario"""
        try:
            user = request.user
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            serializer = UpdateUserMetasSerializer(
                profile,
                data=request.data,
                partial=request.method == 'PATCH'
            )
            
            if serializer.is_valid():
                serializer.save()
                
                logger.info(f"Metas actualizadas para usuario: {user.username}")
                return Response({
                    'mensaje': 'Metas actualizadas exitosamente',
                    'metas': {
                        'meta_germinaciones_mes': profile.meta_germinaciones_mes,
                        'meta_polinizaciones_mes': profile.meta_polinizaciones_mes,
                        'meta_eficiencia': profile.meta_eficiencia
                    }
                })
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            return self.handle_error(e, "Error actualizando metas del usuario")


class UserManagementViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión completa de usuarios (solo administradores)"""
    queryset = User.objects.all()
    serializer_class = UserWithProfileSerializer

    def get_permissions(self):
        """Solo administradores pueden gestionar usuarios"""
        return [IsAuthenticated(), IsAdministrator()]

    def get_queryset(self):
        """Optimizar consulta con select_related"""
        return User.objects.select_related('profile').all().order_by('username')
    
    def get_serializer_class(self):
        """Usar diferentes serializers según la acción"""
        if self.action == 'create':
            return CreateUserWithProfileSerializer
        elif self.action in ['update', 'partial_update']:
            return UpdateUserProfileSerializer
        return UserWithProfileSerializer
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Crear usuario con perfil"""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # El serializer se encarga de crear tanto el usuario como el perfil
            user = serializer.save()

            # Obtener el perfil creado
            profile = user.profile

            # Retornar usuario creado con perfil
            response_data = {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'profile': {
                    'id': profile.id,
                    'rol': profile.rol,
                    'rol_display': profile.get_rol_display(),
                    'telefono': profile.telefono,
                    'departamento': profile.departamento,
                    'fecha_ingreso': profile.fecha_ingreso,
                    'activo': profile.activo
                }
            }

            logger.info(f"Usuario creado: {user.username} con rol {profile.rol}")
            return Response(response_data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            logger.error(f"Error de validación creando usuario: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error creando usuario: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Error interno del servidor: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        """Eliminar usuario"""
        try:
            user = self.get_object()
            username = user.username
            user_id = user.id

            logger.info(f"Intentando eliminar usuario: {username} (ID: {user_id})")

            # Verificar que no sea el usuario actual
            if request.user.id == user_id:
                logger.warning(f"Intento de auto-eliminación bloqueado para usuario: {username}")
                return Response(
                    {'error': 'No puedes eliminar tu propia cuenta'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Eliminar el usuario (el perfil se eliminará en cascada)
            user.delete()

            logger.info(f"Usuario eliminado exitosamente: {username} (ID: {user_id})")
            return Response(
                {'message': f'Usuario {username} eliminado correctamente'},
                status=status.HTTP_204_NO_CONTENT
            )

        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            import traceback
            traceback.print_exc()
            return Response(
                {'error': f'Error eliminando usuario: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """Activar/desactivar usuario"""
        try:
            user = self.get_object()
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            nuevo_estado = request.data.get('activo')
            if nuevo_estado is None:
                return Response(
                    {'error': 'El campo activo es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            profile.activo = bool(nuevo_estado)
            profile.save()
            
            # También actualizar el estado del usuario de Django
            user.is_active = profile.activo
            user.save()
            
            estado_texto = "activado" if profile.activo else "desactivado"
            logger.info(f"Usuario {user.username} {estado_texto}")
            
            return Response({
                'mensaje': f'Usuario {estado_texto} exitosamente',
                'usuario': user.username,
                'activo': profile.activo
            })
            
        except Exception as e:
            logger.error(f"Error cambiando estado del usuario {pk}: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='cambiar-rol')
    def cambiar_rol(self, request, pk=None):
        """Cambiar rol del usuario"""
        try:
            user = self.get_object()
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            nuevo_rol = request.data.get('rol')
            if not nuevo_rol:
                return Response(
                    {'error': 'El campo rol es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validar que el rol sea válido
            roles_validos = [choice[0] for choice in UserProfile.TIPOS_USUARIO]
            if nuevo_rol not in roles_validos:
                return Response(
                    {'error': f'Rol inválido. Roles válidos: {", ".join(roles_validos)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            rol_anterior = profile.rol
            profile.rol = nuevo_rol
            profile.save()
            
            logger.info(f"Rol del usuario {user.username} cambiado de {rol_anterior} a {nuevo_rol}")
            
            return Response({
                'mensaje': f'Rol actualizado de {rol_anterior} a {nuevo_rol}',
                'usuario': user.username,
                'rol_anterior': rol_anterior,
                'rol_nuevo': nuevo_rol
            })
            
        except Exception as e:
            logger.error(f"Error cambiando rol del usuario {pk}: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='permisos')
    def permisos(self, request):
        """Obtiene información sobre permisos y roles"""
        try:
            permisos_info = {
                'roles': [
                    {'codigo': choice[0], 'nombre': choice[1]} 
                    for choice in UserProfile.TIPOS_USUARIO
                ],
                'permisos_por_rol': {
                    'TIPO_1': ['view_germinaciones', 'create_germinaciones'],
                    'TIPO_2': ['view_polinizaciones', 'create_polinizaciones'],
                    'TIPO_3': ['view_germinaciones', 'view_polinizaciones', 'create_germinaciones', 'create_polinizaciones'],
                    'TIPO_4': ['all_permissions']
                }
            }
            
            return Response(permisos_info)
            
        except Exception as e:
            logger.error(f"Error obteniendo información de permisos: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserMetasViewSet(viewsets.ModelViewSet):
    """ViewSet para gestionar metas de rendimiento de usuarios"""
    queryset = UserProfile.objects.all()
    serializer_class = UpdateUserMetasSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar según el usuario"""
        user = self.request.user
        
        # Los administradores pueden ver todas las metas
        if hasattr(user, 'profile') and user.profile.rol == 'TIPO_4':
            return UserProfile.objects.select_related('user').all()
        
        # Otros usuarios solo ven sus propias metas
        return UserProfile.objects.filter(user=user)
    
    @action(detail=False, methods=['get'], url_path='mis-metas')
    def mis_metas(self, request):
        """Obtiene las metas del usuario actual"""
        try:
            user = request.user
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            return Response({
                'usuario': user.username,
                'metas': {
                    'meta_germinaciones_mes': profile.meta_germinaciones_mes,
                    'meta_polinizaciones_mes': profile.meta_polinizaciones_mes,
                    'meta_eficiencia': profile.meta_eficiencia
                },
                'progreso': {
                    # Aquí se calcularía el progreso real vs las metas
                    'germinaciones_mes_actual': 0,  # Calcular desde la base de datos
                    'polinizaciones_mes_actual': 0,  # Calcular desde la base de datos
                    'eficiencia_actual': 0.0  # Calcular desde la base de datos
                }
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo metas del usuario: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )