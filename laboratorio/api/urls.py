from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from ..auth import views as auth_views
from ..integrations import csv_handler as csv_views

# Importar todas las vistas desde el archivo principal y módulos específicos
from .. import views
from ..view_modules.polinizacion_views import PolinizacionViewSet
from ..view_modules.germinacion_views import GerminacionViewSet
from ..view_modules.user_views import UserProfileViewSet, UserManagementViewSet, UserMetasViewSet
from ..view_modules.notification_views import NotificationViewSet
from ..view_modules.utils_views import (
    generar_reporte_germinaciones, generar_reporte_polinizaciones,
    estadisticas_germinaciones, estadisticas_polinizaciones,
    estadisticas_usuario, generar_reporte_con_estadisticas
)
from ..view_modules.prediccion_views import (
    prediccion_germinacion, prediccion_polinizacion, prediccion_completa,
    predicciones_alertas, cambiar_estado_polinizacion, estadisticas_modelos,
    especies_promedios_germinacion, prediccion_polinizacion_ml, model_info,
    prediccion_germinacion_ml, germinacion_model_info,
    germinaciones_validadas, exportar_reentrenamiento_germinacion,
)

# Configurar el router para los ViewSets
router = DefaultRouter()
router.register(r'generos', views.GeneroViewSet)
router.register(r'especies', views.EspecieViewSet)
router.register(r'ubicaciones', views.UbicacionViewSet)
router.register(r'polinizaciones', PolinizacionViewSet)
router.register(r'germinaciones', GerminacionViewSet)
router.register(r'notifications', NotificationViewSet)
router.register(r'seguimientos', views.SeguimientoGerminacionViewSet)
router.register(r'capsulas', views.CapsulaViewSet)
router.register(r'siembras', views.SiembraViewSet)
router.register(r'personal', views.PersonalUsuarioViewSet)
router.register(r'inventarios', views.InventarioViewSet)

# ViewSets para sistema RBAC
router.register(r'user-profiles', UserProfileViewSet)
router.register(r'user-management', UserManagementViewSet)
router.register(r'user-metas', UserMetasViewSet, basename='usermetas')

urlpatterns = [
    # Rutas de autenticación
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/register/', auth_views.RegisterView.as_view(), name='register'),
    path('api/login/', auth_views.LoginView.as_view(), name='login'),
    path('api/protected/', auth_views.ProtectedView.as_view(), name='protected'),
    path('api/health/', auth_views.HealthCheckView.as_view(), name='health'),
    
    # Rutas específicas (deben ir ANTES del router para evitar conflictos)
    path('api/polinizaciones/mis-polinizaciones/', PolinizacionViewSet.as_view({'get': 'mis_polinizaciones'}), name='mis_polinizaciones'),
    path('api/germinaciones/mis-germinaciones/', GerminacionViewSet.as_view({'get': 'mis_germinaciones'}), name='mis_germinaciones'),

    # Rutas para reportes (ANTES del router para evitar conflictos)
    path('api/polinizaciones/reporte/', generar_reporte_polinizaciones, name='reporte_polinizaciones'),
    path('api/germinaciones/reporte/', generar_reporte_germinaciones, name='reporte_germinaciones'),

    # Incluir las rutas del router
    path('api/', include(router.urls)),
    
    # Mantener las rutas antiguas para compatibilidad
    path('inventario/', views.add_inventario, name='add_inventario'),
    path('inventario/<int:id>/', views.update_inventario, name='update_inventario'),
    path('usuarios/', views.add_usuario, name='add_usuario'),
    path('capsula/', views.add_capsula, name='add_capsula'),
    path('siembra/', views.add_siembra, name='add_siembra'),
    path('api/estadisticas/germinaciones/', estadisticas_germinaciones, name='estadisticas_germinaciones'),
    path('api/estadisticas/polinizaciones/', estadisticas_polinizaciones, name='estadisticas_polinizaciones'),
    path('api/estadisticas/usuario/', estadisticas_usuario, name='estadisticas_usuario'),

    # Rutas para importación de CSV
    path('api/upload/polinizaciones/', csv_views.upload_csv_polinizaciones, name='upload_csv_polinizaciones'),
    path('api/upload/germinaciones/', csv_views.upload_csv_germinaciones, name='upload_csv_germinaciones'),
    path('api/csv-templates/', csv_views.get_csv_templates, name='get_csv_templates'),
    
    # Ruta para reportes con estadísticas dinámicas
    path('api/reportes/estadisticas/', generar_reporte_con_estadisticas, name='generar_reporte_con_estadisticas'),
    
    # Rutas para predicciones
    path('api/predicciones/germinacion/', prediccion_germinacion, name='prediccion_germinacion'),
    path('api/predicciones/polinizacion/', prediccion_polinizacion, name='prediccion_polinizacion'),
    path('api/predicciones/completa/', prediccion_completa, name='prediccion_completa'),
    path('api/predicciones/estadisticas/', estadisticas_modelos, name='estadisticas_modelos'),
    path('api/predicciones/especies-promedios/', especies_promedios_germinacion, name='especies_promedios_germinacion'),
    
    # Rutas para predicciones de polinización con modelo .bin (comentadas temporalmente)
    # path('api/predicciones/polinizacion/inicial/', views.prediccion_polinizacion_inicial, name='prediccion_polinizacion_inicial'),
    # path('api/predicciones/polinizacion/refinar/', views.prediccion_polinizacion_refinar, name='prediccion_polinizacion_refinar'),
    # path('api/predicciones/polinizacion/validar/', views.prediccion_polinizacion_validar, name='prediccion_polinizacion_validar'),
    # path('api/predicciones/polinizacion/historial/', views.prediccion_polinizacion_historial, name='prediccion_polinizacion_historial'),
    # path('api/predicciones/polinizacion/completa/', views.prediccion_polinizacion_completa, name='prediccion_polinizacion_completa'),
    
    # Rutas adicionales que podrían estar en el original
    path('api/predicciones/alertas/', predicciones_alertas, name='predicciones_alertas'),
    
    # Ruta para cambiar estado de polinizaciones desde alertas
    path('api/polinizaciones/<int:pk>/cambiar-estado/', cambiar_estado_polinizacion, name='cambiar_estado_polinizacion'),
    
    # Rutas para reportes PDF de usuario (usando funciones de vista directas para evitar problemas de content negotiation)
    path('api/polinizaciones/mis-polinizaciones-pdf/', PolinizacionViewSet.as_view({'get': 'mis_polinizaciones_pdf'}), name='mis_polinizaciones_pdf'),
    path('api/germinaciones/mis-germinaciones-pdf/', GerminacionViewSet.as_view({'get': 'mis_germinaciones_pdf'}), name='mis_germinaciones_pdf'),

    # =============================================================================
    # PREDICCIONES CON MACHINE LEARNING (XGBoost)
    # =============================================================================

    # Predicción de polinización con XGBoost
    path('api/predicciones/polinizacion/ml/', prediccion_polinizacion_ml, name='prediccion_polinizacion_ml'),

    # Información del modelo ML de polinización
    path('api/ml/model-info/', model_info, name='model_info'),

    # =============================================================================
    # PREDICCIONES DE GERMINACIÓN CON MACHINE LEARNING (Random Forest)
    # =============================================================================

    # Predicción de germinación con Random Forest
    path('api/predicciones/germinacion/ml/', prediccion_germinacion_ml, name='prediccion_germinacion_ml'),

    # Información del modelo ML de germinación
    path('api/ml/germinacion/model-info/', germinacion_model_info, name='germinacion_model_info'),

    # =============================================================================
    # GERMINACIONES VALIDADAS Y EXPORTACIÓN PARA REENTRENAMIENTO
    # =============================================================================
    path('api/predicciones/germinaciones/validadas/', germinaciones_validadas, name='germinaciones_validadas'),
    path('api/predicciones/exportar-reentrenamiento-germinacion/', exportar_reentrenamiento_germinacion, name='exportar_reentrenamiento_germinacion'),

]