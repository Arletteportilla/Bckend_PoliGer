from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import *
from .admin_config import (
    BaseModelAdmin, ColoredStatusMixin, LinkToRelatedMixin, 
    DateRangeMixin, ExportMixin
)

@admin.register(Genero)
class GeneroAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

@admin.register(Especie)
class EspecieAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'genero')
    list_filter = ('genero',)
    search_fields = ('nombre', 'genero__nombre')

@admin.register(Variedad)
class VariedadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'especie', 'temporada_inicio', 'temporada_polinizacion')
    list_filter = ('especie__genero', 'especie', 'temporada_inicio')
    search_fields = ('nombre', 'especie__nombre')

@admin.register(Ubicacion)
class UbicacionAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre', 'descripcion')

class SeguimientoGerminacionInline(admin.TabularInline):
    model = SeguimientoGerminacion
    extra = 1
    fields = ('fecha', 'etapa', 'cantidad_germinada', 'observaciones', 'responsable')
    
    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        # Establecer valores por defecto
        formset.form.base_fields['responsable'].initial = request.user
        return formset

@admin.register(SeguimientoGerminacion)
class SeguimientoGerminacionAdmin(BaseModelAdmin, ColoredStatusMixin, ExportMixin):
    list_display = ('germinacion_link', 'fecha', 'etapa_colored', 'cantidad_germinada', 'responsable')
    list_filter = ('etapa', 'fecha', 'responsable')
    search_fields = ('germinacion__codigo', 'germinacion__especie_variedad', 'observaciones')
    date_hierarchy = 'fecha'
    actions = ['export_as_csv']
    
    def germinacion_link(self, obj):
        """Enlace a la germinación relacionada"""
        if obj.germinacion:
            return format_html(
                '<a href="/admin/laboratorio/germinacion/{}/change/">{}</a>',
                obj.germinacion.id,
                obj.germinacion.codigo or f"Germinación {obj.germinacion.id}"
            )
        return '-'
    germinacion_link.short_description = 'Germinación'
    
    def etapa_colored(self, obj):
        """Mostrar etapa con colores"""
        color_map = {
            'SIEMBRA': '#8B4513',      # Marrón
            'GERMINACION': '#32CD32',   # Verde lima
            'CRECIMIENTO': '#228B22',   # Verde bosque
            'TRASPLANTE': '#4169E1',    # Azul real
        }
        color = color_map.get(obj.etapa, '#000000')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_etapa_display()
        )
    etapa_colored.short_description = 'Etapa'
    
    def save_model(self, request, obj, form, change):
        if not obj.responsable:
            obj.responsable = request.user
        if not obj.fecha:
            obj.fecha = timezone.now().date()
        super().save_model(request, obj, form, change)

@admin.register(Germinacion)
class GerminacionAdmin(BaseModelAdmin, ColoredStatusMixin, ExportMixin):
    list_display = ('codigo', 'especie_variedad', 'fecha_siembra', 'estado_colored', 'responsable', 'seguimientos_count')
    list_filter = ('estado_capsula', 'fecha_siembra', 'responsable', 'genero')
    search_fields = ('codigo', 'especie_variedad', 'genero', 'observaciones')
    inlines = [SeguimientoGerminacionInline]
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'creado_por')
    date_hierarchy = 'fecha_siembra'
    actions = ['export_as_csv']
    
    def estado_colored(self, obj):
        """Mostrar estado con colores"""
        if obj.estado_capsula:
            color_map = {
                'CERRADA': '#DC143C',      # Rojo carmesí
                'ABIERTA': '#32CD32',      # Verde lima
                'SEMIABIERTA': '#FF8C00',  # Naranja oscuro
            }
            color = color_map.get(obj.estado_capsula, '#000000')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.get_estado_capsula_display()
            )
        return '-'
    estado_colored.short_description = 'Estado Cápsula'
    
    def seguimientos_count(self, obj):
        """Contar seguimientos"""
        count = obj.seguimientos.count()
        if count > 0:
            return format_html(
                '<a href="/admin/laboratorio/seguimientogerminacion/?germinacion__id__exact={}">{} seguimientos</a>',
                obj.id,
                count
            )
        return '0 seguimientos'
    seguimientos_count.short_description = 'Seguimientos'

@admin.register(Polinizacion)
class PolinizacionAdmin(BaseModelAdmin, ColoredStatusMixin, ExportMixin):
    list_display = [
        'numero', 'codigo', 'genero', 'especie', 'fechapol', 'fechamad', 'ubicacion_display', 'responsable', 'estado_colored', 'disponible'
    ]
    search_fields = ['codigo', 'genero', 'especie', 'ubicacion_nombre', 'responsable']
    list_filter = ['genero', 'especie', 'fechapol', 'fechamad', 'disponible', 'estado']
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion', 'creado_por', 'numero')
    date_hierarchy = 'fechapol'
    actions = ['export_as_csv']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('codigo', 'genero', 'especie', 'fechapol', 'fechamad', 'tipo_polinizacion')
        }),
        ('Ubicación y Responsable', {
            'fields': ('ubicacion_nombre', 'responsable', 'cantidad', 'disponible', 'estado', 'observaciones')
        }),
        ('Plantas Padre y Madre', {
            'fields': ('madre_codigo', 'madre_genero', 'madre_especie', 'padre_codigo', 'padre_genero', 'padre_especie'),
            'classes': ('collapse',)
        }),
        ('Nueva Planta', {
            'fields': ('nueva_codigo', 'nueva_genero', 'nueva_especie'),
            'classes': ('collapse',)
        }),
        ('Predicción', {
            'fields': ('prediccion_dias_estimados', 'prediccion_confianza', 'prediccion_fecha_estimada', 'prediccion_tipo'),
            'classes': ('collapse',)
        }),
        ('Sistema', {
            'fields': ('numero', 'fecha_creacion', 'fecha_actualizacion', 'creado_por'),
            'classes': ('collapse',)
        }),
    )
    
    def ubicacion_display(self, obj):
        """Mostrar ubicación de forma más clara"""
        return obj.ubicacion_nombre or obj.ubicacion or '-'
    ubicacion_display.short_description = 'Ubicación'
    
    def estado_colored(self, obj):
        """Mostrar estado con colores"""
        if obj.estado:
            color_map = {
                'ACTIVO': '#32CD32',       # Verde lima
                'INACTIVO': '#DC143C',     # Rojo carmesí
                'PENDIENTE': '#FF8C00',    # Naranja oscuro
                'EN_PROCESO': '#4169E1',   # Azul real
                'COMPLETADO': '#228B22',   # Verde bosque
            }
            color = color_map.get(obj.estado, '#000000')
            return format_html(
                '<span style="color: {}; font-weight: bold;">{}</span>',
                color,
                obj.estado
            )
        return '-'
    estado_colored.short_description = 'Estado'

@admin.register(Capsula)
class CapsulaAdmin(BaseModelAdmin):
    list_display = ('numero', 'germinacion', 'fecha_creacion')
    list_filter = ('fecha_creacion',)
    search_fields = ('germinacion__codigo', 'germinacion__especie_variedad')
    readonly_fields = ('numero', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(Siembra)
class SiembraAdmin(BaseModelAdmin):
    list_display = ('numero', 'germinacion', 'fecha_creacion')
    list_filter = ('fecha_creacion',)
    search_fields = ('germinacion__codigo', 'germinacion__especie_variedad')
    readonly_fields = ('numero', 'fecha_creacion', 'fecha_actualizacion')


@admin.register(PersonalUsuario)
class PersonalUsuarioAdmin(BaseModelAdmin):
    list_display = ('usuario', 'nombre', 'apellido', 'telefono')
    search_fields = ('usuario__username', 'nombre', 'apellido', 'telefono')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')


@admin.register(Inventario)
class InventarioAdmin(BaseModelAdmin):
    list_display = ('numero', 'germinacion')
    search_fields = ('germinacion__codigo', 'germinacion__especie_variedad')
    readonly_fields = ('numero',)


@admin.register(Notification)
class NotificationAdmin(BaseModelAdmin, ColoredStatusMixin):
    list_display = ('usuario', 'titulo', 'tipo_colored', 'leida', 'fecha_creacion')
    list_filter = ('tipo', 'leida', 'fecha_creacion')
    search_fields = ('usuario__username', 'titulo', 'mensaje')
    readonly_fields = ('fecha_creacion',)
    date_hierarchy = 'fecha_creacion'
    
    def tipo_colored(self, obj):
        """Mostrar tipo con colores"""
        color_map = {
            'INFO': '#17A2B8',         # Azul info
            'SUCCESS': '#28A745',      # Verde éxito
            'WARNING': '#FFC107',      # Amarillo advertencia
            'ERROR': '#DC3545',        # Rojo error
            'NUEVA_POLINIZACION': '#6F42C1',      # Púrpura
            'NUEVA_GERMINACION': '#20C997',       # Verde azulado
            'ESTADO_ACTUALIZADO': '#FD7E14',      # Naranja
        }
        color = color_map.get(obj.tipo, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_tipo_display() if hasattr(obj, 'get_tipo_display') else obj.tipo
        )
    tipo_colored.short_description = 'Tipo'


@admin.register(UserProfile)
class UserProfileAdmin(BaseModelAdmin, ColoredStatusMixin):
    list_display = ('user', 'rol_colored', 'activo', 'telefono', 'fecha_creacion')
    list_filter = ('rol', 'activo', 'fecha_creacion')
    search_fields = ('user__username', 'user__first_name', 'user__last_name', 'telefono')
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')
    
    fieldsets = (
        ('Usuario', {
            'fields': ('user', 'activo')
        }),
        ('Información Personal', {
            'fields': ('telefono', 'direccion', 'fecha_nacimiento', 'especialidad')
        }),
        ('Rol y Permisos', {
            'fields': ('rol',)
        }),
        ('Metas de Rendimiento', {
            'fields': ('meta_germinaciones_mes', 'meta_polinizaciones_mes', 'meta_eficiencia'),
            'classes': ('collapse',)
        }),
        ('Sistema', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def rol_colored(self, obj):
        """Mostrar rol con colores"""
        color_map = {
            'TIPO_1': '#28A745',       # Verde - Germinaciones
            'TIPO_2': '#007BFF',       # Azul - Polinizaciones  
            'TIPO_3': '#6F42C1',       # Púrpura - Ambos
            'TIPO_4': '#DC3545',       # Rojo - Administrador
        }
        color = color_map.get(obj.rol, '#6C757D')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_rol_display()
        )
    rol_colored.short_description = 'Rol'