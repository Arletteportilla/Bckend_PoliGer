"""
Configuraciones adicionales para el admin de Django
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe


class BaseModelAdmin(admin.ModelAdmin):
    """
    Clase base para todos los admins con configuraciones comunes
    """
    
    def save_model(self, request, obj, form, change):
        """Asignar automáticamente el usuario actual si no está asignado"""
        if hasattr(obj, 'creado_por') and not obj.creado_por:
            obj.creado_por = request.user
        if hasattr(obj, 'responsable') and not obj.responsable and hasattr(obj, '_meta'):
            # Solo para modelos que tienen campo responsable como CharField
            if any(field.name == 'responsable' and field.__class__.__name__ == 'CharField' 
                   for field in obj._meta.fields):
                full_name = f"{request.user.first_name} {request.user.last_name}".strip()
                obj.responsable = full_name if full_name else request.user.username
        super().save_model(request, obj, form, change)


class ImprovedListFilter(admin.SimpleListFilter):
    """
    Filtro mejorado que muestra conteos
    """
    
    def lookups(self, request, model_admin):
        """Sobrescribir para agregar conteos"""
        lookups = super().lookups(request, model_admin)
        if lookups:
            # Agregar conteos a cada opción
            counted_lookups = []
            for lookup in lookups:
                count = model_admin.get_queryset(request).filter(**{self.parameter_name: lookup[0]}).count()
                counted_lookups.append((lookup[0], f"{lookup[1]} ({count})"))
            return counted_lookups
        return lookups


class ColoredStatusMixin:
    """
    Mixin para agregar colores a los estados en el admin
    """
    
    def colored_status(self, obj):
        """Mostrar estado con colores"""
        if hasattr(obj, 'estado'):
            status = obj.estado
        elif hasattr(obj, 'estado_capsula'):
            status = obj.estado_capsula
        elif hasattr(obj, 'estado_capsulas'):
            status = obj.estado_capsulas
        else:
            return '-'
        
        color_map = {
            'ACTIVO': 'green',
            'INACTIVO': 'red',
            'PENDIENTE': 'orange',
            'EN_PROCESO': 'blue',
            'COMPLETADO': 'green',
            'CERRADA': 'red',
            'ABIERTA': 'green',
            'SEMIABIERTA': 'orange',
        }
        
        color = color_map.get(status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )
    
    colored_status.short_description = 'Estado'


class LinkToRelatedMixin:
    """
    Mixin para agregar enlaces a objetos relacionados
    """
    
    def link_to_related(self, obj, field_name, display_field='__str__'):
        """Crear enlace a objeto relacionado"""
        related_obj = getattr(obj, field_name, None)
        if related_obj:
            url = reverse(
                f'admin:{related_obj._meta.app_label}_{related_obj._meta.model_name}_change',
                args=[related_obj.pk]
            )
            display_text = getattr(related_obj, display_field) if hasattr(related_obj, display_field) else str(related_obj)
            return format_html('<a href="{}">{}</a>', url, display_text)
        return '-'


class DateRangeMixin:
    """
    Mixin para filtros de rango de fechas
    """
    
    def get_rangefilter_created_at_title(self):
        return 'Fecha de creación'
    
    def get_rangefilter_updated_at_title(self):
        return 'Fecha de actualización'


class ExportMixin:
    """
    Mixin para exportar datos
    """
    
    def export_as_csv(self, request, queryset):
        """Exportar como CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{self.model._meta.verbose_name_plural}.csv"'
        
        writer = csv.writer(response)
        
        # Escribir encabezados
        field_names = [field.verbose_name for field in self.model._meta.fields]
        writer.writerow(field_names)
        
        # Escribir datos
        for obj in queryset:
            row = []
            for field in self.model._meta.fields:
                value = getattr(obj, field.name)
                if value is None:
                    value = ''
                row.append(str(value))
            writer.writerow(row)
        
        return response
    
    export_as_csv.short_description = "Exportar seleccionados como CSV"


class AdminSiteConfig:
    """
    Configuración global del sitio admin
    """
    
    @staticmethod
    def configure_admin_site():
        """Configurar el sitio admin"""
        admin.site.site_header = "PoliGer - Administración"
        admin.site.site_title = "PoliGer Admin"
        admin.site.index_title = "Panel de Administración"
        
        # Personalizar templates si es necesario
        admin.site.enable_nav_sidebar = True


# Aplicar configuración
AdminSiteConfig.configure_admin_site()