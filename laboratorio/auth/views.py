from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from .authentication import get_tokens_for_user
from django.utils import timezone

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'message': 'Backend funcionando correctamente',
            'timestamp': timezone.now().isoformat()
        }, status=status.HTTP_200_OK)

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not username or not email or not password:
            return Response(
                {'error': 'Por favor proporcione username, email y contraseña'},
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
                {'error': 'Por favor proporcione usuario y contraseña'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user = authenticate(username=username, password=password)
        
        if user is not None:
            if user.is_active:
                tokens = get_tokens_for_user(user)
                return Response(tokens, status=status.HTTP_200_OK)
            else:
                return Response(
                    {'error': 'Esta cuenta está desactivada'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            return Response(
                {'error': 'Credenciales inválidas'},
                status=status.HTTP_401_UNAUTHORIZED
            )
            
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            # Obtener información básica del usuario
            user_data = {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
            }
            
            # Obtener información del perfil si existe
            if hasattr(request.user, 'profile'):
                profile = request.user.profile
                user_data.update({
                    'rol': profile.rol,
                    'rol_display': profile.get_rol_display(),
                    'telefono': profile.telefono,
                    'departamento': profile.departamento,
                    'fecha_ingreso': profile.fecha_ingreso.isoformat() if profile.fecha_ingreso else None,
                    'activo': profile.activo,
                    'permisos': profile.get_permisos_detallados()
                })
            else:
                # Si no tiene perfil, crear uno por defecto
                from laboratorio.core.models import UserProfile
                profile = UserProfile.objects.create(
                    user=request.user,
                    rol='TIPO_3'  # Rol por defecto
                )
                user_data.update({
                    'rol': profile.rol,
                    'rol_display': profile.get_rol_display(),
                    'telefono': profile.telefono,
                    'departamento': profile.departamento,
                    'fecha_ingreso': None,
                    'activo': profile.activo,
                    'permisos': profile.get_permisos_detallados()
                })
            
            return Response({
                'message': 'Esta es una vista protegida',
                'user': user_data
            })
        except Exception as e:
            return Response({
                'error': f'Error obteniendo datos del usuario: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            
            return Response({
                'access': access_token
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': 'Token de refresh inválido'},
                status=status.HTTP_401_UNAUTHORIZED
            )
