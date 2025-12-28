"""
Vistas para Polinizaciones usando servicios de negocio
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
import logging

from ..models import Polinizacion
from ..serializers import PolinizacionSerializer
from ..services.polinizacion_service import polinizacion_service
from ..permissions import CanViewPolinizaciones, CanCreatePolinizaciones, CanEditPolinizaciones
from .base_views import BaseServiceViewSet, ErrorHandlerMixin, SearchMixin
from ..renderers import BinaryFileRenderer

logger = logging.getLogger(__name__)


class PolinizacionViewSet(BaseServiceViewSet, ErrorHandlerMixin, SearchMixin):
    """
    ViewSet para Polinizaciones usando servicios de negocio
    """
    queryset = Polinizacion.objects.all()
    serializer_class = PolinizacionSerializer
    service_class = type(polinizacion_service)
    permission_classes = [IsAuthenticated]
    
    # Definir permisos por acción
    role_permissions = {
        'list': CanViewPolinizaciones,
        'retrieve': CanViewPolinizaciones,
        'create': CanCreatePolinizaciones,
        'update': CanEditPolinizaciones,
        'partial_update': CanEditPolinizaciones,
        'destroy': CanEditPolinizaciones,
        'mis_polinizaciones': CanViewPolinizaciones,
        'todas_admin': CanViewPolinizaciones,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = polinizacion_service
    
    def get_queryset(self):
        """Optimizar consulta con select_related"""
        return Polinizacion.objects.select_related(
            'creado_por'
        ).order_by('-fecha_creacion')
    
    def perform_create(self, serializer):
        """Crear polinización usando el servicio"""
        try:
            logger.info(f"Creando polinización para usuario: {self.request.user}")
            
            polinizacion = self.service.create(
                serializer.validated_data,
                user=self.request.user
            )
            
            # Crear notificación automáticamente
            try:
                from ..services.notification_service import notification_service
                notification_service.crear_notificacion_polinizacion(
                    usuario=self.request.user,
                    polinizacion=polinizacion,
                    tipo='NUEVA_POLINIZACION'
                )
                logger.info(f"Notificación creada para polinización {polinizacion.numero}")
            except Exception as e:
                logger.warning(f"No se pudo crear notificación: {e}")
            
            return polinizacion
        
        except Exception as e:
            logger.error(f"Error creando polinización: {e}")
            raise
    
    def perform_update(self, serializer):
        """Actualizar polinización usando el servicio"""
        try:
            polinizacion_anterior = self.get_object()
            estado_anterior = polinizacion_anterior.estado
            
            polinizacion = self.service.update(
                polinizacion_anterior.pk,
                serializer.validated_data,
                user=self.request.user
            )
            
            # Crear notificación si cambió el estado
            if polinizacion.estado != estado_anterior:
                try:
                    from ..services.notification_service import notification_service
                    notification_service.crear_notificacion_polinizacion(
                        usuario=self.request.user,
                        polinizacion=polinizacion,
                        tipo='ESTADO_POLINIZACION_ACTUALIZADO'
                    )
                    logger.info(f"Notificación de cambio de estado creada para polinización {polinizacion.numero}")
                except Exception as e:
                    logger.warning(f"No se pudo crear notificación: {e}")
            
            return polinizacion
        
        except Exception as e:
            logger.error(f"Error actualizando polinización: {e}")
            raise
    
    @action(detail=False, methods=['get'], url_path='mis-polinizaciones')
    def mis_polinizaciones(self, request):
        """Obtiene solo las polinizaciones del usuario autenticado con soporte de paginación"""
        try:
            search = request.GET.get('search', '').strip()
            page = int(request.GET.get('page', 1))
            page_size = int(request.GET.get('page_size', 20))
            dias_recientes = request.GET.get('dias_recientes', None)
            if dias_recientes:
                dias_recientes = int(dias_recientes)
            
            logger.info(f"Obteniendo mis polinizaciones para usuario: {request.user.username}, página: {page}, días recientes: {dias_recientes}")
            
            # Si se solicita paginación, usar método paginado
            if request.GET.get('paginated', 'false').lower() == 'true' or page_size < 1000:
                logger.info("Usando método paginado")
                try:
                    result = self.service.get_mis_polinizaciones_paginated(
                        user=request.user,
                        page=page,
                        page_size=page_size,
                        search=search,
                        dias_recientes=dias_recientes
                    )
                    
                    logger.info(f"Resultado paginado obtenido: {result['count']} registros")
                    
                    serializer = self.get_serializer(result['results'], many=True)
                    
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
                except Exception as e:
                    logger.error(f"Error en método paginado: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
            else:
                # Sin paginación (compatibilidad hacia atrás)
                logger.info("Usando método sin paginación")
                polinizaciones = self.service.get_mis_polinizaciones(
                    user=request.user,
                    search=search,
                    dias_recientes=dias_recientes
                )
                
                serializer = self.get_serializer(polinizaciones, many=True)
                
                logger.info(f"Retornando {len(serializer.data)} polinizaciones")
                return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error general en mis_polinizaciones: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self.handle_error(e, "Error obteniendo mis polinizaciones")
    
    @action(detail=False, methods=['get'], url_path='todas-admin')
    def todas_admin(self, request):
        """Obtiene TODAS las polinizaciones para administradores"""
        try:
            user = request.user
            
            # Verificar que sea administrador
            if not hasattr(user, 'profile') or user.profile.rol != 'TIPO_4':
                return Response(
                    {'error': 'Solo los administradores pueden acceder a todas las polinizaciones'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            logger.info(f"Obteniendo todas las polinizaciones para admin: {user.username}")
            
            polinizaciones = self.service.get_all(user=user)
            serializer = self.get_serializer(polinizaciones, many=True)
            
            return Response({
                'count': len(serializer.data),
                'results': serializer.data
            })
            
        except Exception as e:
            return self.handle_error(e, "Error obteniendo todas las polinizaciones")
    
    @action(detail=False, methods=['get'], url_path='codigos-nuevas-plantas')
    def codigos_nuevas_plantas(self, request):
        """Obtiene códigos de nuevas plantas para autocompletado"""
        try:
            codigos = self.service.get_codigos_nuevas_plantas()
            return Response({
                'codigos': codigos,
                'total': len(codigos)
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo códigos de nuevas plantas")
    
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
    
    @action(detail=False, methods=['get'], url_path='buscar-por-codigo')
    def buscar_por_codigo(self, request):
        """Busca una polinización por código de nueva planta"""
        try:
            codigo = request.GET.get('codigo', '').strip()
            if not codigo:
                return Response(
                    {'error': 'Código es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            resultado = self.service.get_polinizacion_by_codigo_nueva_planta(codigo)

            if resultado:
                return Response(resultado)
            else:
                return Response(
                    {'error': 'No se encontró polinización con ese código'},
                    status=status.HTTP_404_NOT_FOUND
                )

        except Exception as e:
            return self.handle_error(e, "Error buscando por código")

    @action(detail=False, methods=['get'], url_path='buscar-planta-info')
    def buscar_planta_info(self, request):
        """Busca información de una planta por código en polinizaciones y germinaciones"""
        try:
            codigo = request.GET.get('codigo', '').strip()
            if not codigo:
                return Response(
                    {'error': 'Código es requerido'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from ..models import Germinacion
            from django.db.models import Q

            # Buscar en polinizaciones (nueva_codigo, madre_codigo, padre_codigo)
            polinizacion = Polinizacion.objects.filter(
                Q(nueva_codigo=codigo) | Q(madre_codigo=codigo) | Q(padre_codigo=codigo)
            ).first()

            if polinizacion:
                # Determinar de qué planta es el código
                if polinizacion.nueva_codigo == codigo:
                    return Response({
                        'codigo': codigo,
                        'genero': polinizacion.nueva_genero,
                        'especie': polinizacion.nueva_especie,
                        'clima': polinizacion.nueva_clima,
                        'fuente': 'polinizacion_nueva'
                    })
                elif polinizacion.madre_codigo == codigo:
                    return Response({
                        'codigo': codigo,
                        'genero': polinizacion.madre_genero,
                        'especie': polinizacion.madre_especie,
                        'clima': polinizacion.madre_clima,
                        'fuente': 'polinizacion_madre'
                    })
                elif polinizacion.padre_codigo == codigo:
                    return Response({
                        'codigo': codigo,
                        'genero': polinizacion.padre_genero,
                        'especie': polinizacion.padre_especie,
                        'clima': polinizacion.padre_clima,
                        'fuente': 'polinizacion_padre'
                    })

            # Buscar en germinaciones
            germinacion = Germinacion.objects.filter(codigo=codigo).first()

            if germinacion:
                return Response({
                    'codigo': codigo,
                    'genero': germinacion.genero or '',
                    'especie': germinacion.especie_variedad or '',
                    'clima': germinacion.clima or 'I',
                    'fuente': 'germinacion'
                })

            # No se encontró
            return Response(
                {'error': 'No se encontró planta con ese código'},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error buscando información de planta: {e}")
            return self.handle_error(e, "Error buscando información de planta")
    
    @action(detail=False, methods=['get'], url_path='polinizaciones-pdf', renderer_classes=[BinaryFileRenderer])
    def polinizaciones_pdf(self, request):
        """Genera PDF de TODAS las polinizaciones del sistema"""
        try:
            search = request.GET.get('search', '').strip()

            # Obtener todas las polinizaciones del sistema
            queryset = Polinizacion.objects.select_related(
                'creado_por'
            ).order_by('-fecha_creacion')

            # Aplicar búsqueda si existe
            if search:
                queryset = queryset.filter(
                    Q(codigo__icontains=search) |
                    Q(nueva_codigo__icontains=search) |
                    Q(genero__icontains=search) |
                    Q(madre_genero__icontains=search) |
                    Q(padre_genero__icontains=search) |
                    Q(nueva_genero__icontains=search) |
                    Q(especie__icontains=search) |
                    Q(madre_especie__icontains=search) |
                    Q(padre_especie__icontains=search) |
                    Q(nueva_especie__icontains=search)
                )

            polinizaciones = list(queryset)

            # Generar PDF directamente usando HttpResponse
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER
            import io
            from datetime import datetime
            from django.http import HttpResponse

            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f"_busqueda_{search}" if search else ""
            filename = f"polinizaciones_todas_{datetime.now().strftime('%Y%m%d')}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'

            # Crear PDF en modo landscape para más columnas
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)

            # Contenedor de elementos
            elements = []
            styles = getSampleStyleSheet()

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

            # Título
            title = Paragraph(f"<b>Reporte de Todas las Polinizaciones del Sistema</b>", title_style)
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
            info_text += f" | Total: {len(polinizaciones)} registros"

            info = Paragraph(info_text, subtitle_style)
            elements.append(info)
            elements.append(Spacer(1, 20))

            # Crear tabla de datos
            data = [['Código', 'Tipo', 'Fecha\nPolini.', 'Madre\nGénero', 'Madre\nEspecie', 'Padre\nGénero', 'Padre\nEspecie', 'Nueva\nGénero', 'Nueva\nEspecie', 'Ubicación']]

            for pol in polinizaciones:
                data.append([
                    str(pol.codigo or pol.nueva_codigo or '')[:12],
                    str(pol.tipo_polinizacion or pol.Tipo or '')[:6],
                    pol.fechapol.strftime('%d/%m/%Y') if pol.fechapol else '',
                    str(pol.madre_genero or pol.genero or '')[:10],
                    str(pol.madre_especie or pol.especie or '')[:15],
                    str(pol.padre_genero or '')[:10],
                    str(pol.padre_especie or '')[:15],
                    str(pol.nueva_genero or '')[:10],
                    str(pol.nueva_especie or '')[:15],
                    str(pol.ubicacion_nombre or pol.vivero or pol.ubicacion or '')[:10]
                ])

            # Crear tabla
            table = Table(data, colWidths=[0.9*inch, 0.6*inch, 0.75*inch, 0.9*inch, 1.2*inch, 0.9*inch, 1.2*inch, 0.9*inch, 1.2*inch, 0.8*inch])

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

                # Datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Fecha
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
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
            logger.error(f"Error generando PDF de polinizaciones: {e}")
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['get'], url_path='mis-polinizaciones-pdf', renderer_classes=[BinaryFileRenderer])
    def mis_polinizaciones_pdf(self, request):
        """Genera PDF de las polinizaciones del usuario"""
        try:
            search = request.GET.get('search', '').strip()

            # Obtener polinizaciones del usuario (excluyendo importadas por defecto)
            polinizaciones = self.service.get_mis_polinizaciones(
                user=request.user,
                search=search,
                excluir_importadas=True  # Por defecto excluir importaciones
            )

            # Generar PDF directamente usando HttpResponse
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.lib.enums import TA_CENTER
            import io
            from datetime import datetime
            from django.http import HttpResponse

            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f"_busqueda_{search}" if search else ""
            filename = f"polinizaciones_{request.user.username}_{datetime.now().strftime('%Y%m%d')}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'

            # Crear PDF en modo landscape para más columnas
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), topMargin=0.5*inch, bottomMargin=0.5*inch)

            # Contenedor de elementos
            elements = []
            styles = getSampleStyleSheet()

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

            # Título
            user_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
            title = Paragraph(f"<b>Reporte de Polinizaciones</b>", title_style)
            elements.append(title)

            # Subtítulo con información del usuario
            subtitle = Paragraph(f"Usuario: {user_name} ({request.user.username})", subtitle_style)
            elements.append(subtitle)

            # Información adicional
            fecha_generacion = datetime.now().strftime('%d/%m/%Y %H:%M')
            info_text = f"Fecha de generación: {fecha_generacion}"
            if search:
                info_text += f" | Búsqueda: {search}"
            info_text += f" | Total: {len(polinizaciones)} registros"

            info = Paragraph(info_text, subtitle_style)
            elements.append(info)
            elements.append(Spacer(1, 20))

            # Crear tabla de datos
            data = [['Código', 'Tipo', 'Fecha\nPolini.', 'Madre\nGénero', 'Madre\nEspecie', 'Padre\nGénero', 'Padre\nEspecie', 'Nueva\nGénero', 'Nueva\nEspecie', 'Ubicación']]

            for pol in polinizaciones:
                data.append([
                    str(pol.codigo or pol.nueva_codigo or '')[:12],
                    str(pol.tipo_polinizacion or pol.Tipo or '')[:6],
                    pol.fechapol.strftime('%d/%m/%Y') if pol.fechapol else '',
                    str(pol.madre_genero or pol.genero or '')[:10],
                    str(pol.madre_especie or pol.especie or '')[:15],
                    str(pol.padre_genero or '')[:10],
                    str(pol.padre_especie or '')[:15],
                    str(pol.nueva_genero or '')[:10],
                    str(pol.nueva_especie or '')[:15],
                    str(pol.ubicacion_nombre or pol.vivero or pol.ubicacion or '')[:10]
                ])

            # Crear tabla
            table = Table(data, colWidths=[0.9*inch, 0.6*inch, 0.75*inch, 0.9*inch, 1.2*inch, 0.9*inch, 1.2*inch, 0.9*inch, 1.2*inch, 0.8*inch])

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

                # Datos
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),  # Fecha
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
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
            logger.info(f"PDF generado exitosamente para {request.user.username}: {len(polinizaciones)} registros")
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
    
    @action(detail=False, methods=['get'], url_path='debug-headers')
    def debug_headers(self, request):
        """Endpoint de debug para ver headers"""
        return Response({
            'headers': dict(request.headers),
            'method': request.method,
            'content_type': request.content_type,
            'accepts': request.META.get('HTTP_ACCEPT', 'No Accept header'),
            'user_agent': request.META.get('HTTP_USER_AGENT', 'No User-Agent'),
        })

    @action(detail=False, methods=['get'], url_path='alertas_polinizacion')
    def alertas_polinizacion(self, request):
        """Obtener alertas de polinizaciones próximas a madurar"""
        try:
            from django.utils import timezone
            from datetime import timedelta
            
            # Obtener polinizaciones del usuario
            polinizaciones = self.get_queryset().filter(creado_por=request.user)
            
            # Filtrar polinizaciones con predicción y que no hayan madurado
            alertas = []
            hoy = timezone.now().date()
            
            for polinizacion in polinizaciones:
                # Solo considerar polinizaciones que no han madurado aún
                if not polinizacion.fechamad:
                    # Si tiene predicción de fecha estimada
                    if polinizacion.prediccion_fecha_estimada:
                        fecha_estimada = polinizacion.prediccion_fecha_estimada
                        dias_restantes = (fecha_estimada - hoy).days
                        
                        # Alertas para polinizaciones próximas (dentro de 7 días) o vencidas
                        if dias_restantes <= 7:
                            tipo_alerta = 'vencida' if dias_restantes < 0 else 'proxima'
                            alertas.append({
                                'id': polinizacion.numero,
                                'codigo': polinizacion.codigo,
                                'tipo_polinizacion': polinizacion.tipo_polinizacion,
                                'especie': polinizacion.madre_especie or polinizacion.nueva_especie or '',
                                'genero': polinizacion.madre_genero or polinizacion.nueva_genero or '',
                                'fecha_polinizacion': polinizacion.fechapol,
                                'fecha_estimada': fecha_estimada,
                                'dias_restantes': dias_restantes,
                                'tipo_alerta': tipo_alerta,
                                'mensaje': f"Polinización {'vencida' if dias_restantes < 0 else 'próxima a madurar'}"
                            })
            
            return Response({
                'alertas': alertas,
                'total': len(alertas)
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo alertas de polinización: {e}")
            return Response(
                {'error': f'Error al obtener alertas: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='filter-options')
    def filter_options(self, request):
        """Obtiene opciones para filtros de polinizaciones"""
        try:
            user = request.user

            # Obtener queryset base (todos si es admin, solo propios si no)
            if hasattr(user, 'profile') and user.profile.rol == 'TIPO_4':
                queryset = Polinizacion.objects.all()
            else:
                queryset = Polinizacion.objects.filter(creado_por=user)

            options = {
                'estados': list(queryset.values_list('estado', flat=True).distinct().exclude(estado='').order_by('estado')),
                'tipos_polinizacion': list(queryset.values_list('tipo_polinizacion', flat=True).distinct().exclude(tipo_polinizacion='').order_by('tipo_polinizacion')),
                'responsables': list(queryset.values_list('responsable', flat=True).distinct().exclude(responsable='').order_by('responsable')),
                'generos': list(queryset.values_list('genero', flat=True).distinct().exclude(genero='').order_by('genero')),
                'especies': list(queryset.values_list('especie', flat=True).distinct().exclude(especie='').order_by('especie')),
                'ubicacion_nombres': list(queryset.values_list('ubicacion_nombre', flat=True).distinct().exclude(ubicacion_nombre='').order_by('ubicacion_nombre')),
                'ubicacion_tipos': list(queryset.values_list('ubicacion_tipo', flat=True).distinct().exclude(ubicacion_tipo='').order_by('ubicacion_tipo')),
                # Nuevos campos de ubicación detallada
                'viveros': list(queryset.values_list('vivero', flat=True).distinct().exclude(vivero='').order_by('vivero')),
                'mesas': list(queryset.values_list('mesa', flat=True).distinct().exclude(mesa='').order_by('mesa')),
                'paredes': list(queryset.values_list('pared', flat=True).distinct().exclude(pared='').order_by('pared')),
            }

            # Opciones de madre, padre, nueva (pueden ser muchos, limitar o solo ofrecer búsqueda)
            # Por ahora, solo listamos las opciones más relevantes como chips

            return Response({
                'opciones': options,
                'estadisticas': { # Podemos añadir estadísticas rápidas aquí si es necesario
                    'total': queryset.count()
                }
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo opciones de filtro de polinizaciones")

    @action(detail=False, methods=['get'], url_path='viveros')
    def viveros(self, request):
        """Obtiene lista de viveros únicos para el formulario con búsqueda opcional"""
        try:
            # Parámetro de búsqueda opcional
            search = request.GET.get('search', '').strip()

            # Obtener todos los viveros únicos
            queryset = Polinizacion.objects.exclude(vivero='')

            # Filtrar por búsqueda si se proporciona
            if search:
                queryset = queryset.filter(vivero__icontains=search)

            viveros = queryset.values_list('vivero', flat=True).distinct()
            viveros_list = list(viveros)

            # Ordenar numéricamente: V-1, V-2, V-10, V-11, etc.
            def ordenar_codigo(codigo):
                try:
                    numero = int(codigo.split('-')[1])
                    return numero
                except:
                    return 99999

            viveros_list.sort(key=ordenar_codigo)

            return Response({
                'viveros': viveros_list,
                'total': len(viveros_list),
                'search': search if search else None
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo viveros")

    @action(detail=False, methods=['get'], url_path='mesas')
    def mesas(self, request):
        """Obtiene lista de mesas únicas para el formulario con búsqueda opcional"""
        try:
            # Parámetros opcionales
            vivero = request.GET.get('vivero', '').strip()
            search = request.GET.get('search', '').strip()

            queryset = Polinizacion.objects.exclude(mesa='')

            # Filtrar por vivero si se proporciona
            if vivero:
                queryset = queryset.filter(vivero=vivero)

            # Filtrar por búsqueda si se proporciona
            if search:
                queryset = queryset.filter(mesa__icontains=search)

            mesas = queryset.values_list('mesa', flat=True).distinct()
            mesas_list = list(mesas)

            # Ordenar numéricamente: M-1A, M-2A, M-10A, M-11A, etc.
            def ordenar_mesa(codigo):
                try:
                    # Extraer número de M-XY
                    import re
                    match = re.match(r'M-(\d+)([A-Z]+)', codigo)
                    if match:
                        numero = int(match.group(1))
                        letra = match.group(2)
                        return (numero, letra)
                    return (99999, codigo)
                except:
                    return (99999, codigo)

            mesas_list.sort(key=ordenar_mesa)

            return Response({
                'mesas': mesas_list,
                'total': len(mesas_list),
                'vivero_filtrado': vivero if vivero else None,
                'search': search if search else None
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo mesas")

    @action(detail=True, methods=['post'], url_path='marcar-revisado')
    def marcar_revisado(self, request, pk=None):
        """Marca una polinización como revisada y programa la próxima revisión"""
        try:
            polinizacion = self.get_object()
            
            # Obtener datos del request
            nuevo_estado = request.data.get('estado')
            progreso = request.data.get('progreso')
            dias_proxima_revision = request.data.get('dias_proxima_revision', 10)  # Por defecto 10 días
            
            from django.utils import timezone
            from datetime import timedelta
            
            # Actualizar fecha de última revisión
            polinizacion.fecha_ultima_revision = timezone.now().date()
            
            # Actualizar estado si se proporciona
            if nuevo_estado:
                estados_validos = ['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO', 'FINALIZADO']
                if nuevo_estado in estados_validos:
                    polinizacion.estado_polinizacion = nuevo_estado
                    
                    # Actualizar progreso según el estado
                    if nuevo_estado == 'INICIAL':
                        polinizacion.progreso_polinizacion = 10
                    elif nuevo_estado == 'EN_PROCESO_TEMPRANO':
                        polinizacion.progreso_polinizacion = 35
                    elif nuevo_estado == 'EN_PROCESO_AVANZADO':
                        polinizacion.progreso_polinizacion = 75
                    elif nuevo_estado == 'FINALIZADO':
                        polinizacion.progreso_polinizacion = 100
                        if not polinizacion.fechamad:
                            polinizacion.fechamad = timezone.now().date()
            
            # Actualizar progreso si se proporciona explícitamente
            if progreso is not None:
                try:
                    progreso = int(progreso)
                    if 0 <= progreso <= 100:
                        polinizacion.progreso_polinizacion = progreso
                        polinizacion.actualizar_estado_por_progreso()
                except ValueError:
                    pass
            
            # Programar próxima revisión solo si no está finalizada
            if polinizacion.estado_polinizacion != 'FINALIZADO':
                polinizacion.fecha_proxima_revision = timezone.now().date() + timedelta(days=dias_proxima_revision)
                polinizacion.alerta_revision_enviada = False
            else:
                # Si está finalizada, no programar más revisiones
                polinizacion.fecha_proxima_revision = None
                polinizacion.alerta_revision_enviada = True
            
            polinizacion.save()
            
            # Serializar y retornar
            serializer = self.get_serializer(polinizacion)
            
            return Response({
                'message': 'Polinización marcada como revisada exitosamente',
                'polinizacion': serializer.data,
                'proxima_revision': polinizacion.fecha_proxima_revision.isoformat() if polinizacion.fecha_proxima_revision else None
            })
            
        except Exception as e:
            logger.error(f"Error marcando polinización como revisada: {e}")
            return Response(
                {'error': f'Error al marcar como revisada: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='pendientes-revision')
    def pendientes_revision(self, request):
        """Obtiene polinizaciones pendientes de revisión para el usuario actual"""
        try:
            from django.utils import timezone
            hoy = timezone.now().date()
            
            # Filtrar por usuario
            queryset = self.get_queryset().filter(creado_por=request.user)
            
            # Buscar pendientes de revisión
            pendientes = queryset.filter(
                fecha_proxima_revision__lte=hoy,
                estado_polinizacion__in=['INICIAL', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO']
            ).order_by('fecha_proxima_revision')
            
            serializer = self.get_serializer(pendientes, many=True)
            
            return Response({
                'count': len(serializer.data),
                'results': serializer.data
            })
            
        except Exception as e:
            return self.handle_error(e, "Error obteniendo polinizaciones pendientes de revisión")

    @action(detail=False, methods=['get'], url_path='paredes')
    def paredes(self, request):
        """Obtiene lista de paredes únicas para el formulario con búsqueda opcional"""
        try:
            # Parámetros opcionales
            vivero = request.GET.get('vivero', '').strip()
            search = request.GET.get('search', '').strip()

            queryset = Polinizacion.objects.exclude(pared='')

            # Filtrar por vivero si se proporciona
            if vivero:
                queryset = queryset.filter(vivero=vivero)

            # Filtrar por búsqueda si se proporciona
            if search:
                queryset = queryset.filter(pared__icontains=search)

            paredes = queryset.values_list('pared', flat=True).distinct()
            paredes_list = list(paredes)

            # Ordenar numéricamente: P-A, P-B, P-0, P-100, P-101, etc.
            def ordenar_pared(codigo):
                try:
                    import re
                    # P-X o P-XY donde X puede ser número o letra
                    if re.match(r'P-\d+', codigo):
                        numero = int(codigo.split('-')[1])
                        return (0, numero, '')
                    elif re.match(r'P-[A-Z]+', codigo):
                        letra = codigo.split('-')[1]
                        return (1, 0, letra)
                    else:
                        return (2, 0, codigo)
                except:
                    return (2, 0, codigo)

            paredes_list.sort(key=ordenar_pared)

            return Response({
                'paredes': paredes_list,
                'total': len(paredes_list),
                'vivero_filtrado': vivero if vivero else None,
                'search': search if search else None
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo paredes")

    @action(detail=False, methods=['get'], url_path='opciones-ubicacion')
    def opciones_ubicacion(self, request):
        """Obtiene todas las opciones de ubicación (viveros, mesas, paredes) en una sola llamada"""
        try:
            import re

            # Funciones de ordenamiento
            def ordenar_codigo(codigo):
                try:
                    numero = int(codigo.split('-')[1])
                    return numero
                except:
                    return 99999

            def ordenar_mesa(codigo):
                try:
                    match = re.match(r'M-(\d+)([A-Z]+)', codigo)
                    if match:
                        numero = int(match.group(1))
                        letra = match.group(2)
                        return (numero, letra)
                    return (99999, codigo)
                except:
                    return (99999, codigo)

            def ordenar_pared(codigo):
                try:
                    if re.match(r'P-\d+', codigo):
                        numero = int(codigo.split('-')[1])
                        return (0, numero, '')
                    elif re.match(r'P-[A-Z]+', codigo):
                        letra = codigo.split('-')[1]
                        return (1, 0, letra)
                    else:
                        return (2, 0, codigo)
                except:
                    return (2, 0, codigo)

            # Obtener viveros
            viveros = list(Polinizacion.objects.exclude(vivero='').values_list('vivero', flat=True).distinct())
            viveros.sort(key=ordenar_codigo)

            # Obtener mesas
            mesas = list(Polinizacion.objects.exclude(mesa='').values_list('mesa', flat=True).distinct())
            mesas.sort(key=ordenar_mesa)

            # Obtener paredes
            paredes = list(Polinizacion.objects.exclude(pared='').values_list('pared', flat=True).distinct())
            paredes.sort(key=ordenar_pared)

            return Response({
                'viveros': {
                    'opciones': viveros,
                    'total': len(viveros)
                },
                'mesas': {
                    'opciones': mesas,
                    'total': len(mesas)
                },
                'paredes': {
                    'opciones': paredes,
                    'total': len(paredes)
                }
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo opciones de ubicación")

    def _generate_simple_pdf(self, user, polinizaciones, search=""):
        """Genera PDF simple cuando ReportGenerator no está disponible"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            import io
            from datetime import datetime
            from django.http import HttpResponse
            
            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f" - Búsqueda: {search}" if search else ""
            filename = f"mis_polinizaciones_{user.username}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            # Agregar headers adicionales para evitar problemas de CORS y content negotiation
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
            response['Access-Control-Allow-Headers'] = 'Authorization, Content-Type, Accept'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'
            
            # Crear PDF
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            # Título
            p.setFont("Helvetica-Bold", 16)
            title = f"Mis Polinizaciones - {user.first_name} {user.last_name}".strip()
            if not title.endswith(user.username):
                title += f" ({user.username})"
            p.drawString(50, height - 50, title)
            
            if search:
                p.setFont("Helvetica", 12)
                p.drawString(50, height - 70, f"Filtro de búsqueda: {search}")
                y_position = height - 100
            else:
                y_position = height - 80
            
            # Información de fecha
            p.setFont("Helvetica", 10)
            p.drawString(50, y_position, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
            p.drawString(50, y_position - 15, f"Total de polinizaciones: {len(polinizaciones)}")
            
            y_position -= 50
            
            # Encabezados
            p.setFont("Helvetica-Bold", 10)
            p.drawString(50, y_position, "Código")
            p.drawString(150, y_position, "Género")
            p.drawString(250, y_position, "Especie")
            p.drawString(350, y_position, "Fecha Pol.")
            p.drawString(450, y_position, "Estado")
            
            y_position -= 20
            p.setFont("Helvetica", 9)
            
            # Datos
            for pol in polinizaciones:
                if y_position < 50:  # Nueva página si no hay espacio
                    p.showPage()
                    y_position = height - 50
                    p.setFont("Helvetica", 9)
                
                p.drawString(50, y_position, str(pol.codigo or '')[:15])
                p.drawString(150, y_position, str(pol.genero or '')[:15])
                p.drawString(250, y_position, str(pol.especie or '')[:15])
                p.drawString(350, y_position, str(pol.fechapol or '')[:10])
                p.drawString(450, y_position, str(pol.estado or '')[:10])
                
                y_position -= 15
            
            p.save()
            
            # Obtener PDF del buffer
            pdf_data = buffer.getvalue()
            buffer.close()
            
            response.write(pdf_data)
            return response

        except Exception as e:
            logger.error(f"Error generando PDF simple: {e}")
            # Retornar HttpResponse en lugar de Response para mantener consistencia
            from django.http import HttpResponse
            return HttpResponse(
                f'Error generando PDF: {str(e)}',
                status=500,
                content_type='text/plain'
            )
    
    @action(detail=False, methods=['post'], url_path='predecir-maduracion')
    def predecir_maduracion(self, request):
        """
        Predice los días de maduración para una polinización
        
        POST /api/polinizaciones/predecir-maduracion/
        Body: {
            "genero": "Cattleya",
            "especie": "maxima",
            "tipo": "SELF",
            "fecha_pol": "2025-01-15",
            "cantidad": 1
        }
        """
        try:
            # Validar datos requeridos
            genero = request.data.get('genero', '')
            especie = request.data.get('especie', '')
            tipo = request.data.get('tipo', 'SELF')
            fecha_pol = request.data.get('fecha_pol')
            cantidad = request.data.get('cantidad', 1)
            
            if not genero or not especie or not fecha_pol:
                return Response({
                    'error': 'Se requieren género, especie y fecha de polinización'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Hacer predicción
            prediccion = self.service.predecir_maduracion(
                genero=genero,
                especie=especie,
                tipo=tipo,
                fecha_pol=fecha_pol,
                cantidad=cantidad
            )
            
            if prediccion:
                return Response({
                    'success': True,
                    'prediccion': prediccion
                })
            else:
                return Response({
                    'error': 'No se pudo generar predicción'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
        except Exception as e:
            logger.error(f"Error en predicción de maduración: {e}")
            return self.handle_error(e, "Error generando predicción")
    
    @action(detail=False, methods=['get'], url_path='info-modelo-ml')
    def info_modelo_ml(self, request):
        """
        Obtiene información sobre el modelo de ML cargado
        
        GET /api/polinizaciones/info-modelo-ml/
        """
        try:
            from ..services.ml_polinizacion_service import ml_polinizacion_service
            
            model_info = ml_polinizacion_service.get_model_info()
            
            return Response({
                'success': True,
                'modelo': model_info
            })
            
        except Exception as e:
            logger.error(f"Error obteniendo info del modelo: {e}")
            return self.handle_error(e, "Error obteniendo información del modelo")
    
    @action(detail=True, methods=['post'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Cambia el estado o progreso de una polinización
        
        POST /api/polinizaciones/{id}/cambiar-estado/
        Body: {
            "estado": "EN_PROCESO",  // Opcional
            "progreso": 50,          // Opcional
            "fecha_maduracion": "2025-01-15"  // Opcional, para cuando se finaliza
        }
        """
        try:
            polinizacion = self.get_object()
            estado = request.data.get('estado')
            progreso = request.data.get('progreso')
            fecha_maduracion = request.data.get('fecha_maduracion')
            
            # Validar que al menos uno de los campos esté presente
            if estado is None and progreso is None:
                return Response({
                    'error': 'Debe proporcionar estado o progreso'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar progreso si se proporciona
            if progreso is not None:
                try:
                    progreso = int(progreso)
                    if progreso < 0 or progreso > 100:
                        return Response({
                            'error': 'El progreso debe estar entre 0 y 100'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
                    polinizacion.progreso_polinizacion = progreso
                    polinizacion.actualizar_estado_por_progreso()
                    
                except ValueError:
                    return Response({
                        'error': 'El progreso debe ser un número entero'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Actualizar estado si se proporciona
            if estado:
                if estado not in ['INICIAL', 'EN_PROCESO', 'FINALIZADO']:
                    return Response({
                        'error': 'Estado inválido. Debe ser INICIAL, EN_PROCESO o FINALIZADO'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                polinizacion.estado_polinizacion = estado
                
                # Sincronizar progreso con estado
                if estado == 'INICIAL':
                    polinizacion.progreso_polinizacion = 0
                elif estado == 'FINALIZADO':
                    polinizacion.progreso_polinizacion = 100
                elif estado == 'EN_PROCESO' and polinizacion.progreso_polinizacion == 0:
                    polinizacion.progreso_polinizacion = 50
            
            # Actualizar fecha de maduración si se proporciona
            if fecha_maduracion:
                from django.utils.dateparse import parse_date
                fecha_obj = parse_date(fecha_maduracion)
                if fecha_obj:
                    polinizacion.fechamad = fecha_obj
                else:
                    return Response({
                        'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si se finaliza, asegurar que tenga fecha de maduración
            if polinizacion.estado_polinizacion == 'FINALIZADO' and not polinizacion.fechamad:
                from django.utils import timezone
                polinizacion.fechamad = timezone.now().date()
            
            polinizacion.save()
            
            # Crear notificación
            try:
                from ..services.notification_service import notification_service
                notification_service.crear_notificacion_polinizacion(
                    usuario=request.user,
                    polinizacion=polinizacion,
                    tipo='ESTADO_POLINIZACION_ACTUALIZADO'
                )
            except Exception as e:
                logger.warning(f"No se pudo crear notificación: {e}")
            
            serializer = self.get_serializer(polinizacion)
            return Response({
                'success': True,
                'message': 'Estado actualizado correctamente',
                'polinizacion': serializer.data
            })
            
        except Exception as e:
            logger.error(f"Error cambiando estado de polinización: {e}")
            return self.handle_error(e, "Error cambiando estado")
