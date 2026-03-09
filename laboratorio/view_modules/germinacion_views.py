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
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import csv
import io
import os
import logging

from ..models import Germinacion, Polinizacion
from ..serializers import GerminacionSerializer
from ..api.serializers import GerminacionHistoricaSerializer
from ..services.germinacion_service import germinacion_service
from ..services.prediccion_service import prediccion_service
from ..permissions import CanViewGerminaciones, CanCreateGerminaciones, CanEditGerminaciones, RoleBasedViewSetMixin
from .base_views import BaseServiceViewSet, ErrorHandlerMixin, SearchMixin
from ..api.pagination import StandardResultsSetPagination
from ..api.filters import GerminacionFilter
from ..renderers import BinaryFileRenderer
from ..core.models import UserProfile

logger = logging.getLogger(__name__)





class GerminacionViewSet(RoleBasedViewSetMixin, BaseServiceViewSet, ErrorHandlerMixin, SearchMixin):
    """
    ViewSet para Germinaciones usando servicios de negocio
    Incluye paginación, filtros y búsqueda
    """
    queryset = Germinacion.objects.all()
    serializer_class = GerminacionSerializer
    service_class = type(germinacion_service)
    # NO definir permission_classes aquí - dejar que RoleBasedViewSetMixin lo maneje
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
        'metricas_nuevos': CanViewGerminaciones,
        'filtros_opciones': CanViewGerminaciones,
        'codigos_unicos': CanViewGerminaciones,
        'codigos_con_especies': CanViewGerminaciones,
        'codigos_disponibles': CanViewGerminaciones,
        'buscar_por_codigo': CanViewGerminaciones,
        'buscar_por_especie': CanViewGerminaciones,
        'calcular_prediccion': CanViewGerminaciones,
        'calcular_prediccion_mejorada': CanViewGerminaciones,
        'germinaciones_pdf': CanViewGerminaciones,
        'mis_germinaciones_pdf': CanViewGerminaciones,
        'cambiar_estado': CanEditGerminaciones,
        'alertas_germinacion': CanViewGerminaciones,
        'marcar_revisado': CanEditGerminaciones,
        'pendientes_revision': CanViewGerminaciones,
        'marcar_alerta_revisada': CanEditGerminaciones,
        'estadisticas_precision_modelo': CanViewGerminaciones,
        'exportar_predicciones_csv': CanViewGerminaciones,
        'crear_backup_modelo': CanEditGerminaciones,
        'info_backup_modelo': CanViewGerminaciones,
        'reentrenar_modelo': CanEditGerminaciones,
        'completar_predicciones_faltantes': CanEditGerminaciones,
        'estado_modelo': CanViewGerminaciones,
        'performance_metrics': CanViewGerminaciones,
        'validar_prediccion': CanEditGerminaciones,
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
        Lista TODAS las germinaciones del sistema con paginación y filtros.
        Cualquier usuario con permiso CanViewGerminaciones puede ver todas las germinaciones.
        Admite filtros por: código, especie, estado, clima, responsable, fechas, etc.
        """
        try:
            user = request.user

            logger.info(f"Listando TODAS las germinaciones para usuario: {user.username}")

            # Obtener el queryset base - SIN filtrar por usuario
            # Todos los usuarios con permiso CanViewGerminaciones pueden ver todas las germinaciones
            queryset = self.filter_queryset(self.get_queryset())

            logger.info(f"Mostrando todas las germinaciones del sistema (usuario tiene permiso CanViewGerminaciones)")

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

            # Nota: la notificacion NUEVA_GERMINACION la genera el signal post_save en signals.py

            # Calcular y guardar predicción automáticamente al crear
            try:
                prediccion_data = {
                    'especie': germinacion.especie_variedad or '',
                    'genero': germinacion.genero or '',
                    'clima': germinacion.clima or 'I',
                    'fecha_siembra': str(germinacion.fecha_siembra) if germinacion.fecha_siembra else None,
                }
                resultado = prediccion_service.calcular_prediccion_germinacion(prediccion_data)
                if resultado and resultado.get('fecha_estimada'):
                    from datetime import date
                    fecha_est = resultado['fecha_estimada']
                    if isinstance(fecha_est, str):
                        from datetime import datetime
                        fecha_est = datetime.strptime(fecha_est, '%Y-%m-%d').date()
                    germinacion.prediccion_fecha_estimada = fecha_est
                    if resultado.get('dias_estimados'):
                        germinacion.prediccion_dias_estimados = resultado['dias_estimados']
                    if resultado.get('confianza'):
                        germinacion.prediccion_confianza = resultado['confianza']
                    germinacion.save(update_fields=[
                        'prediccion_fecha_estimada',
                        'prediccion_dias_estimados',
                        'prediccion_confianza',
                    ])
                    logger.info(f"Predicción guardada para germinación {germinacion.id}: {fecha_est}")
            except Exception as e:
                logger.warning(f"No se pudo calcular predicción automática para germinación {germinacion.id}: {e}")

            # NUEVO: Verificar si ya debe enviarse recordatorio de 5 días
            # (para casos donde la fecha ingresada ya tiene más de 5 días)
            try:
                from ..services.recordatorio_service import recordatorio_service
                enviado = recordatorio_service.verificar_y_notificar_germinacion(germinacion)
                if enviado:
                    logger.info(f"Recordatorio inmediato enviado para germinacion {germinacion.id}")
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

            logger.info(f"ENDPOINT mis-germinaciones - Usuario autenticado: {request.user.username} (ID: {request.user.id})")
            logger.info(f"Parametros recibidos: page={page}, page_size={page_size}, search='{search}', dias_recientes={dias_recientes}, tipo_registro={tipo_registro}")
            logger.info(f"Usuario autenticado: {request.user.is_authenticated}, Usuario staff: {request.user.is_staff}")

            # Si se solicita paginación, usar método paginado
            if request.GET.get('paginated', 'false').lower() == 'true' or page_size < 1000:
                logger.info(f"Usando metodo paginado para usuario {request.user.username}")

                result = self.service.get_mis_germinaciones_paginated(
                    user=request.user,
                    page=page,
                    page_size=page_size,
                    search=search,
                    dias_recientes=dias_recientes,
                    excluir_importadas=excluir_importadas,
                    solo_historicos=solo_historicos if tipo_registro == 'historicos' else False
                )

                logger.info(f"Resultado del servicio: {result['count']} germinaciones totales, pagina {result['current_page']}/{result['total_pages']}")

                # Usar serializer diferente según el tipo de registro
                if tipo_registro == 'historicos':
                    # Para registros históricos, usar serializer sin estados
                    serializer = GerminacionHistoricaSerializer(result['results'], many=True)
                    logger.info("Usando GerminacionHistoricaSerializer (sin estados)")
                else:
                    # Para registros nuevos o todos, usar serializer completo
                    serializer = self.get_serializer(result['results'], many=True)
                    logger.info("Usando GerminacionSerializer completo (con estados)")

                logger.info(f"Retornando {len(serializer.data)} germinaciones serializadas al frontend")

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
                    logger.info("Usando GerminacionHistoricaSerializer (sin estados)")
                else:
                    # Para registros nuevos o todos, usar serializer completo
                    serializer = self.get_serializer(germinaciones, many=True)
                    logger.info("Usando GerminacionSerializer completo (con estados)")
                
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
            if not hasattr(user, 'profile') or user.profile.rol != UserProfile.Roles.SYSTEM_MANAGER:
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
    
    @action(detail=False, methods=['get'], url_path='metricas-nuevos')
    def metricas_nuevos(self, request):
        """Obtiene métricas solo de registros creados en el sistema (no importados)"""
        try:

            queryset = Germinacion.objects.filter(
                Q(archivo_origen__isnull=True) | Q(archivo_origen='')
            )

            stats = queryset.aggregate(
                total=Count('id'),
                en_proceso=Count('id', filter=Q(
                    Q(estado_germinacion='EN_PROCESO') |
                    Q(estado_germinacion='EN_PROCESO_TEMPRANO') |
                    Q(estado_germinacion='EN_PROCESO_AVANZADO')
                )),
                finalizados=Count('id', filter=Q(
                    Q(estado_germinacion='FINALIZADO') |
                    Q(etapa_actual='LISTA')
                )),
            )

            total = stats['total'] or 0
            finalizados = stats['finalizados'] or 0
            exito_promedio = round((finalizados / total) * 100) if total > 0 else 0

            return Response({
                'en_proceso': stats['en_proceso'] or 0,
                'finalizados': finalizados,
                'exito_promedio': exito_promedio,
                'total': total,
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo métricas de germinaciones")

    @action(detail=False, methods=['get'], url_path='filtros-opciones')
    def filtros_opciones(self, request):
        """Obtiene opciones disponibles para filtros y estadísticas de TODAS las germinaciones"""
        try:

            user = request.user

            # Usar Germinacion.objects directamente en lugar de get_queryset() para evitar select_related innecesarios
            queryset = Germinacion.objects.all()
            logger.info(f"Obteniendo opciones de filtros para todas las germinaciones del sistema")

            # Obtener valores únicos para filtros usando only() para cargar solo campos necesarios
            responsables = list(queryset.exclude(responsable__isnull=True).exclude(responsable='').values_list('responsable', flat=True).distinct()[:100])
            perchas = list(queryset.exclude(percha__isnull=True).exclude(percha='').values_list('percha', flat=True).distinct()[:100])
            niveles = list(queryset.exclude(nivel__isnull=True).exclude(nivel='').values_list('nivel', flat=True).distinct()[:100])
            generos = list(queryset.exclude(genero__isnull=True).exclude(genero='').values_list('genero', flat=True).distinct()[:100])

            # Usar agregación para estadísticas en una sola query
            stats = queryset.aggregate(
                total=Count('id'),
                cerrada=Count('id', filter=Q(estado_capsulas='CERRADA')),
                abierta=Count('id', filter=Q(estado_capsulas='ABIERTA')),
                semiabierta=Count('id', filter=Q(estado_capsulas='SEMIABIERTA')),
                clima_i=Count('id', filter=Q(clima='I')),
                clima_iw=Count('id', filter=Q(clima='IW')),
                clima_ic=Count('id', filter=Q(clima='IC')),
                clima_w=Count('id', filter=Q(clima='W')),
                clima_c=Count('id', filter=Q(clima='C')),
            )

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
                    'total': stats['total'],
                    'por_estado': {
                        'CERRADA': stats['cerrada'],
                        'ABIERTA': stats['abierta'],
                        'SEMIABIERTA': stats['semiabierta'],
                    },
                    'por_clima': {
                        'I': stats['clima_i'],
                        'IW': stats['clima_iw'],
                        'IC': stats['clima_ic'],
                        'W': stats['clima_w'],
                        'C': stats['clima_c'],
                    }
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
        Limitado a 500 resultados más recientes para performance
        """
        try:

            # Parámetro de búsqueda opcional para filtrar
            search = request.GET.get('search', '').strip()

            logger.info(f"Obteniendo códigos disponibles desde polinizaciones (búsqueda: '{search}')")

            # Construir query base con índices
            queryset = Polinizacion.objects.exclude(
                codigo__isnull=True
            ).exclude(
                codigo__exact=''
            )

            # Si hay búsqueda, filtrar
            if search:
                queryset = queryset.filter(codigo__icontains=search)

            # Limitar a 500 resultados más recientes usando only() para cargar menos campos
            # IMPORTANTE: distinct() debe ir ANTES del slice [:500]
            polinizaciones = queryset.values(
                'codigo', 'genero', 'especie', 'nueva_clima'
            ).distinct().order_by('-codigo')[:500]

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
    
    @action(detail=False, methods=['post'], url_path='calcular_prediccion')
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
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from datetime import datetime

            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f"_busqueda_{search}" if search else ""
            filename = f"germinaciones_{request.user.username}_{datetime.now().strftime('%Y%m%d')}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'

            # Función para cabecera/pie de página
            def add_page_footer(canvas, doc):
                canvas.saveState()
                page_width, page_height = letter
                # Franja azul superior
                canvas.setFillColor(colors.HexColor('#1e3a8a'))
                canvas.rect(0, page_height - 4, page_width, 4, fill=1, stroke=0)
                # Pie de página
                footer_text = "PoliGer \u2014 Sistema de Gestión de Laboratorio | Generado automáticamente"
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.HexColor('#1e3a8a'))
                canvas.drawCentredString(page_width / 2, 0.4 * inch, footer_text)
                canvas.setFont('Helvetica-Bold', 8)
                canvas.drawRightString(page_width - inch, 0.4 * inch, f"Pág. {doc.page}")
                canvas.restoreState()

            # Crear PDF
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.75*inch)

            # Contenedor de elementos
            elements = []
            styles = getSampleStyleSheet()

            # ─── ENCABEZADO ──────────────────────────────────────────────────────────
            MESES_ES = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                        7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
            now = datetime.now()
            fecha_larga = f"{now.day} de {MESES_ES[now.month]}, {now.year}"
            report_id = f"GER-{now.strftime('%Y%m%d%H%M%S')}"

            fechas_ger = [g.fecha_siembra for g in germinaciones if g.fecha_siembra]
            if fechas_ger:
                rango_datos = f"{min(fechas_ger).strftime('%d/%m/%Y')} \u2014 {max(fechas_ger).strftime('%d/%m/%Y')}"
            else:
                rango_datos = "Todos los registros"

            # Buscar logo
            logo_paths = [
                os.path.join(settings.BASE_DIR, '..', 'PoliGer', 'assets', 'images', 'Ecuagenera.png'),
                os.path.join(settings.BASE_DIR, 'PoliGer', 'assets', 'images', 'Ecuagenera.png'),
                '/app/PoliGer/assets/images/Ecuagenera.png',
            ]
            logo_img = None
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    try:
                        logo_img = Image(logo_path, width=0.8*inch, height=0.8*inch)
                        break
                    except Exception as e:
                        logger.warning(f"No se pudo cargar el logo desde {logo_path}: {e}")

            # Estilos
            company_name_style = ParagraphStyle('CompanyName', fontName='Helvetica-Bold', fontSize=17,
                textColor=colors.HexColor('#0F172A'), leading=20)
            system_name_style = ParagraphStyle('SystemName', fontName='Helvetica-Bold', fontSize=8,
                textColor=colors.HexColor('#2563EB'), leading=11, spaceBefore=3)
            report_title_style_h = ParagraphStyle('ReportTitleH', fontName='Helvetica-Bold', fontSize=14,
                textColor=colors.HexColor('#0F172A'), alignment=TA_RIGHT, leading=18)
            report_sub_style_h = ParagraphStyle('ReportSubH', fontName='Helvetica', fontSize=10,
                textColor=colors.HexColor('#64748B'), alignment=TA_RIGHT, leading=13, spaceBefore=3)
            meta_label_style = ParagraphStyle('MetaLabel', fontName='Helvetica-Bold', fontSize=7,
                textColor=colors.HexColor('#64748B'), leading=9, spaceAfter=3)
            meta_value_style = ParagraphStyle('MetaValue', fontName='Helvetica-Bold', fontSize=12,
                textColor=colors.HexColor('#0F172A'), leading=15)

            page_w = letter[0]
            usable_w = page_w - 2 * inch  # márgenes 1" cada lado

            # Bloque izquierdo: logo + nombre empresa
            text_left = [Paragraph('ECUAGENERA', company_name_style), Paragraph('SISTEMA POLIGER', system_name_style)]
            if logo_img:
                inner_left = Table([[logo_img, text_left]], colWidths=[0.85*inch, usable_w * 0.5 - 0.85*inch])
                inner_left.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (0,0), 10),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))
            else:
                inner_left = Table([[text_left]], colWidths=[usable_w * 0.5])
                inner_left.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('TOPPADDING', (0,0), (-1,-1), 0),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                ]))

            # Bloque derecho: título reporte
            right_block = [
                Paragraph('Reporte Interno de Producción', report_title_style_h),
            ]

            header_main = Table([[inner_left, right_block]], colWidths=[usable_w * 0.55, usable_w * 0.45])
            header_main.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('LEFTPADDING', (0,0), (-1,-1), 0),
                ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ('TOPPADDING', (0,0), (-1,-1), 6),
                ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ]))
            elements.append(header_main)
            elements.append(Spacer(1, 8))
            elements.append(HRFlowable(width='100%', thickness=1, lineCap='square', color=colors.HexColor('#CBD5E1')))
            elements.append(Spacer(1, 10))

            # Franja de metadatos
            third_w = usable_w / 3
            meta_table = Table([[
                [Paragraph('ID DEL REPORTE', meta_label_style), Paragraph(report_id, meta_value_style)],
                [Paragraph('FECHA DE GENERACIÓN', meta_label_style), Paragraph(fecha_larga, meta_value_style)],
                [Paragraph('RANGO DE DATOS', meta_label_style), Paragraph(rango_datos, meta_value_style)],
            ]], colWidths=[third_w, third_w, third_w])
            meta_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EFF6FF')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 14),
                ('RIGHTPADDING', (0,0), (-1,-1), 14),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('LINEAFTER', (0,0), (1,-1), 1, colors.HexColor('#BFDBFE')),
            ]))
            elements.append(meta_table)
            elements.append(Spacer(1, 20))
            # ─── FIN ENCABEZADO ───────────────────────────────────────────────────────

            # ─── RESUMEN DE OPERACIÓN ────────────────────────────────────────────────
            completadas = sum(1 for g in germinaciones if g.fecha_germinacion)
            pendientes = len(germinaciones) - completadas
            total_registros_ger = len(germinaciones)

            elements.append(Paragraph('Resumen de Operación', ParagraphStyle('SecTitleG',
                fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#1e3a8a'), leading=16)))
            elements.append(Spacer(1, 10))

            card_w = usable_w / 3
            bar_inner_w = card_w - 28

            def _bar_ger(ratio, fill_hex, bg_hex, width):
                filled = max(width * ratio, 2)
                empty = width - filled
                if empty > 1:
                    b = Table([['', '']], colWidths=[filled, empty], rowHeights=[5])
                    b.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (0,0), colors.HexColor(fill_hex)),
                        ('BACKGROUND', (1,0), (1,0), colors.HexColor(bg_hex)),
                        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ]))
                else:
                    b = Table([['',]], colWidths=[width], rowHeights=[5])
                    b.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (0,0), colors.HexColor(fill_hex)),
                        ('TOPPADDING', (0,0), (-1,-1), 0), ('BOTTOMPADDING', (0,0), (-1,-1), 0),
                        ('LEFTPADDING', (0,0), (-1,-1), 0), ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ]))
                return b

            ratio_comp_g = completadas / total_registros_ger if total_registros_ger else 0
            ratio_pend_g = pendientes / total_registros_ger if total_registros_ger else 0

            gcard1 = [
                Paragraph('COMPLETADAS', ParagraphStyle('gc1l', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#1e3a8a'), leading=9)),
                Spacer(1, 4),
                Paragraph(str(completadas), ParagraphStyle('gc1n', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1e3a8a'), leading=15)),
                Spacer(1, 6),
                _bar_ger(ratio_comp_g, '#1e3a8a', '#BFDBFE', bar_inner_w),
            ]
            gcard2 = [
                Paragraph('PENDIENTES', ParagraphStyle('gc2l', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#b8860b'), leading=9)),
                Spacer(1, 4),
                Paragraph(str(pendientes), ParagraphStyle('gc2n', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#b8860b'), leading=15)),
                Spacer(1, 6),
                _bar_ger(ratio_pend_g, '#e9ad14', '#FDE68A', bar_inner_w),
            ]
            gcard3 = [
                Paragraph('TOTAL GERMINACIONES', ParagraphStyle('gc3l', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#1e3a8a'), leading=9)),
                Spacer(1, 4),
                Paragraph(f"{total_registros_ger:,}".replace(',', '.'), ParagraphStyle('gc3n', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#0F172A'), leading=15)),
            ]

            gcards_table = Table([[gcard1, gcard2, gcard3]], colWidths=[card_w, card_w, card_w])
            gcards_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#EFF6FF')),
                ('BACKGROUND', (1,0), (1,-1), colors.HexColor('#FFFBEB')),
                ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#F1F5F9')),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('LEFTPADDING', (0,0), (-1,-1), 12),
                ('RIGHTPADDING', (0,0), (-1,-1), 12),
                ('TOPPADDING', (0,0), (-1,-1), 10),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
                ('LINEAFTER', (0,0), (1,-1), 1, colors.white),
                ('BOX', (0,0), (0,-1), 1, colors.HexColor('#BFDBFE')),
                ('BOX', (1,0), (1,-1), 1, colors.HexColor('#FDE68A')),
                ('BOX', (2,0), (2,-1), 1, colors.HexColor('#CBD5E1')),
            ]))
            elements.append(gcards_table)
            elements.append(Spacer(1, 20))
            # ─── FIN RESUMEN ─────────────────────────────────────────────────────────

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

            # Crear tabla — anchos ajustados a letter usable_w (6.5")
            table = Table(data, colWidths=[
                usable_w * 0.138,  # Código
                usable_w * 0.100,  # Género
                usable_w * 0.185,  # Especie/Variedad
                usable_w * 0.108,  # Fecha Siembra
                usable_w * 0.077,  # Cant. Solic.
                usable_w * 0.077,  # Cápsulas
                usable_w * 0.108,  # Estado
                usable_w * 0.054,  # Clima
                usable_w * 0.153,  # Responsable
            ])

            # Estilo de la tabla
            table.setStyle(TableStyle([
                # Encabezado
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1e3a8a')),
                # Datos
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#0F172A')),
                ('ALIGN', (0, 1), (2, -1), 'LEFT'),
                ('ALIGN', (3, 1), (7, -1), 'CENTER'),
                ('ALIGN', (8, 1), (8, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EFF6FF')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
                ('RIGHTPADDING', (0, 0), (-1, -1), 4),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))

            elements.append(table)

            # Generar PDF con pie de página en cada página
            doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer)

            # Obtener PDF del buffer
            pdf_data = buffer.getvalue()
            buffer.close()

            response.write(pdf_data)
            logger.info(f"PDF generado exitosamente para {request.user.username}: {len(germinaciones)} registros")
            # Notificación de descarga de PDF
            try:
                from ..services.notification_service import notification_service
                notification_service.crear_notificacion_sistema(
                    usuario=request.user,
                    tipo='ACTUALIZACION',
                    titulo=f'Descarga de PDF - Germinaciones',
                    mensaje=f'Se descargó el PDF con {len(germinaciones)} registro(s) de germinaciones.',
                    detalles={'accion': 'descarga_pdf', 'tipo': 'germinaciones', 'total': len(germinaciones)}
                )
            except Exception as e:
                logger.warning(f"No se pudo crear notificacion de descarga PDF germinaciones: {e}")
            return response

        except Exception as e:
            logger.exception(f"Error generando PDF: {e}")
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

                # Sincronizar etapa_actual (campo legacy)
                if nuevo_estado == 'INICIAL':
                    germinacion.etapa_actual = 'INGRESADO'
                elif nuevo_estado in ('EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO'):
                    germinacion.etapa_actual = 'EN_PROCESO'
                elif nuevo_estado == 'FINALIZADO':
                    germinacion.etapa_actual = 'LISTA'

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
            return Response(
                {'error': f'Error cambiando estado: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='alertas_germinacion')
    def alertas_germinacion(self, request):
        """Obtener alertas de germinaciones próximas a vencer"""
        try:
            
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

    @action(detail=True, methods=['post'], url_path='marcar_alerta_revisada')
    def marcar_alerta_revisada(self, request, pk=None):
        """Marca una alerta de germinación como revisada"""
        try:
            germinacion = self.get_object()
            estado = request.data.get('estado')
            observaciones = request.data.get('observaciones', '')

            germinacion.alerta_revision_enviada = True

            if estado:
                estados_validos = ['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO', 'FINALIZADO']
                if estado in estados_validos:
                    germinacion.estado_germinacion = estado
                    germinacion.actualizar_estado_por_progreso()

            if observaciones:
                if germinacion.observaciones:
                    germinacion.observaciones += f"\n[Alerta revisada: {observaciones}]"
                else:
                    germinacion.observaciones = f"[Alerta revisada: {observaciones}]"

            germinacion.save()
            serializer = self.get_serializer(germinacion)
            return Response({
                'mensaje': 'Alerta marcada como revisada exitosamente',
                'germinacion': serializer.data
            })
        except Exception as e:
            return self.handle_error(e, "Error marcando alerta como revisada")

    @action(detail=False, methods=['get'], url_path='estadisticas_precision_modelo')
    def estadisticas_precision_modelo(self, request):
        """Obtiene estadísticas de precisión del modelo de predicción de germinación"""
        try:
            validadas = Germinacion.objects.filter(
                prediccion_fecha_estimada__isnull=False,
                fecha_germinacion__isnull=False
            )
            total_validadas = validadas.count()
            total_predicciones = Germinacion.objects.filter(
                prediccion_fecha_estimada__isnull=False
            ).count()

            if total_validadas == 0:
                return Response({
                    'total_predicciones': total_predicciones,
                    'predicciones_validadas': 0,
                    'precision_promedio': 0,
                    'error_promedio_dias': 0,
                    'distribucion_precision': {'excelente': 0, 'buena': 0, 'aceptable': 0, 'baja': 0},
                    'mensaje': 'No hay predicciones validadas aún'
                })

            errores = [
                abs((g.fecha_germinacion - g.prediccion_fecha_estimada).days)
                for g in validadas
                if g.fecha_germinacion and g.prediccion_fecha_estimada
            ]
            error_promedio = sum(errores) / len(errores) if errores else 0
            precision_promedio = max(0, 100 - (error_promedio * 2))

            return Response({
                'total_predicciones': total_predicciones,
                'predicciones_validadas': total_validadas,
                'precision_promedio': round(precision_promedio, 2),
                'error_promedio_dias': round(error_promedio, 1),
                'distribucion_precision': {
                    'excelente': sum(1 for d in errores if d <= 3),
                    'buena': sum(1 for d in errores if 3 < d <= 7),
                    'aceptable': sum(1 for d in errores if 7 < d <= 14),
                    'baja': sum(1 for d in errores if d > 14),
                }
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo estadísticas de precisión del modelo")

    @action(detail=False, methods=['get'], url_path='exportar_predicciones_csv')
    def exportar_predicciones_csv(self, request):
        """Exporta predicciones de germinación a CSV"""
        try:
            from datetime import datetime as dt

            fecha_inicio = request.GET.get('fecha_inicio')
            fecha_fin = request.GET.get('fecha_fin')
            especie = request.GET.get('especie')
            genero = request.GET.get('genero')

            queryset = Germinacion.objects.filter(
                prediccion_fecha_estimada__isnull=False
            ).select_related('creado_por').order_by('-fecha_creacion')

            if fecha_inicio:
                queryset = queryset.filter(fecha_siembra__gte=fecha_inicio)
            if fecha_fin:
                queryset = queryset.filter(fecha_siembra__lte=fecha_fin)
            if especie:
                queryset = queryset.filter(especie_variedad__icontains=especie)
            if genero:
                queryset = queryset.filter(genero__icontains=genero)

            response = HttpResponse(content_type='text/csv; charset=utf-8')
            filename = f"predicciones_germinacion_{dt.now().strftime('%Y%m%d')}.csv"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response.write('\ufeff')  # BOM para Excel

            writer = csv.writer(response)
            writer.writerow([
                'Código', 'Género', 'Especie/Variedad', 'Fecha Siembra',
                'Días Estimados', 'Fecha Estimada', 'Confianza (%)', 'Tipo Predicción',
                'Fecha Real Germinación', 'Error Días', 'Clima', 'Responsable'
            ])

            for g in queryset:
                error_dias = ''
                if g.fecha_germinacion and g.prediccion_fecha_estimada:
                    error_dias = abs((g.fecha_germinacion - g.prediccion_fecha_estimada).days)
                writer.writerow([
                    g.codigo or '',
                    g.genero or '',
                    g.especie_variedad or '',
                    g.fecha_siembra.strftime('%Y-%m-%d') if g.fecha_siembra else '',
                    g.prediccion_dias_estimados or '',
                    g.prediccion_fecha_estimada.strftime('%Y-%m-%d') if g.prediccion_fecha_estimada else '',
                    float(g.prediccion_confianza) if g.prediccion_confianza else '',
                    g.prediccion_tipo or '',
                    g.fecha_germinacion.strftime('%Y-%m-%d') if g.fecha_germinacion else '',
                    error_dias,
                    g.clima or '',
                    g.responsable or ''
                ])
            return response
        except Exception as e:
            return self.handle_error(e, "Error exportando predicciones a CSV")

    @action(detail=False, methods=['post'], url_path='crear_backup_modelo')
    def crear_backup_modelo(self, request):
        """Crea y descarga un backup del modelo ML de germinación"""
        try:
            from datetime import datetime as dt

            model_paths = [
                os.path.join(settings.BASE_DIR, 'laboratorio', 'modelos', 'germinacion.pkl'),
                os.path.join(settings.BASE_DIR, 'laboratorio', 'ml', 'modelos', 'germinacion.pkl'),
            ]
            model_path = next((p for p in model_paths if os.path.exists(p)), None)

            if not model_path:
                return Response(
                    {'error': 'No se encontró el modelo entrenado en el servidor'},
                    status=status.HTTP_404_NOT_FOUND
                )

            with open(model_path, 'rb') as f:
                model_data = f.read()

            response = HttpResponse(model_data, content_type='application/octet-stream')
            filename = f"germinacion_backup_{dt.now().strftime('%Y%m%d_%H%M%S')}.pkl"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
        except Exception as e:
            return self.handle_error(e, "Error creando backup del modelo")

    @action(detail=False, methods=['get'], url_path='info_backup_modelo')
    def info_backup_modelo(self, request):
        """Obtiene información del modelo ML actual de germinación"""
        try:
            from datetime import datetime as dt

            model_paths = [
                os.path.join(settings.BASE_DIR, 'laboratorio', 'modelos', 'germinacion.pkl'),
                os.path.join(settings.BASE_DIR, 'laboratorio', 'ml', 'modelos', 'germinacion.pkl'),
            ]
            model_path = next((p for p in model_paths if os.path.exists(p)), None)

            if not model_path:
                return Response({'modelo_disponible': False, 'mensaje': 'No hay modelo entrenado disponible'})

            stat = os.stat(model_path)
            return Response({
                'modelo_disponible': True,
                'nombre_archivo': os.path.basename(model_path),
                'tamano_bytes': stat.st_size,
                'fecha_modificacion': dt.fromtimestamp(stat.st_mtime).isoformat(),
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo información del modelo")

    @action(detail=False, methods=['post'], url_path='reentrenar_modelo')
    def reentrenar_modelo(self, request):
        """Reinicia el contador de predicciones faltantes y reporta datos disponibles para reentrenamiento"""
        try:
            datos = Germinacion.objects.filter(
                fecha_siembra__isnull=False,
                fecha_germinacion__isnull=False,
                especie_variedad__isnull=False
            )
            total_registros = datos.count()

            if total_registros < 10:
                return Response({
                    'exito': False,
                    'mensaje': f'Datos insuficientes. Se necesitan al menos 10 registros con fecha de germinación real (disponibles: {total_registros})',
                    'registros_disponibles': total_registros
                }, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                'exito': True,
                'mensaje': f'Se encontraron {total_registros} registros válidos para reentrenamiento',
                'registros_utilizados': total_registros,
                'estado': 'COMPLETADO'
            })
        except Exception as e:
            return self.handle_error(e, "Error en proceso de reentrenamiento")

    @action(detail=False, methods=['post'], url_path='completar_predicciones_faltantes')
    def completar_predicciones_faltantes(self, request):
        """Genera predicciones para germinaciones que no las tienen"""
        try:

            sin_prediccion = Germinacion.objects.filter(
                prediccion_fecha_estimada__isnull=True,
                fecha_siembra__isnull=False,
                especie_variedad__isnull=False
            )
            total = sin_prediccion.count()
            completadas = 0
            errores = 0

            for germinacion in sin_prediccion[:100]:
                try:
                    data = {
                        'especie': germinacion.especie_variedad or '',
                        'genero': germinacion.genero or '',
                        'fecha_siembra': germinacion.fecha_siembra.strftime('%Y-%m-%d'),
                        'clima': germinacion.clima or 'I'
                    }
                    resultado = prediccion_service.calcular_prediccion_germinacion(data)
                    if resultado and resultado.get('dias_estimados'):
                        germinacion.prediccion_dias_estimados = resultado['dias_estimados']
                        germinacion.prediccion_fecha_estimada = germinacion.fecha_siembra + timedelta(days=resultado['dias_estimados'])
                        if resultado.get('confianza'):
                            germinacion.prediccion_confianza = resultado['confianza']
                        germinacion.prediccion_tipo = resultado.get('metodo', 'HEURISTIC')
                        germinacion.save(update_fields=[
                            'prediccion_dias_estimados', 'prediccion_fecha_estimada',
                            'prediccion_confianza', 'prediccion_tipo'
                        ])
                        completadas += 1
                except Exception:
                    errores += 1

            return Response({
                'mensaje': f'Proceso completado: {completadas} predicciones generadas, {errores} errores',
                'total_sin_prediccion': total,
                'predicciones_generadas': completadas,
                'errores': errores
            })
        except Exception as e:
            return self.handle_error(e, "Error completando predicciones faltantes")

    @action(detail=False, methods=['get'], url_path='estado_modelo')
    def estado_modelo(self, request):
        """Obtiene el estado actual del modelo ML de germinación"""
        try:

            model_paths = [
                os.path.join(settings.BASE_DIR, 'laboratorio', 'modelos', 'germinacion.pkl'),
                os.path.join(settings.BASE_DIR, 'laboratorio', 'ml', 'modelos', 'germinacion.pkl'),
            ]
            model_disponible = any(os.path.exists(p) for p in model_paths)
            total = Germinacion.objects.count()
            con_prediccion = Germinacion.objects.filter(prediccion_fecha_estimada__isnull=False).count()
            validadas = Germinacion.objects.filter(
                prediccion_fecha_estimada__isnull=False,
                fecha_germinacion__isnull=False
            ).count()

            return Response({
                'modelo_disponible': model_disponible,
                'tipo_modelo': 'Random Forest (Germinación)',
                'estado': 'ACTIVO' if model_disponible else 'NO_DISPONIBLE',
                'estadisticas': {
                    'total_germinaciones': total,
                    'con_prediccion': con_prediccion,
                    'validadas': validadas,
                    'cobertura': round(con_prediccion / total * 100, 1) if total > 0 else 0
                }
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo estado del modelo")

    @action(detail=False, methods=['get'], url_path='performance_metrics')
    def performance_metrics(self, request):
        """Obtiene métricas de rendimiento del modelo de germinación"""
        try:
            validadas = Germinacion.objects.filter(
                prediccion_fecha_estimada__isnull=False,
                fecha_germinacion__isnull=False
            )
            total = validadas.count()

            if total == 0:
                return Response({
                    'mae': 0, 'rmse': 0,
                    'accuracy_7dias': 0, 'accuracy_14dias': 0,
                    'total_evaluadas': 0,
                    'mensaje': 'No hay suficientes datos para calcular métricas'
                })

            errores = [
                (g.fecha_germinacion - g.prediccion_fecha_estimada).days
                for g in validadas
                if g.fecha_germinacion and g.prediccion_fecha_estimada
            ]
            mae = sum(abs(e) for e in errores) / len(errores)
            rmse = (sum(e ** 2 for e in errores) / len(errores)) ** 0.5
            acc_7 = sum(1 for e in errores if abs(e) <= 7) / len(errores) * 100
            acc_14 = sum(1 for e in errores if abs(e) <= 14) / len(errores) * 100

            return Response({
                'mae': round(mae, 2),
                'rmse': round(rmse, 2),
                'accuracy_7dias': round(acc_7, 1),
                'accuracy_14dias': round(acc_14, 1),
                'total_evaluadas': total,
                'error_promedio_dias': round(mae, 1)
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo métricas de rendimiento")

    @action(detail=True, methods=['post'], url_path='validar-prediccion')
    def validar_prediccion(self, request, pk=None):
        """Valida la predicción comparando con la fecha real de germinación"""
        try:
            germinacion = self.get_object()
            fecha_real_str = request.data.get('fecha_real_germinacion')

            if not fecha_real_str:
                return Response(
                    {'error': 'El campo fecha_real_germinacion es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from datetime import datetime as dt
            try:
                fecha_real = dt.strptime(fecha_real_str, '%Y-%m-%d').date()
            except ValueError:
                return Response(
                    {'error': 'Formato de fecha inválido. Use YYYY-MM-DD'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            germinacion.fecha_germinacion = fecha_real
            dias_reales = None
            diferencia_dias = None
            precision = None
            calidad = 'sin_datos'

            if germinacion.fecha_siembra:
                dias_reales = (fecha_real - germinacion.fecha_siembra).days

            if germinacion.prediccion_fecha_estimada:
                diferencia_dias = abs((fecha_real - germinacion.prediccion_fecha_estimada).days)
                dias_predichos = germinacion.prediccion_dias_estimados or 0
                if dias_predichos > 0:
                    precision = max(0.0, 100 - (diferencia_dias / dias_predichos * 100))
                else:
                    precision = max(0.0, 100 - diferencia_dias * 2)

                if diferencia_dias <= 3:
                    calidad = 'excelente'
                elif diferencia_dias <= 7:
                    calidad = 'buena'
                elif diferencia_dias <= 14:
                    calidad = 'aceptable'
                else:
                    calidad = 'baja'

            germinacion.save()
            serializer = self.get_serializer(germinacion)

            return Response({
                'mensaje': 'Predicción validada exitosamente',
                'validacion': {
                    'dias_reales': dias_reales,
                    'dias_predichos': germinacion.prediccion_dias_estimados,
                    'diferencia_dias': diferencia_dias,
                    'precision': round(precision, 1) if precision is not None else None,
                    'calidad': calidad
                },
                'germinacion': serializer.data
            })
        except Exception as e:
            return self.handle_error(e, "Error validando predicción")