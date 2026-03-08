import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .authentication import get_tokens_for_user
from django.utils import timezone
from ..core.permissions import IsAdministrator

logger = logging.getLogger(__name__)


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'status': 'healthy',
            'message': 'Backend funcionando correctamente',
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)


class RegisterView(APIView):
    """
    Registro de usuarios via API directa.
    Protegido: solo administradores pueden crear usuarios por esta via.
    El flujo principal de creacion de usuarios es UserManagementViewSet.create().
    """
    permission_classes = [IsAuthenticated, IsAdministrator]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')

        if not username or not email or not password:
            return Response(
                {'error': 'Por favor proporcione username, email y contrasena'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'El nombre de usuario ya existe'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )

        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Por favor proporcione usuario y contrasena'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user is not None:
            if user.is_active:
                tokens = get_tokens_for_user(user)
                try:
                    from ..services.notification_service import notification_service
                    notification_service.crear_notificacion_sistema(
                        usuario=user,
                        tipo='MENSAJE',
                        titulo='Inicio de sesion exitoso',
                        mensaje=f'Has iniciado sesion en PoliGer el {timezone.now().strftime("%d/%m/%Y a las %H:%M")}.',
                        detalles={'accion': 'login', 'username': user.username}
                    )
                except Exception as e:
                    logger.warning(f"No se pudo crear notificacion de login para {user.username}: {e}")
                return Response(tokens, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Esta cuenta esta desactivada'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            return Response(
                {'error': 'Credenciales invalidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ProtectedView(APIView):
    """
    Retorna los datos del perfil del usuario autenticado.
    Excluida del permiso PasswordNotExpired para que el usuario pueda
    consultar su estado y saber que debe cambiar su contrasena.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user_data = {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }

            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                user_data.update({
                    'rol': profile.rol,
                    'rol_display': profile.get_rol_display(),
                    'telefono': profile.telefono,
                    'departamento': profile.departamento,
                    'fecha_ingreso': profile.fecha_ingreso.isoformat() if profile.fecha_ingreso else None,
                    'activo': profile.activo,
                    'debe_cambiar_password': profile.debe_cambiar_password,
                    'permisos': profile.get_permisos_detallados()
                })
            else:
                return Response(
                    {'error': 'Tu cuenta no tiene un perfil de rol configurado. Contacta al administrador.'},
                    status=status.HTTP_403_FORBIDDEN
                )

            return Response({
                'message': 'Esta es una vista protegida',
                'user': user_data
            })
        except Exception as e:
            logger.exception(f"Error obteniendo datos del usuario {request.user.username}")
            return Response(
                {'error': 'Error obteniendo datos del usuario'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CambiarPasswordInicialView(APIView):
    """
    Permite al usuario cambiar su contrasena temporal obligatoria.
    Excluida del permiso PasswordNotExpired intencionalmente para que
    usuarios con debe_cambiar_password=True puedan acceder a este endpoint.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        password_actual = request.data.get('password_actual')
        password_nuevo = request.data.get('password_nuevo')

        if not password_actual or not password_nuevo:
            return Response(
                {'error': 'password_actual y password_nuevo son requeridos'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not request.user.check_password(password_actual):
            return Response(
                {'error': 'La contrasena actual es incorrecta'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(password_nuevo) < 8:
            return Response(
                {'error': 'La nueva contrasena debe tener al menos 8 caracteres'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password_actual == password_nuevo:
            return Response(
                {'error': 'La nueva contrasena debe ser diferente a la actual'},
                status=status.HTTP_400_BAD_REQUEST
            )

        request.user.set_password(password_nuevo)
        request.user.save()

        profile = getattr(request.user, 'profile', None)
        if profile and profile.debe_cambiar_password:
            profile.debe_cambiar_password = False
            profile.save(update_fields=['debe_cambiar_password'])

        logger.info(f"Usuario {request.user.username} cambio su contrasena inicial exitosamente")
        return Response({'message': 'Contrasena cambiada exitosamente. Ya puedes usar el sistema.'})


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get('refresh')

        if not refresh_token:
            return Response(
                {'error': 'Token de refresh requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            refresh = RefreshToken(refresh_token)
            access_token = str(refresh.access_token)
            return Response({'access': access_token}, status=status.HTTP_200_OK)
        except Exception:
            return Response(
                {'error': 'Token de refresh invalido'},
                status=status.HTTP_401_UNAUTHORIZED
            )
