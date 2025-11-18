from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType

class Genero(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.nombre

class Especie(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    genero = models.ForeignKey(Genero, on_delete=models.CASCADE, related_name='especies')
    
    def __str__(self):
        return f"{self.genero} {self.nombre}"

class Variedad(models.Model):
    ESTACIONES = [
        ('PRIMAVERA', 'Primavera'),
        ('VERANO', 'Verano'),
        ('OTONO', 'Otoño'),
        ('INVIERNO', 'Invierno'),
    ]
    
    nombre = models.CharField(max_length=100, unique=True)
    especie = models.ForeignKey(Especie, on_delete=models.CASCADE, related_name='variedades')
    temporada_inicio = models.CharField(max_length=20, choices=ESTACIONES)
    temporada_polinizacion = models.CharField(max_length=20, choices=ESTACIONES)
    dias_germinacion_min = models.PositiveIntegerField(verbose_name='Días mínimos de germinación')
    dias_germinacion_max = models.PositiveIntegerField(verbose_name='Días máximos de germinación')
    
    def __str__(self):
        return self.nombre

class Ubicacion(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    
    def __str__(self):
        return self.nombre

class Polinizacion(models.Model):
    ESTADOS_POLINIZACION = [
        ('INGRESADO', 'Ingresado'),
        ('EN_PROCESO', 'En proceso'),
        ('LISTA', 'Lista'),
        ('LISTO', 'Listo'),
    ]
    
    TIPOS_POLINIZACION = [
        ('SELF', 'Self'),
        ('SIBLING', 'Sibling'),
        ('HIBRIDA', 'Híbrida'),
    ]
    
    UBICACIONES = [
        ('finca', 'Finca'),
        ('vivero', 'Vivero'),
        ('mesa', 'Mesa'),
        ('pared', 'Pared'),
    ]
    
    # Fechas
    fechapol = models.DateField(verbose_name='Fecha de polinización', null=True, blank=True)
    fechamad = models.DateField(verbose_name='Fecha de maduración', null=True, blank=True)
    
    # Tipo de polinización
    tipo_polinizacion = models.CharField(max_length=20, choices=TIPOS_POLINIZACION, verbose_name='Tipo de polinización', blank=True, default='SELF')
    
    # Planta madre
    madre_codigo = models.CharField(max_length=50, verbose_name='Código planta madre', default='', blank=True)
    madre_genero = models.CharField(max_length=100, verbose_name='Género planta madre', default='', blank=True)
    madre_clima = models.CharField(max_length=50, verbose_name='Clima planta madre', default='I', blank=True)
    madre_especie = models.CharField(max_length=100, verbose_name='Especie/Variedad planta madre', default='', blank=True)
    
    # Planta padre
    padre_codigo = models.CharField(max_length=50, verbose_name='Código planta padre', default='', blank=True)
    padre_genero = models.CharField(max_length=100, verbose_name='Género planta padre', default='', blank=True)
    padre_clima = models.CharField(max_length=50, verbose_name='Clima planta padre', default='I', blank=True)
    padre_especie = models.CharField(max_length=100, verbose_name='Especie/Variedad planta padre', default='', blank=True)
    
    # Nueva planta
    nueva_codigo = models.CharField(max_length=50, verbose_name='Código nueva planta', default='', blank=True)
    nueva_genero = models.CharField(max_length=100, verbose_name='Género nueva planta', default='', blank=True)
    nueva_clima = models.CharField(max_length=50, verbose_name='Clima nueva planta', default='I', blank=True)
    nueva_especie = models.CharField(max_length=100, verbose_name='Especie/Variedad nueva planta', default='', blank=True)
    
    # Ubicación
    ubicacion_tipo = models.CharField(max_length=20, choices=UBICACIONES, verbose_name='Tipo de ubicación', default='vivero', blank=True)
    ubicacion_nombre = models.CharField(max_length=100, verbose_name='Nombre de ubicación', default='', blank=True)
    
    # Cantidad
    cantidad_capsulas = models.PositiveIntegerField(verbose_name='Cantidad de cápsulas', default=1)
    
    # Campos del sistema
    numero = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=50, blank=True)
    responsable = models.CharField(max_length=100, blank=True)
    disponible = models.BooleanField(default=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_POLINIZACION, default='INGRESADO', verbose_name='Estado de la polinización')
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='polinizaciones_creadas', verbose_name='Creado por')
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True, blank=True)
    
    # Campos legacy para compatibilidad
    genero = models.CharField(max_length=100, blank=True)
    especie = models.CharField(max_length=255, blank=True)
    ubicacion = models.CharField(max_length=100, blank=True)

    # Campos de ubicación detallada
    vivero = models.CharField(max_length=50, blank=True, verbose_name='Vivero (ej: V-13)')
    mesa = models.CharField(max_length=50, blank=True, verbose_name='Mesa (ej: M-1A)')
    pared = models.CharField(max_length=50, blank=True, verbose_name='Pared (ej: P-C)')

    cantidad = models.PositiveIntegerField(default=1)
    archivo_origen = models.CharField(max_length=255, blank=True)
    observaciones = models.TextField(verbose_name='Observaciones', blank=True)
    
    # Campos de predicción
    prediccion_dias_estimados = models.PositiveIntegerField(verbose_name='Días estimados de predicción', null=True, blank=True)
    prediccion_confianza = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Confianza de predicción (%)', null=True, blank=True)
    prediccion_fecha_estimada = models.DateField(verbose_name='Fecha estimada de semillas', null=True, blank=True)
    prediccion_tipo = models.CharField(max_length=50, verbose_name='Tipo de predicción', blank=True)
    prediccion_condiciones_climaticas = models.TextField(verbose_name='Condiciones climáticas de predicción', blank=True)
    prediccion_especie_info = models.TextField(verbose_name='Información de especie de predicción', blank=True)
    prediccion_parametros_usados = models.TextField(verbose_name='Parámetros usados en predicción', blank=True)

    def save(self, *args, **kwargs):
        # Guarda primero para tener ID
        super().save(*args, **kwargs)
        # Ya no ejecuta predicción

    class Meta:
        indexes = [
            models.Index(fields=['fechapol']),
            models.Index(fields=['codigo']),
            models.Index(fields=['responsable']),
            models.Index(fields=['estado']),
            models.Index(fields=['creado_por']),
            models.Index(fields=['fecha_creacion']),
            models.Index(fields=['genero', 'especie']),  # Índice compuesto
        ]
        verbose_name = 'Polinización'
        verbose_name_plural = 'Polinizaciones'

    def __str__(self):
        return f"{self.codigo} - {self.genero} - {self.especie}"

class Germinacion(models.Model):
    ESTADOS_CAPSULAS = [
        ('ABIERTO', 'Abierto'),
        ('CERRADA', 'Cerrada'),
        ('SEMIABIERTA', 'Semiabierta'),
    ]
    
    class Meta:
        indexes = [
            models.Index(fields=['fecha_creacion']),
            models.Index(fields=['responsable']),
            models.Index(fields=['codigo']),
            models.Index(fields=['fecha_siembra']),
        ]
        verbose_name = 'Germinación'
        verbose_name_plural = 'Germinaciones'
    
    TIPOS_POLINIZACION = [
        ('HIBRIDA', 'Híbrida'),
        ('SELF', 'Self'),
        ('SIBLING', 'Sibling'),
    ]
    
    CLIMAS = [
        ('I', 'Intermedio'),
        ('IW', 'Intermedio Caliente'),
        ('IC', 'Intermedio Frío'),
        ('W', 'Frío'),
        ('C', 'Caliente'),
    ]
    
    UBICACIONES = [
        ('percha', 'Percha'),
        ('nivel_1', 'Nivel 1'),
        ('nivel_2', 'Nivel 2'),
        ('nivel_3', 'Nivel 3'),
        ('nivel_4', 'Nivel 4'),
        ('nivel_5', 'Nivel 5'),
    ]
    
    # Fechas
    fecha_polinizacion = models.DateField(verbose_name='Fecha de polinización', null=True, blank=True)
    fecha_siembra = models.DateField(verbose_name='Fecha de siembra', null=True, blank=True)
    
    # Información básica
    codigo = models.CharField(max_length=50, verbose_name='Código', null=True, blank=True, db_index=True)
    genero = models.CharField(max_length=100, verbose_name='Género', null=True, blank=True)
    especie_variedad = models.CharField(max_length=200, verbose_name='Especie/Variedad', null=True, blank=True)
    clima = models.CharField(max_length=20, choices=CLIMAS, verbose_name='Clima', default='I', null=True, blank=True)
    
    # Ubicación detallada
    percha = models.CharField(max_length=50, verbose_name='Percha', null=True, blank=True)
    nivel = models.CharField(max_length=10, verbose_name='Nivel', null=True, blank=True)
    clima_lab = models.CharField(max_length=20, choices=CLIMAS, verbose_name='Clima Lab', default='I', null=True, blank=True)
    
    # Cantidades
    cantidad_solicitada = models.PositiveIntegerField(verbose_name='Cantidad solicitada', default=0, null=True, blank=True)
    no_capsulas = models.PositiveIntegerField(verbose_name='Número de cápsulas', default=0, null=True, blank=True)
    
    # Estado de cápsula y semilla
    ESTADOS_CAPSULA = [
        ('CERRADA', 'Cerrada'),
        ('ABIERTA', 'Abierta'),
        ('SEMIABIERTA', 'Semiabierta'),
    ]
    
    ESTADOS_SEMILLA = [
        ('MADURA', 'Madura'),
        ('TIERNA', 'Tierna'),
        ('VANA', 'Vana'),
    ]
    
    CANTIDADES_SEMILLA = [
        ('ABUNDANTE', 'Abundante'),
        ('ESCASA', 'Escasa'),
    ]
    
    estado_capsula = models.CharField(max_length=20, choices=ESTADOS_CAPSULA, verbose_name='Estado Cápsula', default='CERRADA', null=True, blank=True)
    estado_semilla = models.CharField(max_length=20, choices=ESTADOS_SEMILLA, verbose_name='Semilla', default='MADURA', null=True, blank=True)
    cantidad_semilla = models.CharField(max_length=20, choices=CANTIDADES_SEMILLA, verbose_name='Cantid. Semilla', default='ABUNDANTE', null=True, blank=True)
    semilla_en_stock = models.BooleanField(verbose_name='Semilla en Stock', default=False)
    
    # Observaciones y responsable
    observaciones = models.TextField(verbose_name='Observaciones', null=True, blank=True)
    responsable = models.CharField(max_length=100, verbose_name='Responsable', null=True, blank=True)
    
    # Campos del sistema
    fecha_creacion = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True, null=True, blank=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='germinaciones_creadas', verbose_name='Creado por')
    
    # Campos legacy para compatibilidad
    fecha_germinacion = models.DateField(verbose_name='Fecha de germinación', null=True, blank=True)
    estado_capsulas = models.CharField(max_length=20, choices=ESTADOS_CAPSULAS, verbose_name='Estado de cápsulas', default='CERRADA', null=True, blank=True)
    tipo_polinizacion = models.CharField(max_length=20, choices=TIPOS_POLINIZACION, verbose_name='Tipo de polinización', null=True, blank=True)
    entrega_capsulas = models.CharField(max_length=255, verbose_name='Persona que entrega las cápsulas', null=True, blank=True)
    recibe_capsulas = models.CharField(max_length=255, verbose_name='Persona que recibe las cápsulas', null=True, blank=True)
    semilla_vana = models.PositiveIntegerField(verbose_name='Semilla vana', default=0, null=True, blank=True)
    semillas_stock = models.PositiveIntegerField(verbose_name='Semillas en stock', default=0, null=True, blank=True)
    disponibles = models.PositiveIntegerField(verbose_name='Disponibles', default=0, null=True, blank=True)
    
    # Campos legacy para compatibilidad (opcionales)
    fecha_ingreso = models.DateField(verbose_name='Fecha de ingreso', null=True, blank=True)
    dias_polinizacion = models.PositiveIntegerField(verbose_name='Días desde polinización', null=True, blank=True)
    nombre = models.CharField(max_length=255, verbose_name='Nombre del híbrido', null=True, blank=True)
    detalles_padres = models.TextField(verbose_name='Detalles de padres del híbrido', null=True, blank=True)
    finca = models.CharField(max_length=100, null=True, blank=True)
    numero_vivero = models.CharField(max_length=50, verbose_name='Número de vivero', null=True, blank=True)
    numero_capsulas = models.PositiveIntegerField(verbose_name='Número de cápsulas', null=True, blank=True)
    etapa_actual = models.CharField(max_length=100, choices=[
        ('INGRESADO', 'Ingresado'),
        ('EN_PROCESO', 'En proceso'),
        ('LISTA', 'Lista'),
        ('CANCELADO', 'Cancelado'),
    ], default='INGRESADO', null=True, blank=True)
    polinizacion = models.ForeignKey(Polinizacion, on_delete=models.CASCADE, related_name='germinaciones', null=True, blank=True)
    fecha_ultima_revision = models.DateTimeField(null=True, blank=True)
    
    # Campos de predicción
    prediccion_dias_estimados = models.PositiveIntegerField(verbose_name='Días estimados de predicción', null=True, blank=True)
    prediccion_confianza = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Confianza de predicción (%)', null=True, blank=True)
    prediccion_fecha_estimada = models.DateField(verbose_name='Fecha estimada de germinación', null=True, blank=True)
    prediccion_tipo = models.CharField(max_length=50, verbose_name='Tipo de predicción', blank=True)
    prediccion_condiciones_climaticas = models.TextField(verbose_name='Condiciones climáticas de predicción', blank=True)
    prediccion_especie_info = models.TextField(verbose_name='Información de especie de predicción', blank=True)
    prediccion_parametros_usados = models.TextField(verbose_name='Parámetros usados en predicción', blank=True)

    def save(self, *args, **kwargs):
        # Calcular días de polinización automáticamente si no se proporciona
        if not self.dias_polinizacion and self.fecha_ingreso and self.fecha_polinizacion:
            from datetime import date
            self.dias_polinizacion = (self.fecha_ingreso - self.fecha_polinizacion).days
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} - {self.especie_variedad} - {self.fecha_siembra}"

class SeguimientoGerminacion(models.Model):
    ETAPAS_SEGUIMIENTO = [
        ('SIEMBRA', 'Siembra'),
        ('GERMINACION', 'Germinación'),
        ('CRECIMIENTO', 'Crecimiento'),
        ('TRASPLANTE', 'Trasplante'),
    ]
    
    germinacion = models.ForeignKey(Germinacion, on_delete=models.CASCADE, related_name='seguimientos')
    fecha = models.DateField(null=True, blank=True, verbose_name='Fecha de seguimiento')
    cantidad_germinada = models.PositiveIntegerField(default=0, verbose_name='Cantidad germinada')
    etapa = models.CharField(max_length=20, choices=ETAPAS_SEGUIMIENTO, verbose_name='Etapa')
    observaciones = models.TextField(blank=True, verbose_name='Observaciones')
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='seguimientos_germinacion', verbose_name='Responsable')
    
    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Seguimiento de germinación'
        verbose_name_plural = 'Seguimientos de germinación'
    
    def __str__(self):
        return f"Seguimiento {self.id} - {self.germinacion.codigo} ({self.fecha})"

class Capsula(models.Model):
    germinacion = models.ForeignKey(Germinacion, on_delete=models.CASCADE, related_name='capsulas')
    numero = models.AutoField(primary_key=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

class Siembra(models.Model):
    germinacion = models.ForeignKey(Germinacion, on_delete=models.CASCADE, related_name='siembras')
    numero = models.AutoField(primary_key=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

class PersonalUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=255)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

class Inventario(models.Model):
    germinacion = models.ForeignKey(Germinacion, on_delete=models.CASCADE, related_name='inventarios')
    numero = models.AutoField(primary_key=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

class Notification(models.Model):
    TIPO_CHOICES = [
        ('NUEVA_GERMINACION', 'Nueva Germinación'),
        ('RECORDATORIO_REVISION', 'Recordatorio de Revisión'),
        ('ESTADO_ACTUALIZADO', 'Estado Actualizado'),
        ('NUEVA_POLINIZACION', 'Nueva Polinización'),
        ('ESTADO_POLINIZACION_ACTUALIZADO', 'Estado de Polinización Actualizado'),
        ('MENSAJE', 'Mensaje'),
        ('ERROR', 'Error'),
        ('ACTUALIZACION', 'Actualización'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    germinacion = models.ForeignKey(Germinacion, on_delete=models.CASCADE, related_name='notificaciones', null=True, blank=True)
    polinizacion = models.ForeignKey(Polinizacion, on_delete=models.CASCADE, related_name='notificaciones', null=True, blank=True)
    tipo = models.CharField(max_length=35, choices=TIPO_CHOICES)
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    favorita = models.BooleanField(default=False)
    archivada = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_lectura = models.DateTimeField(null=True, blank=True)
    detalles_adicionales = models.JSONField(null=True, blank=True, help_text="Detalles adicionales en formato JSON")
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        indexes = [
            models.Index(fields=['usuario', '-fecha_creacion']),
            models.Index(fields=['usuario', 'leida']),
            models.Index(fields=['usuario', 'archivada']),
        ]
    
    def __str__(self):
        if self.germinacion:
            return f"{self.tipo} - {self.usuario.username} - {self.germinacion.codigo or self.germinacion.nombre}"
        elif self.polinizacion:
            return f"{self.tipo} - {self.usuario.username} - {self.polinizacion.codigo}"
        else:
            return f"{self.tipo} - {self.usuario.username}"
    
    def marcar_como_leida(self):
        self.leida = True
        self.fecha_lectura = timezone.now()
        self.save()
    
    def toggle_favorita(self):
        self.favorita = not self.favorita
        self.save()
    
    def archivar(self):
        self.archivada = True
        self.save()
    
    def desarchivar(self):
        self.archivada = False
        self.save()


# ============================================================================
# SISTEMA DE CONTROL DE ACCESO BASADO EN ROLES (RBAC)
# ============================================================================

class UserProfile(models.Model):
    """
    Perfil extendido del usuario con información de roles y permisos
    """
    ROLES_CHOICES = [
        ('TIPO_1', 'Técnico de Laboratorio Senior'),  # Germinaciones, polinizaciones, reportes, perfil
        ('TIPO_2', 'Especialista en Polinización'),  # Polinizaciones, perfil
        ('TIPO_3', 'Especialista en Germinación'),  # Germinaciones, perfil
        ('TIPO_4', 'Gestor del Sistema'),  # Acceso total
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    rol = models.CharField(max_length=10, choices=ROLES_CHOICES, default='TIPO_3')
    
    # Información adicional del perfil
    telefono = models.CharField(max_length=20, blank=True)
    departamento = models.CharField(max_length=100, blank=True)
    fecha_ingreso = models.DateField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    
    # Metas de rendimiento mensual
    meta_polinizaciones = models.PositiveIntegerField(default=0, verbose_name='Meta mensual de polinizaciones')
    meta_germinaciones = models.PositiveIntegerField(default=0, verbose_name='Meta mensual de germinaciones')
    tasa_exito_objetivo = models.PositiveIntegerField(default=80, verbose_name='Tasa de éxito objetivo (%)')
    
    # Progreso actual del mes
    polinizaciones_actuales = models.PositiveIntegerField(default=0, verbose_name='Polinizaciones del mes actual')
    germinaciones_actuales = models.PositiveIntegerField(default=0, verbose_name='Germinaciones del mes actual')
    tasa_exito_actual = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Tasa de éxito actual (%)')
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_rol_display()}"
    
    @property
    def puede_ver_germinaciones(self):
        """Verifica si el usuario puede ver germinaciones"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_3', 'TIPO_4']
    
    @property
    def puede_crear_germinaciones(self):
        """Verifica si el usuario puede crear germinaciones"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_3', 'TIPO_4']
    
    @property
    def puede_editar_germinaciones(self):
        """Verifica si el usuario puede editar germinaciones"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_3', 'TIPO_4']
    
    @property
    def puede_ver_polinizaciones(self):
        """Verifica si el usuario puede ver polinizaciones"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_2', 'TIPO_4']
    
    @property
    def puede_crear_polinizaciones(self):
        """Verifica si el usuario puede crear polinizaciones"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_2', 'TIPO_4']
    
    @property
    def puede_editar_polinizaciones(self):
        """Verifica si el usuario puede editar polinizaciones"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_2', 'TIPO_4']
    
    @property
    def puede_ver_reportes(self):
        """Verifica si el usuario puede ver reportes"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_4']
    
    @property
    def puede_generar_reportes(self):
        """Verifica si el usuario puede generar reportes"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_4']
    
    @property
    def puede_administrar_usuarios(self):
        """Verifica si el usuario puede administrar otros usuarios"""
        return self.activo and self.rol == 'TIPO_4'
    
    @property
    def puede_ver_estadisticas_globales(self):
        """Verifica si el usuario puede ver estadísticas globales"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_4']
    
    @property
    def puede_exportar_datos(self):
        """Verifica si el usuario puede exportar datos"""
        return self.activo and self.rol in ['TIPO_1', 'TIPO_4']
    
    def get_permisos_detallados(self):
        """Retorna un diccionario con todos los permisos del usuario"""
        return {
            'germinaciones': {
                'ver': self.puede_ver_germinaciones,
                'crear': self.puede_crear_germinaciones,
                'editar': self.puede_editar_germinaciones,
            },
            'polinizaciones': {
                'ver': self.puede_ver_polinizaciones,
                'crear': self.puede_crear_polinizaciones,
                'editar': self.puede_editar_polinizaciones,
            },
            'reportes': {
                'ver': self.puede_ver_reportes,
                'generar': self.puede_generar_reportes,
                'exportar': self.puede_exportar_datos,
            },
            'administracion': {
                'usuarios': self.puede_administrar_usuarios,
                'estadisticas_globales': self.puede_ver_estadisticas_globales,
            }
        }

    def puede_tener_meta_polinizaciones(self):
        """Verifica si el usuario puede tener meta de polinizaciones según su rol"""
        return self.rol in ['TIPO_1', 'TIPO_2', 'TIPO_4']
    
    def puede_tener_meta_germinaciones(self):
        """Verifica si el usuario puede tener meta de germinaciones según su rol"""
        return self.rol in ['TIPO_1', 'TIPO_3', 'TIPO_4']
    
    def validar_metas_segun_rol(self):
        """Valida que las metas sean consistentes con el rol del usuario"""
        errores = []
        
        # Si no puede tener meta de polinizaciones, debe ser 0
        if not self.puede_tener_meta_polinizaciones() and self.meta_polinizaciones > 0:
            errores.append(f"El rol {self.get_rol_display()} no puede tener meta de polinizaciones")
        
        # Si no puede tener meta de germinaciones, debe ser 0
        if not self.puede_tener_meta_germinaciones() and self.meta_germinaciones > 0:
            errores.append(f"El rol {self.get_rol_display()} no puede tener meta de germinaciones")
        
        # Validar tasa de éxito
        if self.tasa_exito_objetivo < 0 or self.tasa_exito_objetivo > 100:
            errores.append("La tasa de éxito objetivo debe estar entre 0% y 100%")
        
        return errores
    
    def actualizar_progreso_mensual(self):
        """Actualiza el progreso mensual basado en las actividades del usuario"""
        from django.utils import timezone
        
        # Obtener el primer día del mes actual
        hoy = timezone.now().date()
        primer_dia_mes = hoy.replace(day=1)
        
        # Contar polinizaciones del mes actual (sin import circular)
        if self.puede_tener_meta_polinizaciones():
            self.polinizaciones_actuales = Polinizacion.objects.filter(
                creado_por=self.user,
                fechapol__gte=primer_dia_mes
            ).count()
        else:
            self.polinizaciones_actuales = 0
        
        # Contar germinaciones del mes actual (sin import circular)
        if self.puede_tener_meta_germinaciones():
            self.germinaciones_actuales = Germinacion.objects.filter(
                creado_por=self.user,
                fecha_siembra__gte=primer_dia_mes
            ).count()
        else:
            self.germinaciones_actuales = 0
        
        # Calcular tasa de éxito real
        total_actividades = self.polinizaciones_actuales + self.germinaciones_actuales
        
        if total_actividades > 0:
            # Calcular tasa de éxito basada en actividades exitosas
            polinizaciones_exitosas = Polinizacion.objects.filter(
                creado_por=self.user,
                fechapol__gte=primer_dia_mes,
                estado='LISTA'
            ).count()
            
            germinaciones_exitosas = Germinacion.objects.filter(
                creado_por=self.user,
                fecha_siembra__gte=primer_dia_mes,
                estado_capsula='ABIERTA'
            ).count()
            
            total_exitosas = polinizaciones_exitosas + germinaciones_exitosas
            self.tasa_exito_actual = round((total_exitosas / total_actividades) * 100, 2)
        else:
            self.tasa_exito_actual = 0.00
        
        self.save()
    
    def obtener_progreso_meta_polinizaciones(self):
        """Obtiene el porcentaje de progreso de la meta de polinizaciones"""
        if self.meta_polinizaciones > 0:
            return min(round((self.polinizaciones_actuales / self.meta_polinizaciones) * 100, 2), 100)
        return 0
    
    def obtener_progreso_meta_germinaciones(self):
        """Obtiene el porcentaje de progreso de la meta de germinaciones"""
        if self.meta_germinaciones > 0:
            return min(round((self.germinaciones_actuales / self.meta_germinaciones) * 100, 2), 100)
        return 0
    
    def obtener_estado_meta_polinizaciones(self):
        """Obtiene el estado de la meta de polinizaciones (Completada, En Progreso, Pendiente)"""
        progreso = self.obtener_progreso_meta_polinizaciones()
        if progreso >= 100:
            return 'Completada'
        elif progreso > 0:
            return 'En Progreso'
        else:
            return 'Pendiente'
    
    def obtener_estado_meta_germinaciones(self):
        """Obtiene el estado de la meta de germinaciones (Completada, En Progreso, Pendiente)"""
        progreso = self.obtener_progreso_meta_germinaciones()
        if progreso >= 100:
            return 'Completada'
        elif progreso > 0:
            return 'En Progreso'
        else:
            return 'Pendiente'


# Señales para crear automáticamente el perfil cuando se crea un usuario
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """
    Crea automáticamente un perfil de usuario cuando se crea un nuevo usuario
    """
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    """
    Guarda el perfil del usuario cuando se actualiza
    """
    if hasattr(instance, 'profile'):
        try:
            instance.profile.save()
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error guardando perfil de usuario {instance.username}: {e}")

# Señales para actualizar progreso automáticamente
@receiver(post_save, sender=Polinizacion)
def actualizar_progreso_polinizacion(sender, instance, created, **kwargs):
    """
    Actualiza el progreso del usuario cuando se crea o actualiza una polinización
    """
    if instance.responsable:
        try:
            user = User.objects.get(username=instance.responsable)
            if hasattr(user, 'profile'):
                user.profile.actualizar_progreso_mensual()
        except User.DoesNotExist:
            pass

@receiver(post_save, sender=Germinacion)
def actualizar_progreso_germinacion(sender, instance, created, **kwargs):
    """
    Actualiza el progreso del usuario cuando se crea o actualiza una germinación
    """
    if instance.responsable:
        try:
            user = User.objects.get(username=instance.responsable)
            if hasattr(user, 'profile'):
                user.profile.actualizar_progreso_mensual()
        except User.DoesNotExist:
            pass


# ============================================================================
# MODELOS PARA PREDICCIONES DE POLINIZACIÓN CON MODELO .BIN
# ============================================================================

class PrediccionPolinizacion(models.Model):
    """
    Modelo para almacenar predicciones de polinización usando el modelo .bin
    """
    TIPOS_PREDICCION = [
        ('inicial', 'Predicción Inicial'),
        ('refinada', 'Predicción Refinada'),
        ('basica_con_fecha', 'Predicción Básica con Fecha'),
        ('validada', 'Predicción Validada'),
    ]
    
    ESTADOS_PREDICCION = [
        ('activa', 'Activa'),
        ('validada', 'Validada'),
        ('archivada', 'Archivada'),
    ]
    
    # Identificación
    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=50, unique=True, verbose_name='Código de predicción')
    
    # Datos básicos
    especie = models.CharField(max_length=100, verbose_name='Especie')
    genero = models.CharField(max_length=100, blank=True, verbose_name='Género')
    clima = models.CharField(max_length=50, blank=True, verbose_name='Clima')
    ubicacion = models.CharField(max_length=100, blank=True, verbose_name='Ubicación')
    
    # Datos de polinización
    fecha_polinizacion = models.DateField(null=True, blank=True, verbose_name='Fecha de polinización')
    tipo_polinizacion = models.CharField(max_length=50, blank=True, verbose_name='Tipo de polinización')
    
    # Resultados de predicción
    dias_estimados = models.PositiveIntegerField(verbose_name='Días estimados hasta semillas')
    fecha_estimada_semillas = models.DateField(null=True, blank=True, verbose_name='Fecha estimada de semillas')
    confianza = models.PositiveIntegerField(default=0, verbose_name='Confianza de predicción (%)')
    
    # Tipo y estado
    tipo_prediccion = models.CharField(max_length=20, choices=TIPOS_PREDICCION, default='inicial')
    estado = models.CharField(max_length=20, choices=ESTADOS_PREDICCION, default='activa')
    
    # Datos del modelo usado
    archivo_modelo_usado = models.CharField(max_length=100, default='Polinizacion.bin', verbose_name='Archivo del modelo')
    version_modelo = models.CharField(max_length=20, blank=True, verbose_name='Versión del modelo')
    
    # Usuario y fechas
    usuario_creador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predicciones_polinizacion')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    # Validación (cuando se ingresa fecha real)
    fecha_maduracion_real = models.DateField(null=True, blank=True, verbose_name='Fecha real de maduración')
    dias_reales = models.PositiveIntegerField(null=True, blank=True, verbose_name='Días reales hasta semillas')
    precision = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Precisión (%)')
    desviacion_dias = models.IntegerField(null=True, blank=True, verbose_name='Desviación en días')
    
    class Meta:
        verbose_name = 'Predicción de Polinización'
        verbose_name_plural = 'Predicciones de Polinización'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['especie', 'fecha_creacion']),
            models.Index(fields=['usuario_creador', 'estado']),
            models.Index(fields=['fecha_polinizacion']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.especie} ({self.get_tipo_prediccion_display()})"
    
    def save(self, *args, **kwargs):
        # Generar código automáticamente si no existe
        if not self.codigo:
            from django.utils import timezone
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.codigo = f"PRED-POL-{timestamp}"
        
        # Calcular días reales si hay fecha de maduración
        if self.fecha_maduracion_real and self.fecha_polinizacion:
            self.dias_reales = (self.fecha_maduracion_real - self.fecha_polinizacion).days
            
            # Calcular precisión
            if self.dias_estimados > 0:
                diferencia = abs(self.dias_reales - self.dias_estimados)
                self.desviacion_dias = self.dias_reales - self.dias_estimados
                desviacion_porcentual = (diferencia / self.dias_estimados) * 100
                self.precision = max(0, 100 - desviacion_porcentual)
                
                # Cambiar estado a validada
                if self.estado == 'activa':
                    self.estado = 'validada'
        
        super().save(*args, **kwargs)
    
    @property
    def esta_validada(self):
        """Verifica si la predicción ha sido validada con datos reales"""
        return self.fecha_maduracion_real is not None
    
    @property
    def calidad_prediccion(self):
        """Determina la calidad de la predicción basada en la precisión"""
        if not self.precision:
            return 'Sin validar'
        
        if self.precision >= 90:
            return 'Excelente'
        elif self.precision >= 75:
            return 'Buena'
        elif self.precision >= 60:
            return 'Aceptable'
        elif self.precision >= 40:
            return 'Regular'
        else:
            return 'Pobre'
    
    @property
    def dias_restantes(self):
        """Calcula los días restantes hasta la fecha estimada de semillas"""
        if not self.fecha_estimada_semillas:
            return None
        
        from django.utils import timezone
        hoy = timezone.now().date()
        
        if self.fecha_estimada_semillas > hoy:
            return (self.fecha_estimada_semillas - hoy).days
        else:
            return 0  # Ya pasó la fecha
    
    def obtener_factores_usados(self):
        """Retorna una lista de factores que se usaron en la predicción"""
        factores = ['especie']
        
        if self.clima:
            factores.append('clima')
        if self.ubicacion:
            factores.append('ubicacion')
        if self.fecha_polinizacion:
            factores.append('fecha_polinizacion')
        if self.tipo_polinizacion:
            factores.append('tipo_polinizacion')
        
        # Verificar si hay condiciones climáticas detalladas
        if hasattr(self, 'condiciones_climaticas') and self.condiciones_climaticas.exists():
            factores.append('condiciones_climaticas_detalladas')
        
        return factores


class CondicionesClimaticas(models.Model):
    """
    Modelo para almacenar condiciones climáticas detalladas de una predicción
    """
    prediccion = models.OneToOneField(
        PrediccionPolinizacion, 
        on_delete=models.CASCADE, 
        related_name='condiciones_climaticas'
    )
    
    # Temperatura
    temperatura_promedio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Temperatura promedio (°C)')
    temperatura_minima = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Temperatura mínima (°C)')
    temperatura_maxima = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Temperatura máxima (°C)')
    
    # Humedad y precipitación
    humedad = models.PositiveIntegerField(null=True, blank=True, verbose_name='Humedad (%)')
    precipitacion = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name='Precipitación (mm)')
    
    # Estación del año
    ESTACIONES = [
        ('primavera', 'Primavera'),
        ('verano', 'Verano'),
        ('otoño', 'Otoño'),
        ('invierno', 'Invierno'),
    ]
    estacion = models.CharField(max_length=20, choices=ESTACIONES, blank=True, verbose_name='Estación del año')
    
    # Otros factores
    viento_promedio = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='Viento promedio (km/h)')
    horas_luz = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name='Horas de luz solar')
    
    # Metadatos
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Condiciones Climáticas'
        verbose_name_plural = 'Condiciones Climáticas'
    
    def __str__(self):
        return f"Condiciones para {self.prediccion.codigo}"
    
    @property
    def temperatura_optima(self):
        """Verifica si la temperatura está en rango óptimo (20-25°C)"""
        if self.temperatura_promedio:
            return 20 <= self.temperatura_promedio <= 25
        return None
    
    @property
    def humedad_optima(self):
        """Verifica si la humedad está en rango óptimo (60-80%)"""
        if self.humedad:
            return 60 <= self.humedad <= 80
        return None


class HistorialPredicciones(models.Model):
    """
    Modelo para mantener estadísticas y métricas del historial de predicciones
    """
    # Período de análisis
    fecha_inicio = models.DateField(verbose_name='Fecha inicio del período')
    fecha_fin = models.DateField(verbose_name='Fecha fin del período')
    
    # Estadísticas generales
    total_predicciones = models.PositiveIntegerField(default=0, verbose_name='Total de predicciones')
    predicciones_validadas = models.PositiveIntegerField(default=0, verbose_name='Predicciones validadas')
    precision_promedio = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Precisión promedio (%)')
    confianza_promedio = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name='Confianza promedio (%)')
    
    # Estadísticas por tipo
    predicciones_iniciales = models.PositiveIntegerField(default=0, verbose_name='Predicciones iniciales')
    predicciones_refinadas = models.PositiveIntegerField(default=0, verbose_name='Predicciones refinadas')
    
    # Especies más predichas
    especie_mas_predicha = models.CharField(max_length=100, blank=True, verbose_name='Especie más predicha')
    cantidad_especie_top = models.PositiveIntegerField(default=0, verbose_name='Cantidad de la especie top')
    
    # Métricas de calidad
    predicciones_excelentes = models.PositiveIntegerField(default=0, verbose_name='Predicciones excelentes (>90%)')
    predicciones_buenas = models.PositiveIntegerField(default=0, verbose_name='Predicciones buenas (75-90%)')
    predicciones_aceptables = models.PositiveIntegerField(default=0, verbose_name='Predicciones aceptables (60-75%)')
    predicciones_pobres = models.PositiveIntegerField(default=0, verbose_name='Predicciones pobres (<60%)')
    
    # Usuario que generó el reporte
    usuario_generador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='historiales_generados')
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Historial de Predicciones'
        verbose_name_plural = 'Historiales de Predicciones'
        ordering = ['-fecha_generacion']
    
    def __str__(self):
        return f"Historial {self.fecha_inicio} - {self.fecha_fin} ({self.total_predicciones} predicciones)"
    
    @classmethod
    def generar_historial(cls, fecha_inicio, fecha_fin, usuario):
        """
        Genera un nuevo historial de predicciones para el período especificado
        """
        from django.db.models import Avg, Count, Q
        
        # Obtener predicciones del período
        predicciones = PrediccionPolinizacion.objects.filter(
            fecha_creacion__date__gte=fecha_inicio,
            fecha_creacion__date__lte=fecha_fin
        )
        
        # Calcular estadísticas
        total = predicciones.count()
        validadas = predicciones.filter(estado='validada').count()
        
        # Precisión promedio (solo de las validadas)
        precision_avg = predicciones.filter(
            precision__isnull=False
        ).aggregate(Avg('precision'))['precision__avg'] or 0
        
        # Confianza promedio
        confianza_avg = predicciones.aggregate(Avg('confianza'))['confianza__avg'] or 0
        
        # Contar por tipo
        iniciales = predicciones.filter(tipo_prediccion='inicial').count()
        refinadas = predicciones.filter(tipo_prediccion='refinada').count()
        
        # Especie más predicha
        especie_top = predicciones.values('especie').annotate(
            count=Count('especie')
        ).order_by('-count').first()
        
        # Métricas de calidad
        excelentes = predicciones.filter(precision__gte=90).count()
        buenas = predicciones.filter(precision__gte=75, precision__lt=90).count()
        aceptables = predicciones.filter(precision__gte=60, precision__lt=75).count()
        pobres = predicciones.filter(precision__lt=60, precision__isnull=False).count()
        
        # Crear el historial
        historial = cls.objects.create(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            total_predicciones=total,
            predicciones_validadas=validadas,
            precision_promedio=round(precision_avg, 2),
            confianza_promedio=round(confianza_avg, 2),
            predicciones_iniciales=iniciales,
            predicciones_refinadas=refinadas,
            especie_mas_predicha=especie_top['especie'] if especie_top else '',
            cantidad_especie_top=especie_top['count'] if especie_top else 0,
            predicciones_excelentes=excelentes,
            predicciones_buenas=buenas,
            predicciones_aceptables=aceptables,
            predicciones_pobres=pobres,
            usuario_generador=usuario
        )
        
        return historial
    
    @property
    def tasa_validacion(self):
        """Calcula la tasa de validación (predicciones validadas / total)"""
        if self.total_predicciones > 0:
            return round((self.predicciones_validadas / self.total_predicciones) * 100, 2)
        return 0
    
    @property
    def distribucion_calidad(self):
        """Retorna la distribución de calidad como diccionario"""
        return {
            'excelentes': self.predicciones_excelentes,
            'buenas': self.predicciones_buenas,
            'aceptables': self.predicciones_aceptables,
            'pobres': self.predicciones_pobres
        }