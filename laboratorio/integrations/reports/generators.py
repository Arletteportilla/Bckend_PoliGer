"""
Generador de reportes para el sistema de laboratorio
"""
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, LineChart, Reference, PieChart
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from datetime import datetime, timedelta
import io
from .models import Germinacion, Polinizacion
from django.db.models import Count
from django.db.models.functions import TruncMonth


class ReportGenerator:
    """Generador de reportes en Excel y PDF"""
    
    def __init__(self):
        self.font_header = Font(bold=True, color="FFFFFF")
        self.fill_header = PatternFill(start_color="4A6CF7", end_color="4A6CF7", fill_type="solid")
        self.alignment_center = Alignment(horizontal="center", vertical="center")
        self.border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
    
    def safe_get_value(self, obj, field_name, default=''):
        """Obtener valor de forma segura"""
        try:
            value = getattr(obj, field_name, default)
            return value if value is not None else default
        except:
            return default
    
    def format_date(self, date_value):
        """Formatear fecha de forma segura"""
        if date_value is None:
            return ''
        try:
            if hasattr(date_value, 'replace'):
                date_value = date_value.replace(tzinfo=None)
            return date_value.strftime('%Y-%m-%d') if date_value else ''
        except:
            return ''

    def generate_excel_report(self, data_type, filters=None):
        """Genera reporte Excel básico"""
        try:
            # Crear workbook
            wb = Workbook()
            ws = wb.active
            
            if data_type == 'polinizaciones':
                return self._generate_polinizaciones_excel(ws, wb, filters)
            elif data_type == 'germinaciones':
                return self._generate_germinaciones_excel(ws, wb, filters)
            else:
                raise ValueError(f"Tipo de datos no soportado: {data_type}")
                
        except Exception as e:
            print(f"Error generando reporte Excel: {e}")
            raise

    def generate_pdf_report(self, data_type, filters=None):
        """Genera reporte PDF básico"""
        try:
            if data_type == 'polinizaciones':
                return self._generate_polinizaciones_pdf(filters)
            elif data_type == 'germinaciones':
                return self._generate_germinaciones_pdf(filters)
            else:
                raise ValueError(f"Tipo de datos no soportado: {data_type}")
                
        except Exception as e:
            print(f"Error generando reporte PDF: {e}")
            raise

    def _get_filtered_polinizaciones(self, filters=None):
        """Obtiene polinizaciones filtradas"""
        print(f"🔍 _get_filtered_polinizaciones - Filtros recibidos: {filters}")
        queryset = Polinizacion.objects.all()
        
        if filters:
            # Filtro por usuario actual
            if filters.get('usuario_actual'):
                from django.contrib.auth.models import User
                from django.db.models import Q
                username = filters['usuario_actual']
                print(f"🔍 Filtrando por usuario: {username}")
                
                try:
                    user = User.objects.get(username=username)
                    print(f"✅ Usuario encontrado: {user.username} (ID: {user.id})")
                    
                    # Filtrar por creado_por o por responsable como fallback
                    queryset = queryset.filter(
                        Q(creado_por=user) |
                        Q(responsable__iexact=username) |
                        Q(responsable__icontains=f"{user.first_name} {user.last_name}".strip())
                    )
                    print(f"✅ Polinizaciones encontradas después del filtro de usuario: {queryset.count()}")
                except User.DoesNotExist:
                    print(f"❌ Usuario no encontrado: {username}")
                    # Si no se encuentra el usuario, devolver queryset vacío
                    queryset = queryset.none()
            
            # Filtro de búsqueda
            if filters.get('search'):
                from django.db.models import Q
                search = filters['search']
                queryset = queryset.filter(
                    Q(codigo__icontains=search) |
                    Q(genero__icontains=search) |
                    Q(especie__icontains=search) |
                    Q(madre_genero__icontains=search) |
                    Q(madre_especie__icontains=search) |
                    Q(padre_genero__icontains=search) |
                    Q(padre_especie__icontains=search) |
                    Q(nueva_genero__icontains=search) |
                    Q(nueva_especie__icontains=search) |
                    Q(ubicacion_nombre__icontains=search) |
                    Q(observaciones__icontains=search)
                )
            
            # Otros filtros
            if filters.get('fecha_inicio'):
                queryset = queryset.filter(fechapol__gte=filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                queryset = queryset.filter(fechapol__lte=filters['fecha_fin'])
            if filters.get('estado'):
                queryset = queryset.filter(estado=filters['estado'])
        
        return queryset.order_by('-fecha_creacion')

    def _get_filtered_germinaciones(self, filters=None):
        """Obtiene germinaciones filtradas"""
        print(f"🔍 _get_filtered_germinaciones - Filtros recibidos: {filters}")
        queryset = Germinacion.objects.all()
        
        if filters:
            # Filtro por usuario actual
            if filters.get('usuario_actual'):
                from django.contrib.auth.models import User
                from django.db.models import Q
                username = filters['usuario_actual']
                print(f"🔍 Filtrando por usuario: {username}")
                
                try:
                    user = User.objects.get(username=username)
                    print(f"✅ Usuario encontrado: {user.username} (ID: {user.id})")
                    
                    # Filtrar por creado_por o por responsable como fallback
                    queryset = queryset.filter(
                        Q(creado_por=user) |
                        Q(responsable__iexact=username) |
                        Q(responsable__icontains=f"{user.first_name} {user.last_name}".strip())
                    )
                    print(f"✅ Germinaciones encontradas después del filtro de usuario: {queryset.count()}")
                except User.DoesNotExist:
                    print(f"❌ Usuario no encontrado: {username}")
                    # Si no se encuentra el usuario, devolver queryset vacío
                    queryset = queryset.none()
            
            # Filtro de búsqueda
            if filters.get('search'):
                from django.db.models import Q
                search = filters['search']
                queryset = queryset.filter(
                    Q(codigo__icontains=search) |
                    Q(genero__icontains=search) |
                    Q(especie_variedad__icontains=search) |
                    Q(percha__icontains=search) |
                    Q(nivel__icontains=search) |
                    Q(observaciones__icontains=search) |
                    Q(responsable__icontains=search)
                )
            
            # Otros filtros
            if filters.get('fecha_inicio'):
                queryset = queryset.filter(fecha_siembra__gte=filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                queryset = queryset.filter(fecha_siembra__lte=filters['fecha_fin'])
            if filters.get('etapa'):
                queryset = queryset.filter(etapa_actual=filters['etapa'])
        
        return queryset.order_by('-fecha_creacion')

    def _generate_polinizaciones_excel(self, ws, wb, filters=None):
        """Genera Excel de polinizaciones"""
        ws.title = "Polinizaciones"
        
        # Obtener datos filtrados
        polinizaciones = self._get_filtered_polinizaciones(filters)
        
        # Encabezados
        headers = [
            'Código', 'Género', 'Especie', 'Tipo', 'Fecha Polinización',
            'Fecha Maduración', 'Estado', 'Cantidad', 'Ubicación', 'Responsable'
        ]
        
        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.font_header
            cell.fill = self.fill_header
            cell.alignment = self.alignment_center
            cell.border = self.border
        
        # Escribir datos
        for row, pol in enumerate(polinizaciones, 2):
            ws.cell(row=row, column=1, value=self.safe_get_value(pol, 'codigo'))
            ws.cell(row=row, column=2, value=self.safe_get_value(pol, 'genero'))
            ws.cell(row=row, column=3, value=self.safe_get_value(pol, 'especie'))
            ws.cell(row=row, column=4, value=self.safe_get_value(pol, 'tipo_polinizacion'))
            ws.cell(row=row, column=5, value=self.format_date(pol.fechapol))
            ws.cell(row=row, column=6, value=self.format_date(pol.fechamad))
            ws.cell(row=row, column=7, value=self.safe_get_value(pol, 'estado'))
            ws.cell(row=row, column=8, value=self.safe_get_value(pol, 'cantidad_capsulas'))
            ws.cell(row=row, column=9, value=self.safe_get_value(pol, 'ubicacion_nombre'))
            ws.cell(row=row, column=10, value=self.safe_get_value(pol, 'responsable'))
        
        # Ajustar ancho de columnas
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15
        
        # Crear respuesta HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="polinizaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        # Guardar workbook en respuesta
        wb.save(response)
        return response

    def _generate_germinaciones_excel(self, ws, wb, filters=None):
        """Genera Excel de germinaciones"""
        ws.title = "Germinaciones"
        
        # Obtener datos filtrados
        germinaciones = self._get_filtered_germinaciones(filters)
        
        # Encabezados
        headers = [
            'Código', 'Género', 'Especie/Variedad', 'Fecha Siembra',
            'Ubicación', 'Cantidad Solicitada', 'No. Cápsulas',
            'Estado Cápsula', 'Estado Semilla', 'Responsable'
        ]

        # Escribir encabezados
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = self.font_header
            cell.fill = self.fill_header
            cell.alignment = self.alignment_center
            cell.border = self.border

        # Escribir datos
        for row, germ in enumerate(germinaciones, 2):
            # Construir ubicación concatenando percha y nivel
            percha = self.safe_get_value(germ, 'percha', '')
            nivel = self.safe_get_value(germ, 'nivel', '')
            ubicacion = f"{percha} {nivel}".strip() if percha or nivel else ''

            ws.cell(row=row, column=1, value=self.safe_get_value(germ, 'codigo'))
            ws.cell(row=row, column=2, value=self.safe_get_value(germ, 'genero'))
            ws.cell(row=row, column=3, value=self.safe_get_value(germ, 'especie_variedad'))
            ws.cell(row=row, column=4, value=self.format_date(germ.fecha_siembra))
            ws.cell(row=row, column=5, value=ubicacion)
            ws.cell(row=row, column=6, value=self.safe_get_value(germ, 'cantidad_solicitada'))
            ws.cell(row=row, column=7, value=self.safe_get_value(germ, 'no_capsulas'))
            ws.cell(row=row, column=8, value=self.safe_get_value(germ, 'estado_capsula'))
            ws.cell(row=row, column=9, value=self.safe_get_value(germ, 'estado_semilla'))
            ws.cell(row=row, column=10, value=self.safe_get_value(germ, 'responsable'))
        
        # Ajustar ancho de columnas
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 15
        
        # Crear respuesta HTTP
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="germinaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx"'
        
        # Guardar workbook en respuesta
        wb.save(response)
        return response

    def _generate_polinizaciones_pdf(self, filters=None):
        """Genera PDF de polinizaciones"""
        print(f"🔍 _generate_polinizaciones_pdf - Iniciando generación con filtros: {filters}")
        
        try:
            # Verificar que reportlab esté disponible
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            print("✅ ReportLab está disponible")
        except ImportError as e:
            print(f"❌ ReportLab no está disponible: {e}")
            raise ImportError("ReportLab no está instalado. Instala con: pip install reportlab")
        
        # Obtener datos filtrados
        polinizaciones = self._get_filtered_polinizaciones(filters)
        print(f"✅ Polinizaciones obtenidas para PDF: {polinizaciones.count()}")
        
        # Crear respuesta HTTP
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="polinizaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        # Crear PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Título
        p.setFont("Helvetica-Bold", 16)
        title = "Reporte de Polinizaciones"
        if filters and filters.get('usuario_actual'):
            title += f" - Usuario: {filters['usuario_actual']}"
        p.drawString(50, height - 50, title)
        
        # Información adicional
        y_position = height - 80
        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        p.drawString(50, y_position - 15, f"Total de registros: {polinizaciones.count()}")
        
        if filters and filters.get('search'):
            p.drawString(50, y_position - 30, f"Filtro de búsqueda: {filters['search']}")
            y_position -= 15
        
        y_position -= 50
        
        # Encabezados
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y_position, "Código")
        p.drawString(150, y_position, "Género")
        p.drawString(250, y_position, "Especie")
        p.drawString(350, y_position, "Fecha")
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

    def _generate_germinaciones_pdf(self, filters=None):
        """Genera PDF de germinaciones"""
        print(f"🔍 _generate_germinaciones_pdf - Iniciando generación con filtros: {filters}")
        
        try:
            # Verificar que reportlab esté disponible
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            print("✅ ReportLab está disponible")
        except ImportError as e:
            print(f"❌ ReportLab no está disponible: {e}")
            raise ImportError("ReportLab no está instalado. Instala con: pip install reportlab")
        
        # Obtener datos filtrados
        germinaciones = self._get_filtered_germinaciones(filters)
        print(f"✅ Germinaciones obtenidas para PDF: {germinaciones.count()}")
        
        # Crear respuesta HTTP
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="germinaciones_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf"'
        
        # Crear PDF
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Título
        p.setFont("Helvetica-Bold", 16)
        title = "Reporte de Germinaciones"
        if filters and filters.get('usuario_actual'):
            title += f" - Usuario: {filters['usuario_actual']}"
        p.drawString(50, height - 50, title)
        
        # Información adicional
        y_position = height - 80
        p.setFont("Helvetica", 10)
        p.drawString(50, y_position, f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        p.drawString(50, y_position - 15, f"Total de registros: {germinaciones.count()}")
        
        if filters and filters.get('search'):
            p.drawString(50, y_position - 30, f"Filtro de búsqueda: {filters['search']}")
            y_position -= 15
        
        y_position -= 50
        
        # Encabezados
        p.setFont("Helvetica-Bold", 10)
        p.drawString(50, y_position, "Código")
        p.drawString(150, y_position, "Género")
        p.drawString(250, y_position, "Especie")
        p.drawString(350, y_position, "Fecha")
        p.drawString(450, y_position, "Estado")
        
        y_position -= 20
        p.setFont("Helvetica", 9)
        
        # Datos
        for germ in germinaciones:
            if y_position < 50:  # Nueva página si no hay espacio
                p.showPage()
                y_position = height - 50
                p.setFont("Helvetica", 9)
            
            p.drawString(50, y_position, str(germ.codigo or '')[:15])
            p.drawString(150, y_position, str(germ.genero or '')[:15])
            p.drawString(250, y_position, str(germ.especie_variedad or '')[:15])
            p.drawString(350, y_position, str(germ.fecha_siembra or '')[:10])
            p.drawString(450, y_position, str(germ.etapa_actual or '')[:10])
            
            y_position -= 15
        
        p.save()
        
        # Obtener PDF del buffer
        pdf_data = buffer.getvalue()
        buffer.close()
        
        response.write(pdf_data)
        return response
    
    def generate_excel_report_with_stats(self, tipo, filters=None):
        """Genera reporte Excel con estadísticas y gráficos"""
        try:
            wb = Workbook()
            
            if tipo == 'germinaciones':
                ws_data = wb.active
                ws_data.title = "Datos Germinaciones"
                self._fill_germinaciones_data(ws_data, filters)
                
                ws_stats = wb.create_sheet("Estadísticas")
                self._generate_estadisticas_germinaciones_sheet(ws_stats)
                
                ws_charts = wb.create_sheet("Gráficos")
                self._generate_charts_germinaciones_sheet(ws_charts)
                
            elif tipo == 'polinizaciones':
                ws_data = wb.active
                ws_data.title = "Datos Polinizaciones"
                self._fill_polinizaciones_data(ws_data, filters)
                
                ws_stats = wb.create_sheet("Estadísticas")
                self._generate_estadisticas_polinizaciones_sheet(ws_stats)
                
                ws_charts = wb.create_sheet("Gráficos")
                self._generate_charts_polinizaciones_sheet(ws_charts)
                
            elif tipo == 'ambos':
                ws_germ = wb.active
                ws_germ.title = "Datos Germinaciones"
                self._fill_germinaciones_data(ws_germ, filters)
                
                ws_pol = wb.create_sheet("Datos Polinizaciones")
                self._fill_polinizaciones_data(ws_pol, filters)
                
                ws_stats = wb.create_sheet("Estadísticas Generales")
                self._generate_estadisticas_generales_sheet(ws_stats)
                
                ws_charts = wb.create_sheet("Gráficos Generales")
                self._generate_charts_generales_sheet(ws_charts)
            
            return self._create_excel_response(wb, f'{tipo}_con_estadisticas')
            
        except Exception as e:
            raise Exception(f"Error generando reporte: {str(e)}")

    def _fill_germinaciones_data(self, ws, filters):
        """Llena una hoja con datos de germinaciones"""
        queryset = Germinacion.objects.select_related('creado_por', 'polinizacion').all()
        
        if filters:
            if filters.get('fecha_inicio'):
                queryset = queryset.filter(fecha_creacion__gte=filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                queryset = queryset.filter(fecha_creacion__lte=filters['fecha_fin'])
        
        headers = [
            'ID', 'Código', 'Especie/Variedad', 'Fecha Polinización', 'Fecha Siembra',
            'Clima', 'Ubicación', 'Clima Lab', 'Cantidad Solicitada', 'No. Cápsulas',
            'Estado Cápsula', 'Estado Semilla', 'Cantidad Semilla', 'Semilla en Stock',
            'Observaciones', 'Responsable', 'Fecha Creación', 'Fecha Actualización',
            'Creado por', 'Fecha Germinación', 'Tipo Polinización', 'Etapa Actual'
        ]

        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)

        for row, germinacion in enumerate(queryset, 2):
            # Construir ubicación concatenando percha y nivel
            percha = self.safe_get_value(germinacion, 'percha', '')
            nivel = self.safe_get_value(germinacion, 'nivel', '')
            ubicacion = f"{percha} {nivel}".strip() if percha or nivel else ''

            ws.cell(row=row, column=1, value=self.safe_get_value(germinacion, 'id'))
            ws.cell(row=row, column=2, value=self.safe_get_value(germinacion, 'codigo'))
            ws.cell(row=row, column=3, value=self.safe_get_value(germinacion, 'especie_variedad'))
            ws.cell(row=row, column=4, value=self.format_date(self.safe_get_value(germinacion, 'fecha_polinizacion')))
            ws.cell(row=row, column=5, value=self.format_date(self.safe_get_value(germinacion, 'fecha_siembra')))
            ws.cell(row=row, column=6, value=self.safe_get_value(germinacion, 'clima'))
            ws.cell(row=row, column=7, value=ubicacion)
            ws.cell(row=row, column=8, value=self.safe_get_value(germinacion, 'clima_lab'))
            ws.cell(row=row, column=9, value=self.safe_get_value(germinacion, 'cantidad_solicitada'))
            ws.cell(row=row, column=10, value=self.safe_get_value(germinacion, 'no_capsulas'))
            ws.cell(row=row, column=11, value=self.safe_get_value(germinacion, 'estado_capsula'))
            ws.cell(row=row, column=12, value=self.safe_get_value(germinacion, 'estado_semilla'))
            ws.cell(row=row, column=13, value=self.safe_get_value(germinacion, 'cantidad_semilla'))
            ws.cell(row=row, column=14, value='Sí' if self.safe_get_value(germinacion, 'semilla_en_stock') else 'No')
            ws.cell(row=row, column=15, value=self.safe_get_value(germinacion, 'observaciones'))
            ws.cell(row=row, column=16, value=self.safe_get_value(germinacion, 'responsable'))
            ws.cell(row=row, column=17, value=self.format_date(self.safe_get_value(germinacion, 'fecha_creacion')))
            ws.cell(row=row, column=18, value=self.format_date(self.safe_get_value(germinacion, 'fecha_actualizacion')))
            ws.cell(row=row, column=19, value=self.safe_get_value(germinacion.creado_por, 'username') if germinacion.creado_por else '')
            ws.cell(row=row, column=20, value=self.format_date(self.safe_get_value(germinacion, 'fecha_germinacion')))
            ws.cell(row=row, column=21, value=self.safe_get_value(germinacion, 'tipo_polinizacion'))
            ws.cell(row=row, column=22, value=self.safe_get_value(germinacion, 'etapa_actual'))
        
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

    def _fill_polinizaciones_data(self, ws, filters):
        """Llena una hoja con datos de polinizaciones"""
        queryset = Polinizacion.objects.select_related('creado_por').all()
        
        if filters:
            if filters.get('fecha_inicio'):
                queryset = queryset.filter(fecha_creacion__gte=filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                queryset = queryset.filter(fecha_creacion__lte=filters['fecha_fin'])
        
        headers = [
            'Número', 'Código', 'Fecha Polinización', 'Fecha Maduración', 'Tipo Polinización',
            'Madre Código', 'Madre Género', 'Madre Clima', 'Madre Especie',
            'Padre Código', 'Padre Género', 'Padre Clima', 'Padre Especie',
            'Ubicación Tipo', 'Ubicación Nombre', 'Cantidad Cápsulas', 'Responsable',
            'Disponible', 'Estado', 'Fecha Creación', 'Fecha Actualización', 'Creado por'
        ]
        
        for col, header in enumerate(headers, 1):
            ws.cell(row=1, column=col, value=header)
        
        for row, polinizacion in enumerate(queryset, 2):
            ws.cell(row=row, column=1, value=self.safe_get_value(polinizacion, 'numero'))
            ws.cell(row=row, column=2, value=self.safe_get_value(polinizacion, 'codigo'))
            ws.cell(row=row, column=3, value=self.format_date(self.safe_get_value(polinizacion, 'fechapol')))
            ws.cell(row=row, column=4, value=self.format_date(self.safe_get_value(polinizacion, 'fechamad')))
            ws.cell(row=row, column=5, value=self.safe_get_value(polinizacion, 'tipo_polinizacion'))
            ws.cell(row=row, column=6, value=self.safe_get_value(polinizacion, 'madre_codigo'))
            ws.cell(row=row, column=7, value=self.safe_get_value(polinizacion, 'madre_genero'))
            ws.cell(row=row, column=8, value=self.safe_get_value(polinizacion, 'madre_clima'))
            ws.cell(row=row, column=9, value=self.safe_get_value(polinizacion, 'madre_especie'))
            ws.cell(row=row, column=10, value=self.safe_get_value(polinizacion, 'padre_codigo'))
            ws.cell(row=row, column=11, value=self.safe_get_value(polinizacion, 'padre_genero'))
            ws.cell(row=row, column=12, value=self.safe_get_value(polinizacion, 'padre_clima'))
            ws.cell(row=row, column=13, value=self.safe_get_value(polinizacion, 'padre_especie'))
            ws.cell(row=row, column=14, value=self.safe_get_value(polinizacion, 'ubicacion_tipo'))
            ws.cell(row=row, column=15, value=self.safe_get_value(polinizacion, 'ubicacion_nombre'))
            ws.cell(row=row, column=16, value=self.safe_get_value(polinizacion, 'cantidad_capsulas'))
            ws.cell(row=row, column=17, value=self.safe_get_value(polinizacion, 'responsable'))
            ws.cell(row=row, column=18, value='Sí' if self.safe_get_value(polinizacion, 'disponible') else 'No')
            ws.cell(row=row, column=19, value=self.safe_get_value(polinizacion, 'estado'))
            ws.cell(row=row, column=20, value=self.format_date(self.safe_get_value(polinizacion, 'fecha_creacion')))
            ws.cell(row=row, column=21, value=self.format_date(self.safe_get_value(polinizacion, 'fecha_actualizacion')))
            ws.cell(row=row, column=22, value=self.safe_get_value(polinizacion.creado_por, 'username') if polinizacion.creado_por else '')
        
        for col in range(1, len(headers) + 1):
            ws.column_dimensions[get_column_letter(col)].width = 18

    def _generate_estadisticas_germinaciones_sheet(self, ws):
        """Genera hoja de estadísticas para germinaciones"""
        ws.title = "Estadísticas Germinaciones"
        
        ws.cell(row=1, column=1, value="ESTADÍSTICAS DE GERMINACIONES")
        ws.cell(row=1, column=1).font = Font(bold=True, size=16)
        
        germinaciones = Germinacion.objects.all()
        total_germinaciones = germinaciones.count()
        
        row = 3
        ws.cell(row=row, column=1, value="Total de Germinaciones:")
        ws.cell(row=row, column=2, value=total_germinaciones)
        
        row += 1
        ws.cell(row=row, column=1, value="Germinaciones con Semilla en Stock:")
        ws.cell(row=row, column=2, value=germinaciones.filter(semilla_en_stock=True).count())
        
        row += 1
        ws.cell(row=row, column=1, value="Germinaciones sin Semilla en Stock:")
        ws.cell(row=row, column=2, value=germinaciones.filter(semilla_en_stock=False).count())
        
        ws.column_dimensions['A'].width = 30
        ws.column_dimensions['B'].width = 15

    def _generate_estadisticas_polinizaciones_sheet(self, ws):
        """Genera hoja de estadísticas para polinizaciones"""
        ws.title = "Estadísticas Polinizaciones"
        
        ws.cell(row=1, column=1, value="ESTADÍSTICAS DE POLINIZACIONES")
        ws.cell(row=1, column=1).font = Font(bold=True, size=16)
        
        polinizaciones = Polinizacion.objects.all()
        total_polinizaciones = polinizaciones.count()
        
        row = 3
        ws.cell(row=row, column=1, value="Total de Polinizaciones:")
        ws.cell(row=row, column=2, value=total_polinizaciones)
        
        row += 1
        ws.cell(row=row, column=1, value="Polinizaciones Disponibles:")
        ws.cell(row=row, column=2, value=polinizaciones.filter(disponible=True).count())
        
        row += 1
        ws.cell(row=row, column=1, value="Polinizaciones No Disponibles:")
        ws.cell(row=row, column=2, value=polinizaciones.filter(disponible=False).count())
        
        ws.column_dimensions['A'].width = 35
        ws.column_dimensions['B'].width = 15

    def _generate_estadisticas_generales_sheet(self, ws):
        """Genera hoja de estadísticas generales"""
        ws.title = "Estadísticas Generales"
        
        ws.cell(row=1, column=1, value="ESTADÍSTICAS GENERALES DEL SISTEMA")
        ws.cell(row=1, column=1).font = Font(bold=True, size=16)
        
        germinaciones = Germinacion.objects.all()
        polinizaciones = Polinizacion.objects.all()
        
        row = 3
        ws.cell(row=row, column=1, value="Total de Germinaciones:")
        ws.cell(row=row, column=2, value=germinaciones.count())
        
        row += 1
        ws.cell(row=row, column=1, value="Total de Polinizaciones:")
        ws.cell(row=row, column=2, value=polinizaciones.count())
        
        row += 1
        ws.cell(row=row, column=1, value="Total de Registros:")
        ws.cell(row=row, column=2, value=germinaciones.count() + polinizaciones.count())
        
        ws.column_dimensions['A'].width = 40
        ws.column_dimensions['B'].width = 15

    def _generate_charts_germinaciones_sheet(self, ws):
        """Genera hoja de gráficos para germinaciones"""
        ws.title = "Gráficos Germinaciones"
        
        ws.cell(row=1, column=1, value="GRÁFICOS DE GERMINACIONES")
        ws.cell(row=1, column=1).font = Font(bold=True, size=16)
        
        # Gráfico simple de distribución por etapa
        etapas = Germinacion.objects.values('etapa_actual').annotate(count=Count('id'))
        
        ws.cell(row=3, column=1, value="Distribución por Etapa")
        ws.cell(row=3, column=1).font = Font(bold=True, size=14)
        
        ws.cell(row=5, column=1, value="Etapa")
        ws.cell(row=5, column=2, value="Cantidad")
        
        row = 6
        for etapa in etapas:
            if etapa['etapa_actual']:
                ws.cell(row=row, column=1, value=etapa['etapa_actual'])
                ws.cell(row=row, column=2, value=etapa['count'])
                row += 1
        
        # Crear gráfico de barras
        chart = BarChart()
        chart.title = "Distribución por Etapa"
        chart.x_axis.title = "Etapa"
        chart.y_axis.title = "Cantidad"
        
        data = Reference(ws, min_col=2, min_row=5, max_row=row-1)
        cats = Reference(ws, min_col=1, min_row=6, max_row=row-1)
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        
        ws.add_chart(chart, "D10")

    def _generate_charts_polinizaciones_sheet(self, ws):
        """Genera hoja de gráficos para polinizaciones"""
        ws.title = "Gráficos Polinizaciones"
        
        ws.cell(row=1, column=1, value="GRÁFICOS DE POLINIZACIONES")
        ws.cell(row=1, column=1).font = Font(bold=True, size=16)
        
        # Gráfico simple de distribución por estado
        estados = Polinizacion.objects.values('estado').annotate(count=Count('id'))
        
        ws.cell(row=3, column=1, value="Distribución por Estado")
        ws.cell(row=3, column=1).font = Font(bold=True, size=14)
        
        ws.cell(row=5, column=1, value="Estado")
        ws.cell(row=5, column=2, value="Cantidad")
        
        row = 6
        for estado in estados:
            if estado['estado']:
                ws.cell(row=row, column=1, value=estado['estado'])
                ws.cell(row=row, column=2, value=estado['count'])
                row += 1
        
        # Crear gráfico de barras
        chart = BarChart()
        chart.title = "Distribución por Estado"
        chart.x_axis.title = "Estado"
        chart.y_axis.title = "Cantidad"
        
        data = Reference(ws, min_col=2, min_row=5, max_row=row-1)
        cats = Reference(ws, min_col=1, min_row=6, max_row=row-1)
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        
        ws.add_chart(chart, "D10")

    def _generate_charts_generales_sheet(self, ws):
        """Genera hoja de gráficos generales"""
        ws.title = "Gráficos Generales"
        
        ws.cell(row=1, column=1, value="GRÁFICOS GENERALES DEL SISTEMA")
        ws.cell(row=1, column=1).font = Font(bold=True, size=16)
        
        # Gráfico de comparación general
        total_germinaciones = Germinacion.objects.count()
        total_polinizaciones = Polinizacion.objects.count()
        
        ws.cell(row=3, column=1, value="Comparación Germinaciones vs Polinizaciones")
        ws.cell(row=3, column=1).font = Font(bold=True, size=14)
        
        ws.cell(row=5, column=1, value="Tipo")
        ws.cell(row=5, column=2, value="Cantidad")
        
        ws.cell(row=6, column=1, value="Germinaciones")
        ws.cell(row=6, column=2, value=total_germinaciones)
        
        ws.cell(row=7, column=1, value="Polinizaciones")
        ws.cell(row=7, column=2, value=total_polinizaciones)
        
        # Crear gráfico de barras
        chart = BarChart()
        chart.title = "Comparación General"
        chart.x_axis.title = "Tipo"
        chart.y_axis.title = "Cantidad"
        
        data = Reference(ws, min_col=2, min_row=5, max_row=7)
        cats = Reference(ws, min_col=1, min_row=6, max_row=7)
        
        chart.add_data(data, titles_from_data=True)
        chart.set_categories(cats)
        
        ws.add_chart(chart, "D10")

    def _create_excel_response(self, wb, report_type):
        """Crea respuesta HTTP para Excel"""
        excel_file = io.BytesIO()
        wb.save(excel_file)
        excel_file.seek(0)
        
        response = HttpResponse(
            excel_file.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        filename = f'reporte_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response

    def generate_pdf_report_with_stats(self, tipo, filters=None):
        """Genera reporte PDF con estadísticas"""
        try:
            buffer = io.BytesIO()
            p = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter
            
            p.setFont("Helvetica-Bold", 16)
            p.drawCentredString(width/2, height-50, f"REPORTE DE {tipo.upper()}")
            
            if tipo == 'germinaciones':
                queryset = Germinacion.objects.all()
                if filters:
                    if filters.get('fecha_inicio'):
                        queryset = queryset.filter(fecha_creacion__gte=filters['fecha_inicio'])
                    if filters.get('fecha_fin'):
                        queryset = queryset.filter(fecha_creacion__lte=filters['fecha_fin'])
                
                y_position = height - 100
                p.setFont("Helvetica-Bold", 12)
                p.drawString(50, y_position, "ESTADÍSTICAS DE GERMINACIONES")
                
                y_position -= 30
                p.setFont("Helvetica", 10)
                p.drawString(50, y_position, f"Total de Germinaciones: {queryset.count()}")
                
                y_position -= 20
                p.drawString(50, y_position, f"Con Semilla en Stock: {queryset.filter(semilla_en_stock=True).count()}")
                
                y_position -= 20
                p.drawString(50, y_position, f"Sin Semilla en Stock: {queryset.filter(semilla_en_stock=False).count()}")
                
            elif tipo == 'polinizaciones':
                queryset = Polinizacion.objects.all()
                if filters:
                    if filters.get('fecha_inicio'):
                        queryset = queryset.filter(fecha_creacion__gte=filters['fecha_inicio'])
                    if filters.get('fecha_fin'):
                        queryset = queryset.filter(fecha_creacion__lte=filters['fecha_fin'])
                
                y_position = height - 100
                p.setFont("Helvetica-Bold", 12)
                p.drawString(50, y_position, "ESTADÍSTICAS DE POLINIZACIONES")
                
                y_position -= 30
                p.setFont("Helvetica", 10)
                p.drawString(50, y_position, f"Total de Polinizaciones: {queryset.count()}")
                
                y_position -= 20
                p.drawString(50, y_position, f"Disponibles: {queryset.filter(disponible=True).count()}")
                
                y_position -= 20
                p.drawString(50, y_position, f"No Disponibles: {queryset.filter(disponible=False).count()}")
            
            p.showPage()
            p.save()
            
            buffer.seek(0)
            response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
            filename = f'reporte_{tipo}_con_estadisticas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            raise Exception(f"Error generando reporte PDF: {str(e)}")
