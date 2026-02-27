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

            # Capturar contraseña en texto plano ANTES de que create_user la hashee
            plain_password = request.data.get('password', '')

            # El serializer se encarga de crear tanto el usuario como el perfil
            user = serializer.save()

            # Obtener el perfil creado (refresh para evitar caché del signal post_save)
            user.refresh_from_db()
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

            # Enviar email de bienvenida (no bloquea la creación del usuario)
            email_sent = False
            try:
                from ..services.email_service import email_service
                email_sent = email_service.enviar_email_bienvenida(
                    user=user,
                    password=plain_password,
                    rol_display=profile.get_rol_display(),
                )
            except Exception as email_error:
                logger.error(
                    f"Error al enviar email de bienvenida para {user.username}: "
                    f"{email_error}"
                )

            response_data['email_enviado'] = email_sent

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

    @action(detail=True, methods=['post'], url_path='cambiar_estado')
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

    @action(detail=True, methods=['post'], url_path='cambiar-password')
    def cambiar_password(self, request, pk=None):
        """Cambiar contraseña de un usuario (solo admin)"""
        try:
            user = self.get_object()

            password = request.data.get('password')
            confirm_password = request.data.get('confirm_password')

            if not password or not confirm_password:
                return Response(
                    {'error': 'Los campos password y confirm_password son requeridos'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if password != confirm_password:
                return Response(
                    {'error': 'Las contraseñas no coinciden'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if len(password) < 8:
                return Response(
                    {'error': 'La contraseña debe tener al menos 8 caracteres'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(password)
            user.save()

            logger.info(f"Contraseña cambiada para usuario {user.username} por {request.user.username}")

            return Response({
                'mensaje': f'Contraseña actualizada exitosamente para {user.username}'
            })

        except Exception as e:
            logger.error(f"Error cambiando contraseña del usuario {pk}: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='estadisticas_usuarios')
    def estadisticas_usuarios(self, request):
        """Estadísticas de usuarios agrupadas por rol"""
        try:
            from django.contrib.auth.models import User as DjangoUser
            from ..models import UserProfile

            roles_display = dict(UserProfile.TIPOS_USUARIO)
            por_rol = {}
            for codigo, nombre in UserProfile.TIPOS_USUARIO:
                total = UserProfile.objects.filter(rol=codigo).count()
                por_rol[codigo] = {'nombre': nombre, 'total': total}

            activos = UserProfile.objects.filter(activo=True).count()
            inactivos = UserProfile.objects.filter(activo=False).count()
            total = DjangoUser.objects.count()

            return Response({
                'por_rol': por_rol,
                'usuarios_activos': activos,
                'usuarios_inactivos': inactivos,
                'total_usuarios': total
            })
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de usuarios: {e}")
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

    @action(detail=False, methods=['post'], url_path='bulk-toggle-status')
    def bulk_toggle_status(self, request):
        """Activar/desactivar múltiples usuarios a la vez"""
        try:
            user_ids = request.data.get('user_ids', [])
            nuevo_estado = request.data.get('status')

            if not user_ids:
                return Response(
                    {'error': 'El campo user_ids es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if nuevo_estado is None:
                return Response(
                    {'error': 'El campo status es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            actualizados = 0
            errores = []

            with transaction.atomic():
                for user_id in user_ids:
                    try:
                        user = User.objects.get(pk=user_id)
                        profile, _ = UserProfile.objects.get_or_create(user=user)
                        profile.activo = bool(nuevo_estado)
                        profile.save()
                        user.is_active = profile.activo
                        user.save()
                        actualizados += 1
                    except User.DoesNotExist:
                        errores.append(f'Usuario {user_id} no encontrado')

            estado_texto = 'activados' if nuevo_estado else 'desactivados'
            logger.info(f"Bulk toggle: {actualizados} usuarios {estado_texto} por {request.user.username}")

            return Response({
                'mensaje': f'{actualizados} usuarios {estado_texto} exitosamente',
                'actualizados': actualizados,
                'errores': errores
            })

        except Exception as e:
            logger.error(f"Error en bulk toggle status: {e}")
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
    
    @action(detail=True, methods=['post'], url_path='actualizar_progreso')
    def actualizar_progreso(self, request, pk=None):
        """Calcula y actualiza el progreso mensual del usuario vs sus metas"""
        try:
            from django.utils import timezone
            from django.db.models import Count

            profile = self.get_object()
            user = profile.user
            ahora = timezone.now()
            inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

            from ..models import Germinacion, Polinizacion
            germinaciones_mes = Germinacion.objects.filter(
                creado_por=user,
                fecha_creacion__gte=inicio_mes
            ).count()
            polinizaciones_mes = Polinizacion.objects.filter(
                creado_por=user,
                fecha_creacion__gte=inicio_mes
            ).count() if hasattr(Polinizacion, 'creado_por') else 0

            meta_germ = profile.meta_germinaciones_mes or 1
            meta_pol = profile.meta_polinizaciones_mes or 1
            meta_ef = profile.meta_eficiencia or 1

            progreso_germ = min(100, round(germinaciones_mes / meta_germ * 100, 1))
            progreso_pol = min(100, round(polinizaciones_mes / meta_pol * 100, 1))
            eficiencia = round((progreso_germ + progreso_pol) / 2, 1)

            logger.info(f"Progreso calculado para usuario {user.username}")

            return Response({
                'usuario': user.username,
                'mes': ahora.strftime('%Y-%m'),
                'progreso': {
                    'germinaciones': {
                        'actual': germinaciones_mes,
                        'meta': profile.meta_germinaciones_mes,
                        'porcentaje': progreso_germ
                    },
                    'polinizaciones': {
                        'actual': polinizaciones_mes,
                        'meta': profile.meta_polinizaciones_mes,
                        'porcentaje': progreso_pol
                    },
                    'eficiencia': {
                        'actual': eficiencia,
                        'meta': profile.meta_eficiencia,
                        'porcentaje': min(100, round(eficiencia / meta_ef * 100, 1))
                    }
                }
            })
        except Exception as e:
            logger.error(f"Error actualizando progreso del usuario: {e}")
            return Response(
                {'error': 'Error interno del servidor'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

