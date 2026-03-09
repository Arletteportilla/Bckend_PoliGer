"""
Vistas para Polinizaciones usando servicios de negocio
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.db.models import Q, Count
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.conf import settings
from datetime import timedelta
import csv
import io
import os
import re
import logging

from ..models import Polinizacion, Germinacion
from ..serializers import PolinizacionSerializer
from ..api.serializers import PolinizacionHistoricaSerializer
from ..services.polinizacion_service import polinizacion_service
from ..permissions import CanViewPolinizaciones, CanCreatePolinizaciones, CanEditPolinizaciones, RoleBasedViewSetMixin
from .base_views import BaseServiceViewSet, ErrorHandlerMixin, SearchMixin
from ..renderers import BinaryFileRenderer
from ..core.models import UserProfile

logger = logging.getLogger(__name__)


class PolinizacionViewSet(RoleBasedViewSetMixin, BaseServiceViewSet, ErrorHandlerMixin, SearchMixin):
    """
    ViewSet para Polinizaciones usando servicios de negocio
    """
    queryset = Polinizacion.objects.all()
    serializer_class = PolinizacionSerializer
    service_class = type(polinizacion_service)
    # NO definir permission_classes aquí - dejar que RoleBasedViewSetMixin lo maneje
    
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
        'polinizaciones_pdf': CanViewPolinizaciones,
        'mis_polinizaciones_pdf': CanViewPolinizaciones,
        'alertas_polinizacion': CanViewPolinizaciones,
        'filter_options': CanViewPolinizaciones,
        'codigos_nuevas_plantas': CanViewPolinizaciones,
        'codigos_con_especies': CanViewPolinizaciones,
        'buscar_por_codigo': CanViewPolinizaciones,
        'buscar_planta_info': CanViewPolinizaciones,
        'buscar_genero_por_especie': CanViewPolinizaciones,
        'viveros': CanViewPolinizaciones,
        'mesas': CanViewPolinizaciones,
        'paredes': CanViewPolinizaciones,
        'opciones_ubicacion': CanViewPolinizaciones,
        'marcar_revisado': CanEditPolinizaciones,
        'pendientes_revision': CanViewPolinizaciones,
        'predecir_maduracion': CanViewPolinizaciones,
        'info_modelo_ml': CanViewPolinizaciones,
        'cambiar_estado': CanEditPolinizaciones,
        'generar_predicciones_usuario': CanEditPolinizaciones,
        'validar_prediccion': CanEditPolinizaciones,
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

            # Nota: la notificacion NUEVA_POLINIZACION la genera el signal post_save en signals.py

            # Verificar si ya debe enviarse recordatorio de 5 dias
            # (para casos donde la fecha ingresada ya tiene mas de 5 dias)
            try:
                from ..services.recordatorio_service import recordatorio_service
                enviado = recordatorio_service.verificar_y_notificar_polinizacion(polinizacion)
                if enviado:
                    logger.info(f"Recordatorio inmediato enviado para polinizacion {polinizacion.numero}")
            except Exception as e:
                logger.warning(f"No se pudo enviar recordatorio para polinizacion {polinizacion.numero}: {e}")

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
                excluir_importadas = True   # Por defecto, excluir importadas (comportamiento actual)
                solo_historicos = False
            
            logger.info(f"Obteniendo mis polinizaciones para usuario: {request.user.username}, página: {page}, días recientes: {dias_recientes}, tipo_registro: {tipo_registro}")
            
            # Si se solicita paginación, usar método paginado
            if request.GET.get('paginated', 'false').lower() == 'true' or page_size < 1000:
                logger.info("Usando método paginado")
                try:
                    result = self.service.get_mis_polinizaciones_paginated(
                        user=request.user,
                        page=page,
                        page_size=page_size,
                        search=search,
                        dias_recientes=dias_recientes,
                        excluir_importadas=excluir_importadas,
                        solo_historicos=solo_historicos if tipo_registro == 'historicos' else False
                    )
                    
                    logger.info(f"Resultado paginado obtenido: {result['count']} registros")
                    
                    # Usar serializer diferente según el tipo de registro
                    if tipo_registro == 'historicos':
                        # Para registros históricos, usar serializer sin estados
                        serializer = PolinizacionHistoricaSerializer(result['results'], many=True)
                        logger.info("Usando PolinizacionHistoricaSerializer (sin estados)")
                    else:
                        # Para registros nuevos o todos, usar serializer completo
                        serializer = self.get_serializer(result['results'], many=True)
                        logger.info("Usando PolinizacionSerializer completo (con estados)")
                    
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
                    raise
            else:
                # Sin paginación (compatibilidad hacia atrás)
                logger.info("Usando método sin paginación")
                polinizaciones = self.service.get_mis_polinizaciones(
                    user=request.user,
                    search=search,
                    dias_recientes=dias_recientes
                )
                
                # Usar serializer diferente según el tipo de registro
                if tipo_registro == 'historicos':
                    # Para registros históricos, usar serializer sin estados
                    serializer = PolinizacionHistoricaSerializer(polinizaciones, many=True)
                    logger.info("Usando PolinizacionHistoricaSerializer (sin estados)")
                else:
                    # Para registros nuevos o todos, usar serializer completo
                    serializer = self.get_serializer(polinizaciones, many=True)
                    logger.info("Usando PolinizacionSerializer completo (con estados)")
                
                logger.info(f"Retornando {len(serializer.data)} polinizaciones")
                return Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error general en mis_polinizaciones: {e}")
            return self.handle_error(e, "Error obteniendo mis polinizaciones")
    
    @action(detail=False, methods=['get'], url_path='todas-admin')
    def todas_admin(self, request):
        """Obtiene TODAS las polinizaciones para administradores"""
        try:
            user = request.user
            
            # Verificar que sea administrador
            if not hasattr(user, 'profile') or user.profile.rol != UserProfile.Roles.SYSTEM_MANAGER:
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
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch, cm
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT
            from datetime import datetime

            # Crear respuesta HTTP para PDF
            response = HttpResponse(content_type='application/pdf')
            search_text = f"_busqueda_{search}" if search else ""
            filename = f"polinizaciones_{request.user.username}_{datetime.now().strftime('%Y%m%d')}{search_text}.pdf"
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache'

            # Función para agregar cabecera/pie de página en cada página
            def add_page_footer(canvas, doc):
                canvas.saveState()
                page_width, page_height = landscape(A4)
                # Franja azul superior
                canvas.setFillColor(colors.HexColor('#1e3a8a'))
                canvas.rect(0, page_height - 4, page_width, 4, fill=1, stroke=0)
                # Pie de página
                footer_text = "PoliGer \u2014 Sistema de Gestión de Laboratorio | Generado automáticamente"
                canvas.setFont('Helvetica', 8)
                canvas.setFillColor(colors.HexColor('#1e3a8a'))
                canvas.drawCentredString(page_width / 2, 0.5 * cm, footer_text)
                canvas.setFont('Helvetica-Bold', 8)
                canvas.drawRightString(page_width - 1 * cm, 0.5 * cm, f"Pág. {doc.page}")
                canvas.restoreState()

            # Crear PDF en modo landscape A4 para más columnas
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=0.5*inch, bottomMargin=1*cm)

            # Contenedor de elementos
            elements = []
            styles = getSampleStyleSheet()

            # ─── ENCABEZADO ──────────────────────────────────────────────────────────
            MESES_ES = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                        7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',11:'Noviembre',12:'Diciembre'}
            now = datetime.now()
            fecha_larga = f"{now.day} de {MESES_ES[now.month]}, {now.year}"
            report_id = f"POL-{now.strftime('%Y%m%d%H%M%S')}"

            fechas_pol = [p.fechapol for p in polinizaciones if p.fechapol]
            if fechas_pol:
                rango_datos = f"{min(fechas_pol).strftime('%d/%m/%Y')} \u2014 {max(fechas_pol).strftime('%d/%m/%Y')}"
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

            page_w = landscape(A4)[0]
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

            # Crear tabla de datos
            data = [['Código', 'Tipo', 'Fecha\nPolini.', 'Fecha\nMad.', 'Nueva\nGénero', 'Nueva\nEspecie', 'Ubicación', 'Cantidad\nSolicitada', 'Cantidad\nDisponible']]

            for pol in polinizaciones:
                data.append([
                    str(pol.codigo or pol.nueva_codigo or '')[:12],
                    str(pol.tipo_polinizacion or pol.Tipo or '')[:6],
                    pol.fechapol.strftime('%d/%m/%Y') if pol.fechapol else '',
                    pol.fechamad.strftime('%d/%m/%Y') if pol.fechamad else '-',
                    str(pol.nueva_genero or pol.madre_genero or pol.genero or '')[:10],
                    str(pol.nueva_especie or pol.madre_especie or pol.especie or '')[:15],
                    str(pol.ubicacion_nombre or pol.vivero or pol.ubicacion or '')[:10],
                    str(pol.cantidad_solicitada or '-'),
                    str(pol.cantidad_disponible or '-')
                ])

            # Crear tabla
            table = Table(data, colWidths=[0.95*inch, 0.55*inch, 0.75*inch, 0.75*inch, 0.9*inch, 1.2*inch, 0.8*inch, 0.75*inch, 0.75*inch])

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
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#EFF6FF')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#BFDBFE')),
                ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#1e3a8a')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 3),
                ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 1), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ]))

            elements.append(table)

            # ─── RESUMEN DE OPERACIÓN ────────────────────────────────────────────────
            total_completadas = sum(1 for pol in polinizaciones if pol.fechamad)
            total_pendientes = len(polinizaciones) - total_completadas
            total_registros = len(polinizaciones)

            elements.append(Spacer(1, 20))
            elements.append(Paragraph('Resumen de Operación', ParagraphStyle('SecTitle',
                fontName='Helvetica-Bold', fontSize=13, textColor=colors.HexColor('#1e3a8a'), leading=16)))
            elements.append(Spacer(1, 10))

            card_w = usable_w / 3
            bar_inner_w = card_w - 28

            def _bar(ratio, fill_hex, bg_hex, width):
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

            ratio_comp = total_completadas / total_registros if total_registros else 0
            ratio_pend = total_pendientes / total_registros if total_registros else 0

            card1 = [
                Paragraph('COMPLETADAS', ParagraphStyle('c1l', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#1e3a8a'), leading=9)),
                Spacer(1, 4),
                Paragraph(str(total_completadas), ParagraphStyle('c1n', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#1e3a8a'), leading=15)),
                Spacer(1, 6),
                _bar(ratio_comp, '#1e3a8a', '#BFDBFE', bar_inner_w),
            ]
            card2 = [
                Paragraph('PENDIENTES', ParagraphStyle('c2l', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#b8860b'), leading=9)),
                Spacer(1, 4),
                Paragraph(str(total_pendientes), ParagraphStyle('c2n', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#b8860b'), leading=15)),
                Spacer(1, 6),
                _bar(ratio_pend, '#e9ad14', '#FDE68A', bar_inner_w),
            ]
            card3 = [
                Paragraph('TOTAL POLINIZACIONES', ParagraphStyle('c3l', fontName='Helvetica-Bold', fontSize=7, textColor=colors.HexColor('#1e3a8a'), leading=9)),
                Spacer(1, 4),
                Paragraph(f"{total_registros:,}".replace(',', '.'), ParagraphStyle('c3n', fontName='Helvetica-Bold', fontSize=12, textColor=colors.HexColor('#0F172A'), leading=15)),
            ]

            cards_table = Table([[card1, card2, card3]], colWidths=[card_w, card_w, card_w])
            cards_table.setStyle(TableStyle([
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
            elements.append(cards_table)
            # ─── FIN RESUMEN ─────────────────────────────────────────────────────────

            # Generar PDF con pie de página en cada página
            doc.build(elements, onFirstPage=add_page_footer, onLaterPages=add_page_footer)

            # Obtener PDF del buffer
            pdf_data = buffer.getvalue()
            buffer.close()

            response.write(pdf_data)
            logger.info(f"PDF generado exitosamente para {request.user.username}: {len(polinizaciones)} registros")
            # Notificación de descarga de PDF
            try:
                from ..services.notification_service import notification_service
                notification_service.crear_notificacion_sistema(
                    usuario=request.user,
                    tipo='ACTUALIZACION',
                    titulo=f'Descarga de PDF - Polinizaciones',
                    mensaje=f'Se descargó el PDF con {len(polinizaciones)} registro(s) de polinizaciones.',
                    detalles={'accion': 'descarga_pdf', 'tipo': 'polinizaciones', 'total': len(polinizaciones)}
                )
            except Exception as e:
                logger.warning(f"No se pudo crear notificacion de descarga PDF polinizaciones: {e}")
            return response

        except Exception as e:
            logger.exception(f"Error generando PDF: {e}")
            response = HttpResponse(
                f'Error generando PDF: {str(e)}',
                status=500,
                content_type='text/plain'
            )
            return response

    @action(detail=False, methods=['get'], url_path='alertas_polinizacion')
    def alertas_polinizacion(self, request):
        """Obtener alertas de polinizaciones próximas a madurar"""
        try:
            
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
        """Obtiene opciones para filtros de TODAS las polinizaciones del sistema"""
        try:

            user = request.user

            # Obtener queryset base - TODAS las polinizaciones del sistema
            queryset = Polinizacion.objects.all()
            logger.info(f"Obteniendo opciones de filtros para todas las polinizaciones del sistema")

            # Limitar resultados a 100 más comunes para evitar sobrecarga
            options = {
                'estados': list(queryset.exclude(estado='').values_list('estado', flat=True).distinct().order_by('estado')[:50]),
                'tipos_polinizacion': list(queryset.exclude(tipo_polinizacion='').values_list('tipo_polinizacion', flat=True).distinct().order_by('tipo_polinizacion')[:50]),
                'responsables': list(queryset.exclude(responsable='').values_list('responsable', flat=True).distinct().order_by('responsable')[:100]),
                'generos': list(queryset.exclude(genero='').values_list('genero', flat=True).distinct().order_by('genero')[:100]),
                'especies': list(queryset.exclude(especie='').values_list('especie', flat=True).distinct().order_by('especie')[:100]),
                'ubicacion_nombres': list(queryset.exclude(ubicacion_nombre='').values_list('ubicacion_nombre', flat=True).distinct().order_by('ubicacion_nombre')[:100]),
                'ubicacion_tipos': list(queryset.exclude(ubicacion_tipo='').values_list('ubicacion_tipo', flat=True).distinct().order_by('ubicacion_tipo')[:50]),
                # Nuevos campos de ubicación detallada
                'viveros': list(queryset.exclude(vivero='').values_list('vivero', flat=True).distinct().order_by('vivero')[:100]),
                'mesas': list(queryset.exclude(mesa='').values_list('mesa', flat=True).distinct().order_by('mesa')[:100]),
                'paredes': list(queryset.exclude(pared='').values_list('pared', flat=True).distinct().order_by('pared')[:100]),
            }

            # Usar aggregate para count en vez de queryset.count() separado
            total_count = queryset.aggregate(total=Count('numero'))['total']

            return Response({
                'opciones': options,
                'estadisticas': {
                    'total': total_count
                }
            })
        except Exception as e:
            return self.handle_error(e, "Error obteniendo opciones de filtro de polinizaciones")

    @action(detail=False, methods=['get'], url_path='buscar-genero-por-especie')
    def buscar_genero_por_especie(self, request):
        """
        Busca el género correspondiente a una especie en las polinizaciones.
        Útil para autocompletar el género en formularios de germinación.

        GET /api/polinizaciones/buscar-genero-por-especie/?especie=nombre_especie
        """
        try:
            especie = request.GET.get('especie', '').strip()

            if not especie:
                return Response({
                    'found': False,
                    'genero': None,
                    'message': 'Especie no proporcionada'
                })

            especie_lower = especie.lower()

            # Buscar en los diferentes campos de especie
            polinizacion = Polinizacion.objects.filter(
                Q(especie__iexact=especie) |
                Q(madre_especie__iexact=especie) |
                Q(padre_especie__iexact=especie) |
                Q(nueva_especie__iexact=especie)
            ).first()

            if polinizacion:
                # Determinar qué género devolver según el campo que coincidió
                genero = None
                if polinizacion.especie and polinizacion.especie.lower() == especie_lower:
                    genero = polinizacion.genero
                elif polinizacion.madre_especie and polinizacion.madre_especie.lower() == especie_lower:
                    genero = polinizacion.madre_genero
                elif polinizacion.padre_especie and polinizacion.padre_especie.lower() == especie_lower:
                    genero = polinizacion.padre_genero
                elif polinizacion.nueva_especie and polinizacion.nueva_especie.lower() == especie_lower:
                    genero = polinizacion.nueva_genero

                if genero:
                    return Response({
                        'found': True,
                        'genero': genero,
                        'especie': especie,
                        'message': 'Genero encontrado'
                    })

            return Response({
                'found': False,
                'genero': None,
                'especie': especie,
                'message': 'No se encontro genero para esta especie'
            })

        except Exception as e:
            logger.error(f"Error buscando genero por especie: {e}")
            return self.handle_error(e, "Error buscando genero por especie")

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
        """Obtiene todas las opciones de ubicación (viveros, mesas, paredes) en una sola llamada - limitado para performance"""
        try:

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

            # Limitar a 200 opciones cada uno para no sobrecargar
            # Obtener viveros
            viveros = list(Polinizacion.objects.exclude(vivero='').values_list('vivero', flat=True).distinct()[:200])
            viveros.sort(key=ordenar_codigo)

            # Obtener mesas
            mesas = list(Polinizacion.objects.exclude(mesa='').values_list('mesa', flat=True).distinct()[:200])
            mesas.sort(key=ordenar_mesa)

            # Obtener paredes
            paredes = list(Polinizacion.objects.exclude(pared='').values_list('pared', flat=True).distinct()[:200])
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
            from datetime import datetime
            
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

            # Encabezado poliger ecuagenera
            p.setFont("Helvetica-Bold", 18)
            p.drawCentredString(width / 2, height - 30, "POLIGER ECUAGENERA")

            # Título
            p.setFont("Helvetica-Bold", 16)
            title = f"Mis Polinizaciones - {user.first_name} {user.last_name}".strip()
            if not title.endswith(user.username):
                title += f" ({user.username})"
            p.drawString(50, height - 60, title)
            
            if search:
                p.setFont("Helvetica", 12)
                p.drawString(50, height - 80, f"Filtro de búsqueda: {search}")
                y_position = height - 110
            else:
                y_position = height - 90
            
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
                estados_validos = ['INICIAL', 'EN_PROCESO', 'EN_PROCESO_TEMPRANO', 'EN_PROCESO_AVANZADO', 'FINALIZADO']
                if estado not in estados_validos:
                    return Response({
                        'error': f'Estado inválido. Debe ser uno de: {", ".join(estados_validos)}'
                    }, status=status.HTTP_400_BAD_REQUEST)

                polinizacion.estado_polinizacion = estado

                # Sincronizar progreso con estado
                if estado == 'INICIAL':
                    polinizacion.progreso_polinizacion = 0
                elif estado in ('EN_PROCESO', 'EN_PROCESO_TEMPRANO'):
                    if polinizacion.progreso_polinizacion < 35:
                        polinizacion.progreso_polinizacion = 35
                elif estado == 'EN_PROCESO_AVANZADO':
                    if polinizacion.progreso_polinizacion < 75:
                        polinizacion.progreso_polinizacion = 75
                elif estado == 'FINALIZADO':
                    polinizacion.progreso_polinizacion = 100
            
            # Actualizar fecha de maduración si se proporciona
            if fecha_maduracion:
                fecha_obj = parse_date(fecha_maduracion)
                if fecha_obj:
                    polinizacion.fechamad = fecha_obj
                else:
                    return Response({
                        'error': 'Formato de fecha inválido. Use YYYY-MM-DD'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si se finaliza, asegurar que tenga fecha de maduración
            if polinizacion.estado_polinizacion == 'FINALIZADO' and not polinizacion.fechamad:
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

    @action(detail=False, methods=['post'], url_path='generar-predicciones-usuario')
    def generar_predicciones_usuario(self, request):
        """
        Genera predicciones para todas las polinizaciones del usuario que no las tengan

        POST /api/polinizaciones/generar-predicciones-usuario/
        """
        try:
            from ..services.prediccion_service import prediccion_service
            from datetime import datetime, timedelta

            # Obtener polinizaciones del usuario que no tienen predicción
            polinizaciones = self.get_queryset().filter(
                creado_por=request.user,
                prediccion_fecha_estimada__isnull=True,
                fechamad__isnull=True  # Solo las que no han madurado
            )

            logger.info(f"Generando predicciones para {polinizaciones.count()} polinizaciones de {request.user.username}")

            predicciones_generadas = 0
            errores = 0

            for polinizacion in polinizaciones:
                try:
                    # Preparar datos para predicción
                    data = {
                        'especie': polinizacion.especie or polinizacion.nueva_especie or polinizacion.madre_especie or '',
                        'genero': polinizacion.genero or polinizacion.nueva_genero or polinizacion.madre_genero or '',
                        'clima': polinizacion.nueva_clima or polinizacion.madre_clima or 'I',
                        'fecha_polinizacion': polinizacion.fechapol or datetime.now().date(),
                        'ubicacion': polinizacion.ubicacion or polinizacion.ubicacion_nombre or 'laboratorio',
                        'tipo_polinizacion': polinizacion.tipo_polinizacion or polinizacion.tipo or 'SELF'
                    }

                    # Calcular predicción
                    prediccion = prediccion_service.calcular_prediccion_polinizacion(data)

                    # Guardar predicción en el modelo
                    polinizacion.prediccion_dias_estimados = prediccion['dias_estimados']
                    polinizacion.prediccion_fecha_estimada = prediccion['fecha_estimada_semillas']
                    polinizacion.prediccion_confianza = prediccion['confianza']
                    polinizacion.prediccion_tipo = prediccion['tipo_prediccion']
                    polinizacion.prediccion_condiciones_climaticas = prediccion.get('condiciones_climaticas', {})
                    polinizacion.prediccion_especie_info = prediccion.get('especie_info', '')
                    polinizacion.prediccion_parametros_usados = prediccion.get('parametros_usados', {})

                    polinizacion.save()
                    predicciones_generadas += 1

                except Exception as e:
                    logger.error(f"Error generando predicción para polinización {polinizacion.numero}: {e}")
                    errores += 1
                    continue

            return Response({
                'success': True,
                'message': f'Predicciones generadas exitosamente',
                'predicciones_generadas': predicciones_generadas,
                'errores': errores,
                'total_procesadas': polinizaciones.count()
            })

        except Exception as e:
            logger.error(f"Error generando predicciones masivas: {e}")
            return self.handle_error(e, "Error generando predicciones")

    @action(detail=True, methods=['post'], url_path='validar-prediccion')
    def validar_prediccion(self, request, pk=None):
        """
        Valida la predicción de maduración comparando con la fecha real

        POST /api/polinizaciones/{id}/validar-prediccion/
        Body: { "fecha_maduracion_real": "YYYY-MM-DD" }
        """
        try:
            polinizacion = self.get_object()
            fecha_real_str = request.data.get('fecha_maduracion_real')

            if not fecha_real_str:
                return Response(
                    {'error': 'El campo fecha_maduracion_real es requerido'},
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

            # Obtener fecha predicha (usar el campo de predicción ML si existe)
            fecha_predicha = (
                polinizacion.fecha_maduracion_predicha or
                polinizacion.prediccion_fecha_estimada
            )

            dias_reales = None
            dias_predichos = None
            diferencia_dias = None
            precision = None
            desviacion_porcentual = None
            calidad = 'sin_datos'

            if polinizacion.fechapol:
                dias_reales = (fecha_real - polinizacion.fechapol).days

            if fecha_predicha:
                dias_predichos = (
                    polinizacion.dias_maduracion_predichos or
                    polinizacion.prediccion_dias_estimados or
                    (fecha_predicha - polinizacion.fechapol).days if polinizacion.fechapol else None
                )
                diferencia_dias = abs((fecha_real - fecha_predicha).days)

                if dias_predichos and dias_predichos > 0:
                    precision = max(0.0, 100 - (diferencia_dias / dias_predichos * 100))
                    desviacion_porcentual = round(diferencia_dias / dias_predichos * 100, 2)
                else:
                    precision = max(0.0, 100 - diferencia_dias * 2)
                    desviacion_porcentual = None

                if diferencia_dias <= 3:
                    calidad = 'Excelente'
                elif diferencia_dias <= 7:
                    calidad = 'Buena'
                elif diferencia_dias <= 14:
                    calidad = 'Aceptable'
                else:
                    calidad = 'Pobre'

            logger.info(
                f"Predicción validada para polinización {polinizacion.numero}: "
                f"precision={precision}, calidad={calidad}"
            )

            return Response({
                'success': True,
                'mensaje': 'Predicción validada exitosamente',
                'validacion': {
                    'fecha_predicha': str(fecha_predicha) if fecha_predicha else None,
                    'fecha_real': fecha_real_str,
                    'diferencia_dias': diferencia_dias,
                    'precision': round(precision, 1) if precision is not None else None,
                    'calidad': calidad,
                    'dias_estimados': dias_predichos,
                    'dias_reales': dias_reales,
                    'desviacion_porcentual': desviacion_porcentual,
                }
            })

        except Exception as e:
            logger.error(f"Error validando predicción de polinización {pk}: {e}")
            return self.handle_error(e, "Error validando predicción")
