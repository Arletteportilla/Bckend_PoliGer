"""
Vistas para Germinaciones usando servicios de negocio
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.db.models import Q
import logging

from ..models import Germinacion
from ..serializers import GerminacionSerializer
from ..api.serializers import GerminacionHistoricaSerializer
from ..services.germinacion_service import germinacion_service
from ..services.prediccion_service import prediccion_service
from ..permissions import CanViewGerminaciones, CanCreateGerminaciones, CanEditGerminaciones
from .base_views import BaseServiceViewSet, ErrorHandlerMixin, SearchMixin
from ..api.pagination import StandardResultsSetPagination
from ..api.filters import GerminacionFilter
from ..renderers import BinaryFileRenderer

logger = logging.getLogger(__name__)





class GerminacionViewSet(BaseServiceViewSet, ErrorHandlerMixin, SearchMixin):
    """
    ViewSet para Germinaciones usando servicios de negocio
    Incluye paginación, filtros y búsqueda
    """
    queryset = Germinacion.objects.all()
    serializer_class = GerminacionSerializer
    service_class = type(germinacion_service)
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = GerminacionFilter
    search_fields = ['codigo', 'especie_variedad', 'genero', 'responsable']
    ordering_fields = ['fecha_siembra', 'fecha_creacion', 'codigo', 'especie_variedad', 'estado_capsulas']
    ordering = ['-fecha_creacion']

    
    # Definir permisos por acción
    role_permissions = {
        'list': CanViewGerminaciones,
        'retrieve': CanViewGerminaciones,
        'create': CanCreateGerminaciones,
        'update': CanEditGerminaciones,
        'partial_update': CanEditGerminaciones,
        'destroy': CanEditGerminaciones,
        'mis_germinaciones': CanViewGerminaciones,
        'todas_admin': CanViewGerminaciones,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = germinacion_service
    
    def get_queryset(self):
        """Optimizar consulta con select_related y prefetch_related"""
        return Germinacion.objects.select_related(
            'creado_por', 'polinizacion'
        ).prefetch_related(
            'seguimientos', 'capsulas', 'siembras'
        ).order_by('-fecha_creacion')

    def list(self, request, *args, **kwargs):
        """
        Lista germinaciones con paginación y filtros.
        Admite filtros por: código, especie, estado, clima, responsable, fechas, etc.
        """
        try:
            user = request.user

            logger.info(f"Listando germinaciones para usuario: {user.username}")

            # Obtener el queryset base según el rol del usuario
            queryset = self.filter_queryset(self.get_queryset())

            # Filtrar por usuario si no es administrador
            if not (hasattr(user, 'profile') and user.profile.rol == 'TIPO_4'):
                queryset = queryset.filter(creado_por=user)
                logger.info(f"Usuario regular - filtrando solo sus germinaciones")
            else:
                logger.info(f"Usuario es administrador - mostrando todas las germinaciones")

            # Aplicar paginación
            page = self.paginate_queryset(queryset)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                logger.info(f"Retornando página con {len(serializer.data)} germinaciones")
                return self.get_paginated_response(serializer.data)

            # Si no hay paginación configurada, retornar todo
            serializer = self.get_serializer(queryset, many=True)
            logger.info(f"Retornando {len(serializer.data)} germinaciones sin paginación")
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error listando germinaciones: {e}")
            return self.handle_error(e, "Error obteniendo germinaciones")

    def perform_create(self, serializer):
        """Crear germinación usando el servicio"""
        try:
            logger.info(f"Creando germinación para usuario: {self.request.user}")

            germinacion = self.service.create(
                serializer.validated_data,
                user=self.request.user
            )

            # Crear notificación de nueva germinación
            try:
                from ..services.notification_service import notification_service
                notification_service.crear_notificacion_germinacion(
                    usuario=self.request.user,
                    germinacion=germinacion,
                    tipo='NUEVA_GERMINACION'
                )
                logger.info(f"Notificación creada para germinación {germinacion.id}")
            except Exception as e:
                logger.warning(f"No se pudo crear notificación: {e}")

            # NUEVO: Verificar si ya debe enviarse recordatorio de 5 días
            # (para casos donde la fecha ingresada ya tiene más de 5 días)
            try:
                from ..services.recordatorio_service import recordatorio_service
                enviado = recordatorio_service.verificar_y_notificar_germinacion(germinacion)
                if enviado:
                    logger.info(f"⚡ Recordatorio inmediato enviado para germinación {germinacion.id}")
            except Exception as e:
                logger.warning(f"Error verificando recordatorio inmediato: {e}")

            return germinacion

        except Exception as e:
            logger.error(f"Error creando germinación: {e}")
            raise
    
    def perform_update(self, serializer):
        """Actualizar germinación usando el servicio"""
        try:
            germinacion_anterior = self.get_object()
            estado_anterior = germinacion_anterior.estado_capsulas
            
            germinacion = self.service.update(
                germinacion_anterior.pk,
                serializer.validated_data,
                user=self.request.user
            )
            
            # Crear notificación si cambió el estado
            if germinacion.estado_capsulas != estado_anterior:
                try:
                    from ..services.notification_service import notification_service
                    notification_service.crear_notificacion_germinacion(
                        usuario=self.request.user,
                        germinacion=germinacion,
                        tipo='ESTADO_ACTUALIZADO'
                    )
                    logger.info(f"Notificación de cambio de estado creada para germinación {germinacion.id}")
                except Exception as e:
                    logger.warning(f"No se pudo crear notificación: {e}")
            
            return germinacion
        
        except Exception as e:
            logger.error(f"Error actualizando germinación: {e}")
            raise
    
    @action(detail=False, methods=['get'], url_path='mis-germinaciones')
    def mis_germinaciones(self, request):
        """Obtiene solo las germinaciones del usuario autenticado con soporte de paginación"""
        try:
            search = request.GET.get('search', '').strip()
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            dias_recientes = request.GET.get('dias_recientes', None)
            tipo_registro = request.GET.get('tipo_registro', '').strip()  # 'historicos' o 'nuevos'
            
            if dias_recientes:
                dias_recientes = int(dias_recientes)
            
            # Determinar si excluir importadas basado en tipo_registro
            if tipo_registro == 'historicos':
                excluir_importadas = False  # Mostrar SOLO registros históricos (importados)
                solo_historicos = True
            elif tipo_registro == 'nuevos':
                excluir_importadas = True   # Mostrar SOLO registros nuevos (no importados)
                solo_historicos = False
            else:
                excluir_importadas = request.GET.get('excluir_importadas', 'false').lower() == 'true'
                solo_historicos = False

            logger.info(f"🔍 ENDPOINT mis-germinaciones - Usuario autenticado: {request.user.username} (ID: {request.user.id})")
            logger.info(f"🔍 Parámetros recibidos: page={page}, page_size={page_size}, search='{search}', dias_recientes={dias_recientes}, tipo_registro={tipo_registro}")
            logger.info(f"🔍 Usuario autenticado: {request.user.is_authenticated}, Usuario staff: {request.user.is_staff}")

            # Si se solicita paginación, usar método paginado
            if request.GET.get('paginated', 'false').lower() == 'true' or page_size < 1000:
                logger.info(f"📋 Usando método paginado para usuario {request.user.username}")

                result = self.service.get_mis_germinaciones_paginated(
                    user=request.user,
                    page=page,
                    page_size=page_size,
                    search=search,
                    dias_recientes=dias_recientes,
                    excluir_importadas=excluir_importadas,
                    solo_historicos=solo_historicos if tipo_registro == 'historicos' else False
                )

                logger.info(f"📊 Resultado del servicio: {result['count']} germinaciones totales, página {result['current_page']}/{result['total_pages']}")

                # Usar serializer diferente según el tipo de registro
                if tipo_registro == 'historicos':
                    # Para registros históricos, usar serializer sin estados
                    serializer = GerminacionHistoricaSerializer(result['results'], many=True)
                    logger.info("📦 Usando GerminacionHistoricaSerializer (sin estados)")
                else:
                    # Para registros nuevos o todos, usar serializer completo
                    serializer = self.get_serializer(result['results'], many=True)
                    logger.info("🆕 Usando GerminacionSerializer completo (con estados)")

                logger.info(f"✅ Retornando {len(serializer.data)} germinaciones serializadas al frontend")

                return Response({
                    'results': serializer.data,
                    'count': result['count'],
                    'total_pages': result['total_pages'],
                    'current_page': result['current_page'],
                    'page_size': result['page_size'],
                    'has_next': result['has_next'],
                    'has_previous': result['has_previous'],
                    'next': result['next'],
                    'previous': result['previous']
                })
            else:
                # Sin paginación (compatibilidad hacia atrás)
                germinaciones = self.service.get_mis_germinaciones(
                    user=request.user,
                    search=search,
                    dias_recientes=dias_recientes
                )
                
                # Usar serializer diferente según el tipo de registro
                if tipo_registro == 'historicos':
                    # Para registros históricos, usar serializer sin estados
                    serializer = GerminacionHistoricaSerializer(germinaciones, many=True)
                    logger.info("📦 Usando GerminacionHistoricaSerializer (sin estados)")
                else:
                    # Para registros nuevos o todos, usar serializer completo
                    serializer = self.get_serializer(germinaciones, many=True)
                    logger.info("🆕 Usando GerminacionSerializer completo (con estados)")
                
                logger.info(f"Retornando {len(serializer.data)} germinaciones")
                return Response(serializer.data)
            
        except Exception as e:
            return self.handle_error(e, "Error obteniendo mis germinaciones")
    
    @action(detail=False, methods=['get'], url_path='todas-admin')
    def todas_admin(self, request):
        """Obtiene TODAS las germinaciones para administradores"""
        try:
            user = request.user
            
            # Verificar que sea administrador
            if not hasattr(user, 'profile') or user.profile.rol != 'TIPO_4':
                return Response(
                    {'error': 'Solo los administradores pueden acceder a todas las germinaciones'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            logger.info(f"Obteniendo todas las germinaciones para admin: {user.username}")
            
            germinaciones = self.service.get_all(user=user)
            serializer = self.get_serializer(germinaciones, many=True)
            
            return Response({
                'count': len(serializer.data),
                'results': serializer.data
            })
            
        except Exception as e:
            return self.handle_error(e, "Error obteniendo todas las germinaciones")
    
    @action(detail=False, methods=['get'], url_path='filtros-opciones')
    def filtros_opciones(self, request):
        """Obtiene opciones disponibles para filtros y estadísticas"""
        try:
            user = request.user

            # Obtener queryset base según rol
            if hasattr(user, 'profile') and user.profile.rol == 'TIPO_4':
                queryset = self.get_queryset()
            else:
                queryset = self.get_queryset().filter(creado_por=user)

            # Obtener valores únicos para filtros
            responsables = list(queryset.exclude(responsable__isnull=True).exclude(responsable='').values_list('responsable', flat=True).distinct())
            perchas = list(queryset.exclude(percha__isnull=True).exclude(percha='').values_list('percha', flat=True).distinct())
            niveles = list(queryset.exclude(nivel__isnull=True).exclude(nivel='').values_list('nivel', flat=True).distinct())
            generos = list(queryset.exclude(genero__isnull=True).exclude(genero='').values_list('genero', flat=True).distinct())

            # Estadísticas
            total = queryset.count()
            por_estado = {
                'CERRADA': queryset.filter(estado_capsulas='CERRADA').count(),
                'ABIERTA': queryset.filter(estado_capsulas='ABIERTA').count(),
                'SEMIABIERTA': queryset.filter(estado_capsulas='SEMIABIERTA').count(),
            }
            por_clima = {
                'I': queryset.filter(clima='I').count(),
                'IW': queryset.filter(clima='IW').count(),
                'IC': queryset.filter(clima='IC').count(),
                'W': queryset.filter(clima='W').count(),
                'C': queryset.filter(clima='C').count(),
            }

            return Response({
                'opciones': {
                    'responsables': sorted(responsables),
                    'perchas': sorted(perchas),
                    'niveles': sorted(niveles),
                    'generos': sorted(generos),
                    'estados': ['CERRADA', 'ABIERTA', 'SEMIABIERTA'],
                    'climas': ['I', 'IW', 'IC', 'W', 'C'],
                    'tipos_polinizacion': ['SELF', 'HIBRIDA', 'SIBLING']
                },
                'estadisticas': {
                    'total': total,
                    'por_estado': por_estado,
                    'por_clima': por_clima
                }
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo opciones de filtros")

    @action(detail=False, methods=['get'], url_path='codigos-unicos')
    def codigos_unicos(self, request):
        """Obtiene códigos únicos para autocompletado"""
        try:
            codigos = self.service.get_codigos_unicos()
            return Response({
                'codigos': codigos,
                'total': len(codigos)
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo códigos únicos")
    
    @action(detail=False, methods=['get'], url_path='codigos-con-especies')
    def codigos_con_especies(self, request):
        """Obtiene códigos con especies para autocompletado"""
        try:
            codigos_especies = self.service.get_codigos_con_especies()
            return Response({
                'codigos_especies': codigos_especies,
                'total': len(codigos_especies)
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo códigos con especies")

    @action(detail=False, methods=['get'], url_path='codigos-disponibles')
    def codigos_disponibles(self, request):
        """
        Obtiene códigos disponibles desde la tabla Polinizacion con su información
        Usado para autocompletar en formularios de polinización
        """
        try:
            from ..models import Polinizacion

            logger.info("Obteniendo códigos disponibles desde polinizaciones")

            # Obtener polinizaciones con código no vacío
            polinizaciones = Polinizacion.objects.exclude(
                codigo__isnull=True
            ).exclude(
                codigo__exact=''
            ).values(
                'codigo', 'genero', 'especie', 'nueva_clima'
            ).distinct().order_by('codigo')

            # Formatear respuesta
            codigos_disponibles = []
            for pol in polinizaciones:
                codigos_disponibles.append({
                    'codigo': pol['codigo'],
                    'genero': pol['genero'] or '',
                    'especie': pol['especie'] or '',
                    'clima': pol['nueva_clima'] or 'I'
                })

            logger.info(f"Se encontraron {len(codigos_disponibles)} códigos disponibles desde polinizaciones")

            return Response(codigos_disponibles)

        except Exception as e:
            logger.error(f"Error obteniendo códigos disponibles: {e}")
            return self.handle_error(e, "Error obteniendo códigos disponibles")

    @action(detail=False, methods=['get'], url_path='buscar-por-codigo')
    def buscar_por_codigo(self, request):
        """Busca una germinación por código"""
        try:
            codigo = request.GET.get('codigo', '').strip()
            if not codigo:
                return Response(
                    {'error': 'Código es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            resultado = self.service.get_germinacion_by_codigo(codigo)
            
            if resultado:
                return Response(resultado)
            else:
                return Response(
                    {'error': 'No se encontró germinación con ese código'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            return self.handle_error(e, "Error buscando por código")
    
    @action(detail=False, methods=['get'], url_path='buscar-por-especie')
    def buscar_por_especie(self, request):
        """Busca una germinación por especie/variedad para autocompletar código"""
        try:
            especie = request.GET.get('especie', '').strip()
            if not especie:
                return Response(
                    {'error': 'Especie es requerida'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            resultado = self.service.get_germinacion_by_especie(especie)
            
            if resultado:
                return Response(resultado)
            else:
                return Response(
                    {'error': 'No se encontró germinación con esa especie'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        except Exception as e:
            return self.handle_error(e, "Error buscando por especie")
    
    @action(detail=False, methods=['post'], url_path='calcular-prediccion')
    def calcular_prediccion(self, request):
        """Calcula predicción de germinación"""
        try:
            logger.info("Calculando predicción de germinación")
            
            resultado = prediccion_service.calcular_prediccion_germinacion(request.data)
            
            logger.info("Predicción calculada exitosamente")
            return Response(resultado)
            
        except Exception as e:
            return self.handle_error(e, "Error calculando predicción")
    
    @action(detail=False, methods=['post'], url_path='calcular-prediccion-mejorada')
    def calcular_prediccion_mejorada(self, request):
        """Calcula predicción mejorada usando modelo ML"""
        try:
            logger.info("Calculando predicción mejorada de germinación")

            # Validar datos requeridos
            required_fields = ['especie', 'genero', 'fecha_siembra', 'clima']
            for field in required_fields:
                if not request.data.get(field):
                    return Response(
                        {'error': f'El campo {field} es requerido'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # Log de datos recibidos para debuggear
            logger.info(f"Datos recibidos: especie={request.data.get('especie')}, genero={request.data.get('genero')}, fecha_siembra={request.data.get('fecha_siembra')}, clima={request.data.get('clima')}")

            # Obtener predicción del servicio (usa ML si está disponible)
            resultado = prediccion_service.calcular_prediccion_germinacion(request.data)

            # Log del resultado
            logger.info(f"Resultado del servicio: {resultado}")

            # Transformar respuesta al formato esperado por el frontend
            dias_estimados = resultado.get('dias_estimados', 30)
            fecha_estimada = resultado.get('fecha_estimada', '')
            confianza = resultado.get('confianza', 75.0)
            nivel_confianza = resultado.get('nivel_confianza', 'media')
            metodo = resultado.get('metodo', 'HEURISTIC')
            modelo_utilizado = resultado.get('modelo_utilizado', 'Heurístico')

            logger.info(f"Fecha estimada del servicio: {fecha_estimada}, Días estimados: {dias_estimados}")

            # Formatear fecha estimada
            try:
                from datetime import datetime
                if isinstance(fecha_estimada, str):
                    fecha_obj = datetime.strptime(fecha_estimada, '%Y-%m-%d')
                    fecha_estimada_formatted = fecha_obj.strftime('%d/%m/%Y')
                else:
                    fecha_estimada_formatted = fecha_estimada.strftime('%d/%m/%Y')
            except:
                fecha_estimada_formatted = str(fecha_estimada)

            # Determinar estado y mensaje
            if metodo == 'ML':
                estado = 'excelente' if confianza >= 80 else 'bueno' if confianza >= 60 else 'aceptable'
                mensaje_estado = f"Predicción generada usando modelo de Machine Learning: {modelo_utilizado}"
            else:
                estado = 'aceptable'
                mensaje_estado = "Predicción generada usando método heurístico basado en datos históricos"

            # Generar recomendaciones
            recomendaciones = self._generar_recomendaciones(
                dias_estimados,
                request.data.get('clima', 'I'),
                confianza
            )

            # Determinar rango de confianza
            rango_confianza = self._obtener_rango_confianza(confianza, nivel_confianza)

            # Estructura de respuesta esperada por el frontend
            respuesta_estructurada = {
                'prediccion': {
                    'dias_estimados': dias_estimados,
                    'fecha_estimada': fecha_estimada,  # Formato ISO para guardar en BD
                    'fecha_estimada_formatted': fecha_estimada_formatted,  # Formato para mostrar
                    'confianza': confianza,
                    'nivel_confianza': nivel_confianza,
                    'modelo_usado': metodo,
                    'estado': estado,
                    'mensaje_estado': mensaje_estado
                },
                'parametros_usados': {
                    'especie': request.data.get('especie', ''),
                    'genero': request.data.get('genero', ''),
                    'clima': request.data.get('clima', ''),
                    'fecha_siembra': request.data.get('fecha_siembra', '')
                },
                'recomendaciones': recomendaciones,
                'rango_confianza': rango_confianza
            }

            logger.info(f"Predicción mejorada calculada exitosamente: {dias_estimados} días, confianza {confianza:.1f}%")
            return Response(respuesta_estructurada)

        except Exception as e:
            logger.error(f"Error calculando predicción mejorada: {e}")
            return self.handle_error(e, "Error calculando predicción mejorada")

    def _generar_recomendaciones(self, dias_estimados, clima, confianza):
        """Genera recomendaciones basadas en la predicción"""
        recomendaciones = []

        # Recomendaciones por tiempo estimado
        if dias_estimados < 30:
            recomendaciones.append("Tiempo de germinación corto. Monitorear frecuentemente.")
        elif dias_estimados > 90:
            recomendaciones.append("Tiempo de germinación prolongado. Mantener condiciones estables.")
        else:
            recomendaciones.append("Tiempo de germinación normal. Seguir protocolo estándar.")

        # Recomendaciones por clima
        clima_recomendaciones = {
            'C': "Clima cálido: Mantener humedad alta, evitar sobrecalentamiento.",
            'W': "Clima frío: Proporcionar calor suplementario si es necesario.",
            'I': "Clima intermedio: Condiciones óptimas, mantener estabilidad.",
            'IC': "Clima intermedio-frío: Monitorear temperatura regularmente.",
            'IW': "Clima intermedio-cálido: Asegurar ventilación adecuada.",
            'Warm': "Clima cálido: Mantener humedad alta, evitar sobrecalentamiento.",
            'Cool': "Clima frío: Proporcionar calor suplementario si es necesario.",
            'Intermedio': "Clima intermedio: Condiciones óptimas, mantener estabilidad."
        }
        if clima in clima_recomendaciones:
            recomendaciones.append(clima_recomendaciones[clima])

        # Recomendaciones por confianza
        if confianza < 60:
            recomendaciones.append("Confianza baja: Considerar datos adicionales para mejorar predicción.")
        elif confianza >= 80:
            recomendaciones.append("Alta confianza: Predicción basada en datos sólidos.")

        return recomendaciones

    def _obtener_rango_confianza(self, confianza, nivel_confianza):
        """Obtiene descripción del rango de confianza"""
        if nivel_confianza == 'alta' or confianza >= 80:
            return {
                'descripcion': 'Alta confianza en la predicción',
                'color': '#10b981',  # verde
                'precision_esperada': '±3-5 días'
            }
        elif nivel_confianza == 'media' or confianza >= 60:
            return {
                'descripcion': 'Confianza media en la predicción',
                'color': '#f59e0b',  # naranja
                'precision_esperada': '±5-10 días'
            }
        else:
            return {
                'descripcion': 'Confianza baja en la predicción',
                'color': '#ef4444',  # rojo
                'precision_esperada': '±10-15 días'
            }
    
    @action(detail=False, methods=['get'], url_path='germinaciones-pdf', renderer_classes=[BinaryFileRenderer])
    def germinaciones_pdf(self, request):
        """Genera PDF de TODAS las germinaciones del sistema"""
        try:
            search = request.GET.get('search', '').strip()

            # Obtener todas las germinaciones del sistema
            queryset = Germinacion.objects.select_related(
                'polinizacion', 'creado_por'
            ).prefetch_related(
                'seguimientos', 'capsulas', 'siembras'
            ).order_by('-fecha_creacion')

            # Aplicar búsqueda si existe
            if search:
                queryset = queryset.filter(
                    Q(codigo__icontains=search) |
                    Q(genero__icontains=search) |
                    Q(especie_variedad__icontains=search) |
                    Q(responsable__icontains=search)
                )

            germinaciones = list(queryset)

            # Generar PDF directamente usando HttpResponse
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER
            import io
            import os
            from datetime import datetime
            from django.conf import settings

            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f"_busqueda_{search}" if search else ""
            filename = f"germinaciones_todas_{datetime.now().strftime('%Y%m%d')}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'

            # Crear PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

            # Contenedor de elementos
            elements = []
            styles = getSampleStyleSheet()

            # Agregar logo si existe
            # Buscar el logo en diferentes ubicaciones posibles
            logo_paths = [
                os.path.join(settings.BASE_DIR, '..', 'PoliGer', 'assets', 'images', 'Ecuagenera.png'),
                os.path.join(settings.BASE_DIR, 'PoliGer', 'assets', 'images', 'Ecuagenera.png'),
                '/app/PoliGer/assets/images/Ecuagenera.png',  # Ruta en producción
            ]

            logo_img = None
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    try:
                        logo_img = Image(logo_path, width=0.8*inch, height=0.8*inch)
                        logo_img.hAlign = 'RIGHT'
                        elements.append(logo_img)
                        elements.append(Spacer(1, 6))
                        break
                    except Exception as e:
                        logger.warning(f"No se pudo cargar el logo desde {logo_path}: {e}")

            # Estilo personalizado para el encabezado principal
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Estilo personalizado para el título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Estilo para subtítulos
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#475569'),
                spaceAfter=6,
                alignment=TA_CENTER
            )

            # Encabezado POLIGER ECUAGENERA
            header = Paragraph("<b>POLIGER ECUAGENERA</b>", header_style)
            elements.append(header)
            elements.append(Spacer(1, 6))

            # Título
            title = Paragraph(f"<b>Reporte de Todas las Germinaciones del Sistema</b>", title_style)
            elements.append(title)

            # Subtítulo
            user_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            subtitle = Paragraph(f"Generado por: {user_name}", subtitle_style)
            elements.append(subtitle)

            # Información adicional
            fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
            info_text = f"Fecha de generación: {fecha_generacion}"
            if search:
                info_text += f" | Búsqueda: {search}"
            info_text += f" | Total: {len(germinaciones)} registros"

            info = Paragraph(info_text, subtitle_style)
            elements.append(info)
            elements.append(Spacer(1, 20))

            # Calcular estadísticas de estado
            completadas = sum(1 for g in germinaciones if g.fecha_germinacion)
            pendientes = len(germinaciones) - completadas

            # Tabla de resumen de estados
            summary_data = [
                ['Estado', 'Cantidad'],
                ['Completadas (con fecha de germinación)', str(completadas)],
                ['Pendientes (sin fecha de germinación)', str(pendientes)],
                ['TOTAL', str(len(germinaciones))]
            ]

            summary_table = Table(summary_data, colWidths=[4*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Filas de datos (Completadas)
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d1fae5')),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, 1), 10),
                ('ALIGN', (0, 1), (0, 1), 'LEFT'),
                ('ALIGN', (1, 1), (1, 1), 'CENTER'),

                # Filas de datos (Pendientes)
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fef3c7')),
                ('TEXTCOLOR', (0, 2), (-1, 2), colors.black),
                ('FONTNAME', (0, 2), (-1, 2), 'Helvetica'),
                ('FONTSIZE', (0, 2), (-1, 2), 10),
                ('ALIGN', (0, 2), (0, 2), 'LEFT'),
                ('ALIGN', (1, 2), (1, 2), 'CENTER'),

                # Fila TOTAL
                ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e5e7eb')),
                ('TEXTCOLOR', (0, 3), (-1, 3), colors.black),
                ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 3), (-1, 3), 11),
                ('ALIGN', (0, 3), (-1, 3), 'CENTER'),

                # Bordes y padding
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))

            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # Crear tabla de datos
            data = [['Código', 'Género', 'Especie/Variedad', 'Fecha\nSiembra', 'Cant.\nSolic.', 'Cápsulas', 'Estado', 'Clima', 'Responsable']]

            for germ in germinaciones:
                data.append([
                    str(germ.codigo or '')[:15],
                    str(germ.genero or '')[:10],
                    str(germ.especie_variedad or '')[:20],
                    germ.fecha_siembra.strftime('%d/%m/%Y') if germ.fecha_siembra else '',
                    str(germ.cantidad_solicitada or '0'),
                    str(germ.no_capsulas or '0'),
                    str(germ.estado_capsula or '')[:10],
                    str(germ.clima or '')[:4],
                    str(germ.responsable or '')[:15]
                ])

            # Crear tabla
            table = Table(data, colWidths=[0.9*inch, 0.7*inch, 1.3*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.8*inch, 0.5*inch, 1*inch])

            # Estilo de la tabla
            table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                ('ALIGN', (6, 1), (6, -1), 'CENTER'),
                ('ALIGN', (7, 1), (7, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))

            elements.append(table)

            # Pie de página
            elements.append(Spacer(1, 20))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
            footer = Paragraph(f"PoliGer - Sistema de Gestión de Laboratorio | Generado automáticamente", footer_style)
            elements.append(footer)

            # Generar PDF
            doc.build(elements)

            # Escribir el buffer al response
            pdf = buffer.getvalue()
            buffer.close()
            response.write(pdf)

            return response

        except Exception as e:
            logger.error(f"Error generando PDF de germinaciones: {e}")
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='mis-germinaciones-pdf', renderer_classes=[BinaryFileRenderer])
    def mis_germinaciones_pdf(self, request):
        """Genera PDF de las germinaciones del usuario"""
        try:
            search = request.GET.get('search', '').strip()

            # Obtener germinaciones del usuario (sin filtro de días para PDF completo)
            # EXCLUIR las germinaciones importadas desde Excel/CSV
            germinaciones = self.service.get_mis_germinaciones(
                user=request.user,
                search=search,
                dias_recientes=0,  # 0 = todos los registros
                excluir_importadas=True  # Excluir importaciones desde archivos
            )

            # Generar PDF directamente usando HttpResponse
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER
            import io
            import os
            from datetime import datetime
            from django.conf import settings

            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f"_busqueda_{search}" if search else ""
            filename = f"germinaciones_{request.user.username}_{datetime.now().strftime('%Y%m%d')}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'

            # Crear PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)

            # Contenedor de elementos
            elements = []
            styles = getSampleStyleSheet()

            # Agregar logo si existe
            # Buscar el logo en diferentes ubicaciones posibles
            logo_paths = [
                os.path.join(settings.BASE_DIR, '..', 'PoliGer', 'assets', 'images', 'Ecuagenera.png'),
                os.path.join(settings.BASE_DIR, 'PoliGer', 'assets', 'images', 'Ecuagenera.png'),
                '/app/PoliGer/assets/images/Ecuagenera.png',  # Ruta en producción
            ]

            logo_img = None
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    try:
                        logo_img = Image(logo_path, width=0.8*inch, height=0.8*inch)
                        logo_img.hAlign = 'RIGHT'
                        elements.append(logo_img)
                        elements.append(Spacer(1, 6))
                        break
                    except Exception as e:
                        logger.warning(f"No se pudo cargar el logo desde {logo_path}: {e}")

            # Estilo personalizado para el encabezado principal
            header_style = ParagraphStyle(
                'CustomHeader',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=6,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Estilo personalizado para el título
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=12,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )

            # Estilo para subtítulos
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=11,
                textColor=colors.HexColor('#475569'),
                spaceAfter=6,
                alignment=TA_CENTER
            )

            # Encabezado poliger ecuagenera
            header = Paragraph("<b>POLIGER ECUAGENERA</b>", header_style)
            elements.append(header)
            elements.append(Spacer(1, 6))

            # Título
            user_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            title = Paragraph(f"<b>Reporte de Germinaciones</b>", title_style)
            elements.append(title)

            # Subtítulo con información del usuario
            subtitle = Paragraph(f"Usuario: {user_name} ({request.user.username})", subtitle_style)
            elements.append(subtitle)

            # Información adicional
            fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
            info_text = f"Fecha de generación: {fecha_generacion}"
            if search:
                info_text += f" | Búsqueda: {search}"
            info_text += f" | Total: {len(germinaciones)} registros"

            info = Paragraph(info_text, subtitle_style)
            elements.append(info)
            elements.append(Spacer(1, 20))

            # Calcular estadísticas de estado
            completadas = sum(1 for g in germinaciones if g.fecha_germinacion)
            pendientes = len(germinaciones) - completadas

            # Tabla de resumen de estados
            summary_data = [
                ['Estado', 'Cantidad'],
                ['Completadas (con fecha de germinación)', str(completadas)],
                ['Pendientes (sin fecha de germinación)', str(pendientes)],
                ['TOTAL', str(len(germinaciones))]
            ]

            summary_table = Table(summary_data, colWidths=[4*inch, 1.5*inch])
            summary_table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Filas de datos (Completadas)
                ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#d1fae5')),
                ('TEXTCOLOR', (0, 1), (-1, 1), colors.black),
                ('FONTNAME', (0, 1), (-1, 1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, 1), 10),
                ('ALIGN', (0, 1), (0, 1), 'LEFT'),
                ('ALIGN', (1, 1), (1, 1), 'CENTER'),

                # Filas de datos (Pendientes)
                ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#fef3c7')),
                ('TEXTCOLOR', (0, 2), (-1, 2), colors.black),
                ('FONTNAME', (0, 2), (-1, 2), 'Helvetica'),
                ('FONTSIZE', (0, 2), (-1, 2), 10),
                ('ALIGN', (0, 2), (0, 2), 'LEFT'),
                ('ALIGN', (1, 2), (1, 2), 'CENTER'),

                # Fila TOTAL
                ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e5e7eb')),
                ('TEXTCOLOR', (0, 3), (-1, 3), colors.black),
                ('FONTNAME', (0, 3), (-1, 3), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 3), (-1, 3), 11),
                ('ALIGN', (0, 3), (-1, 3), 'CENTER'),

                # Bordes y padding
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ]))

            elements.append(summary_table)
            elements.append(Spacer(1, 20))

            # Crear tabla de datos
            data = [['Código', 'Género', 'Especie/Variedad', 'Fecha\nSiembra', 'Cant.\nSolic.', 'Cápsulas', 'Estado', 'Clima', 'Responsable']]

            for germ in germinaciones:
                data.append([
                    str(germ.codigo or '')[:15],
                    str(germ.genero or '')[:10],
                    str(germ.especie_variedad or '')[:20],
                    germ.fecha_siembra.strftime('%d/%m/%Y') if germ.fecha_siembra else '',
                    str(germ.cantidad_solicitada or '0'),
                    str(germ.no_capsulas or '0'),
                    str(germ.estado_capsula or '')[:10],
                    str(germ.clima or '')[:4],
                    str(germ.responsable or '')[:15]
                ])

            # Crear tabla
            table = Table(data, colWidths=[0.9*inch, 0.7*inch, 1.3*inch, 0.8*inch, 0.6*inch, 0.6*inch, 0.8*inch, 0.5*inch, 1*inch])

            # Estilo de la tabla
            table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),

                # Datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),
                ('ALIGN', (5, 1), (5, -1), 'CENTER'),
                ('ALIGN', (6, 1), (6, -1), 'CENTER'),
                ('ALIGN', (7, 1), (7, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))

            elements.append(table)

            # Pie de página
            elements.append(Spacer(1, 20))
            footer_style = ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.grey,
                alignment=TA_CENTER
            )
            footer = Paragraph(f"PoliGer - Sistema de Gestión de Laboratorio | Generado automáticamente", footer_style)
            elements.append(footer)

            # Generar PDF
            doc.build(elements)

            # Obtener PDF del buffer
            pdf_data = buffer.getvalue()
            buffer.close()

            response.write(pdf_data)
            logger.info(f"PDF generado exitosamente para {request.user.username}: {len(germinaciones)} registros")
            return response

        except Exception as e:
            logger.error(f"Error generando PDF: {e}")
            import traceback
            logger.error(traceback.format_exc())
            response = HttpResponse(
                f'Error generando PDF: {str(e)}',
                status=500,
                content_type='text/plain'
            )
            return response
    
    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """Cambia el estado de germinación (INICIAL, EN_PROCESO, FINALIZADO) o actualiza el progreso"""
        try:
            germinacion = self.get_object()
            nuevo_estado = request.data.get('estado')
            progreso = request.data.get('progreso')
            fecha_germinacion_custom = request.data.get('fecha_germinacion')
            
            logger.info(f"Cambiando estado de germinación {pk}: estado={nuevo_estado}, progreso={progreso}, fecha={fecha_germinacion_custom}")
            
            estado_anterior = germinacion.estado_germinacion if hasattr(germinacion, 'estado_germinacion') else 'INICIAL'
            progreso_anterior = germinacion.progreso_germinacion if hasattr(germinacion, 'progreso_germinacion') else 0
            
            # Si se proporciona progreso, actualizar y calcular estado automáticamente
            if progreso is not None:
                try:
                    progreso = int(progreso)
                    if progreso < 0 or progreso > 100:
                        return Response(
                            {'error': 'El progreso debe estar entre 0 y 100'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    germinacion.progreso_germinacion = progreso
                    if hasattr(germinacion, 'actualizar_estado_por_progreso'):
                        germinacion.actualizar_estado_por_progreso()
                    else:
                        # Fallback si el método no existe
                        if progreso <= 10:
                            germinacion.estado_germinacion = 'INICIAL'
                        elif progreso <= 60:
                            germinacion.estado_germinacion = 'EN_PROCESO_TEMPRANO'
                        elif progreso <= 90:
                            germinacion.estado_germinacion = 'EN_PROCESO_AVANZADO'
                        else:
                            germinacion.estado_germinacion = 'FINALIZADO'
                    
                except ValueError:
                    return Response(
                        {'error': 'El progreso debe ser un número entero'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Si se proporciona estado explícitamente, validar y actualizar
            elif nuevo_estado:
                estados_validos = ['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO', 'FINALIZADO']
                if nuevo_estado not in estados_validos:
                    return Response(
                        {'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                germinacion.estado_germinacion = nuevo_estado
                
                # Actualizar progreso según el estado
                if nuevo_estado == 'INICIAL':
                    germinacion.progreso_germinacion = 10
                elif nuevo_estado == 'EN_PROCESO_TEMPRANO':
                    germinacion.progreso_germinacion = 35
                elif nuevo_estado == 'EN_PROCESO_AVANZADO':
                    germinacion.progreso_germinacion = 75
                elif nuevo_estado == 'FINALIZADO':
                    germinacion.progreso_germinacion = 100
                    # Registrar fecha de germinación (personalizada o actual)
                    if fecha_germinacion_custom:
                        from datetime import datetime
                        try:
                            germinacion.fecha_germinacion = datetime.strptime(fecha_germinacion_custom, '%Y-%m-%d').date()
                        except ValueError:
                            return Response(
                                {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                                status=status.HTTP_400_BAD_REQUEST
                            )
                    elif not germinacion.fecha_germinacion:
                        from django.utils import timezone
                        germinacion.fecha_germinacion = timezone.now().date()
            
            else:
                return Response(
                    {'error': 'Debe proporcionar "estado" o "progreso"'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            germinacion.save()
            logger.info(f"Estado actualizado: {estado_anterior} → {germinacion.estado_germinacion}, Progreso: {progreso_anterior}% → {germinacion.progreso_germinacion}%")
            
            # Crear notificación del cambio de estado
            try:
                from ..services.notification_service import notification_service
                notification_service.crear_notificacion_germinacion(
                    usuario=request.user,
                    germinacion=germinacion,
                    tipo='ESTADO_ACTUALIZADO'
                )
                logger.info(f"Notificación creada para germinación {germinacion.id}")
            except Exception as e:
                logger.warning(f"No se pudo crear notificación: {e}")
            
            serializer = self.get_serializer(germinacion)
            
            return Response({
                'message': f'Estado actualizado de {estado_anterior} a {germinacion.estado_germinacion} (Progreso: {germinacion.progreso_germinacion}%)',
                'germinacion': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error cambiando estado de germinación: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {'error': f'Error cambiando estado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='alertas_germinacion')
    def alertas_germinacion(self, request):
        """Obtener alertas de germinaciones próximas a vencer"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Obtener germinaciones del usuario
            germinaciones = self.get_queryset().filter(creado_por=request.user)
            
            # Filtrar germinaciones con predicción y que no hayan germinado
            alertas = []
            hoy = timezone.now().date()
            
            for germinacion in germinaciones:
                # Solo considerar germinaciones que no han germinado aún
                if not germinacion.fecha_germinacion:
                    # Si tiene predicción de fecha estimada
                    if germinacion.prediccion_fecha_estimada:
                        fecha_estimada = germinacion.prediccion_fecha_estimada
                        dias_restantes = (fecha_estimada - hoy).days
                        
                        # Alertas para germinaciones próximas (dentro de 7 días) o vencidas
                        if dias_restantes <= 7:
                            tipo_alerta = 'vencida' if dias_restantes < 0 else 'proxima'
                            alertas.append({
                                'id': germinacion.id,
                                'codigo': germinacion.codigo,
                                'especie': germinacion.especie_variedad,
                                'genero': germinacion.genero,
                                'fecha_siembra': germinacion.fecha_siembra,
                                'fecha_estimada': fecha_estimada,
                                'dias_restantes': dias_restantes,
                                'tipo_alerta': tipo_alerta,
                                'mensaje': f"Germinación {'vencida' if dias_restantes < 0 else 'próxima a germinar'}"
                            })
            
            return Response({
                'alertas': alertas,
                'total': len(alertas)
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo alertas de germinación: {e}")
            return Response(
                {'error': f'Error al obtener alertas: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'], url_path='marcar-revisado')
    def marcar_revisado(self, request, pk=None):
        """Marca una germinación como revisada y programa la próxima revisión"""
        try:
            germinacion = self.get_object()
            
            # Obtener datos del request
            nuevo_estado = request.data.get('estado')
            progreso = request.data.get('progreso')
            dias_proxima_revision = request.data.get('dias_proxima_revision', 10)  # Por defecto 10 días
            
            from django.utils import timezone
            from datetime import timedelta
            
            # Actualizar fecha de última revisión
            germinacion.fecha_ultima_revision = timezone.now().date()
            
            # Actualizar estado si se proporciona
            if nuevo_estado:
                estados_validos = ['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO', 'FINALIZADO']
                if nuevo_estado in estados_validos:
                    germinacion.estado_germinacion = nuevo_estado
                    
                    # Actualizar progreso según el estado
                    if nuevo_estado == 'INICIAL':
                        germinacion.progreso_germinacion = 10
                    elif nuevo_estado == 'EN_PROCESO_TEMPRANO':
                        germinacion.progreso_germinacion = 35
                    elif nuevo_estado == 'EN_PROCESO_AVANZADO':
                        germinacion.progreso_germinacion = 75
                    elif nuevo_estado == 'FINALIZADO':
                        germinacion.progreso_germinacion = 100
                        if not germinacion.fecha_germinacion:
                            germinacion.fecha_germinacion = timezone.now().date()
            
            # Actualizar progreso si se proporciona explícitamente
            if progreso is not None:
                try:
                    progreso = int(progreso)
                    if 0 <= progreso <= 100:
                        germinacion.progreso_germinacion = progreso
                        germinacion.actualizar_estado_por_progreso()
                except ValueError:
                    pass
            
            # Programar próxima revisión solo si no está finalizada
            if germinacion.estado_germinacion != 'FINALIZADO':
                germinacion.fecha_proxima_revision = timezone.now().date() + timedelta(days=dias_proxima_revision)
                germinacion.alerta_revision_enviada = False
            else:
                # Si está finalizada, no programar más revisiones
                germinacion.fecha_proxima_revision = None
                germinacion.alerta_revision_enviada = True
            
            germinacion.save()
            
            # Serializar y retornar
            serializer = self.get_serializer(germinacion)
            
            return Response({
                'message': 'Germinación marcada como revisada exitosamente',
                'germinacion': serializer.data,
                'proxima_revision': germinacion.fecha_proxima_revision.isoformat() if germinacion.fecha_proxima_revision else None
            })
            
        except Exception as e:
            logger.error(f"Error marcando germinación como revisada: {e}")
            return Response(
                {'error': f'Error al marcar como revisada: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='pendientes-revision')
    def pendientes_revision(self, request):
        """Obtiene germinaciones pendientes de revisión para el usuario actual"""
        try:
            from django.utils import timezone
            hoy = timezone.now().date()
            
            # Filtrar por usuario
            queryset = self.get_queryset().filter(creado_por=request.user)
            
            # Buscar pendientes de revisión
            pendientes = queryset.filter(
                fecha_proxima_revision__lte=hoy,
                estado_germinacion__in=['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO']
            ).order_by('fecha_proxima_revision')
            
            serializer = self.get_serializer(pendientes, many=True)
            
            return Response({
                'count': len(serializer.data),
                'results': serializer.data
            })
            
        except Exception as e:
            return self.handle_error(e, "Error obteniendo germinaciones pendientes de revisión")