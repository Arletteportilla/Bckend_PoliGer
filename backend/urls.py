from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('laboratorio.urls')),

    # ─── Documentación API ───────────────────────────────────────────────────
    # Esquema OpenAPI en formato JSON/YAML (descargable)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI interactivo  →  http://localhost:8000/api/docs/
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    # ReDoc (alternativa más limpia)  →  http://localhost:8000/api/redoc/
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]