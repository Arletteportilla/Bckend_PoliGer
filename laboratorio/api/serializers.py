from rest_framework import serializers
from django.contrib.auth.models import User
from datetime import date, timedelta
from ..core.models import (
    Genero, Especie, Variedad, Ubicacion, Polinizacion,
    Germinacion, SeguimientoGerminacion, Capsula, Siembra,
    PersonalUsuario, Inventario, Notification, UserProfile,
    PrediccionPolinizacion, CondicionesClimaticas, HistorialPredicciones
)

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class GeneroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genero
        fields = '__all__'

class EspecieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Especie
        fields = '__all__'

class VariedadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variedad
        fields = '__all__'


class UbicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ubicacion
        fields = '__all__'

class PolinizacionSerializer(serializers.ModelSerializer):
    creado_por = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Polinizacion
        fields = [
            'numero', 'codigo', 'fechapol', 'fechamad', 'tipo_polinizacion',
            'madre_codigo', 'madre_genero', 'madre_clima', 'madre_especie',
            'padre_codigo', 'padre_genero', 'padre_clima', 'padre_especie',
            'nueva_codigo', 'nueva_genero', 'nueva_clima', 'nueva_especie',
            'ubicacion_tipo', 'ubicacion_nombre', 'cantidad_capsulas',
            'responsable', 'disponible', 'estado', 'creado_por',
            'fecha_creacion', 'fecha_actualizacion',
            # Campos legacy para compatibilidad
            'genero', 'especie', 'ubicacion', 'cantidad', 'archivo_origen', 'observaciones',
            # Campos de ubicación detallada
            'vivero', 'mesa', 'pared',
            # Campos de predicción
            'prediccion_dias_estimados', 'prediccion_confianza', 'prediccion_fecha_estimada',
            'prediccion_tipo', 'prediccion_condiciones_climaticas', 'prediccion_especie_info',
            'prediccion_parametros_usados'
        ]
        extra_kwargs = {
            'fechamad': {'required': False, 'allow_null': True},
            'codigo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'ubicacion': {'required': False, 'allow_blank': True, 'allow_null': True},
            'genero': {'required': False, 'allow_blank': True, 'allow_null': True},
            'especie': {'required': False, 'allow_blank': True, 'allow_null': True},
            'observaciones': {'required': False, 'allow_blank': True, 'allow_null': True},
            # Hacer campos de padre opcionales
            'padre_codigo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'padre_genero': {'required': False, 'allow_blank': True, 'allow_null': True},
            'padre_especie': {'required': False, 'allow_blank': True, 'allow_null': True},
            'padre_clima': {'required': False, 'allow_blank': True, 'allow_null': True},
            # Hacer campos de ubicación opcionales
            'ubicacion_nombre': {'required': False, 'allow_blank': True, 'allow_null': True},
            'ubicacion_tipo': {'required': False, 'allow_blank': True, 'allow_null': True},
            'vivero': {'required': False, 'allow_blank': True, 'allow_null': True},
            'mesa': {'required': False, 'allow_blank': True, 'allow_null': True},
            'pared': {'required': False, 'allow_blank': True, 'allow_null': True},
        }
    
    def create(self, validated_data):
        """Crear una nueva polinización con validaciones personalizadas"""
        try:
            polinizacion = super().create(validated_data)
            return polinizacion
        except Exception as e:
            raise serializers.ValidationError(f"Error al crear polinización: {str(e)}")
    
    def validate(self, data):


        """Validaciones personalizadas simplificadas"""
        from datetime import date
        from django.utils.dateparse import parse_date
        
        # Compatibilidad de nombres de campos
        # El frontend puede enviar 'fecha_polinizacion' en lugar de 'fechapol'
        if 'fecha_polinizacion' in data and 'fechapol' not in data:
            data['fechapol'] = data.pop('fecha_polinizacion')
        
        # El frontend puede enviar 'fecha_maduracion' en lugar de 'fechamad'
        if 'fecha_maduracion' in data and 'fechamad' not in data:
            fechamad_value = data.pop('fecha_maduracion')
            # Solo asignar si no es None o vacío
            if fechamad_value:
                data['fechamad'] = fechamad_value
        
        # Validar que fechapol esté presente y sea válida
        if 'fechapol' not in data or not data['fechapol']:
            raise serializers.ValidationError({
                'fechapol': 'La fecha de polinización es obligatoria'
            })
        
        # Convertir fechapol a objeto date si es string
        fechapol = data['fechapol']
        if isinstance(fechapol, str):
            try:
                fechapol = parse_date(fechapol)
                if not fechapol:
                    raise serializers.ValidationError({
                        'fechapol': 'Formato de fecha inválido. Use YYYY-MM-DD'
                    })
                data['fechapol'] = fechapol
            except Exception:
                raise serializers.ValidationError({
                    'fechapol': 'Formato de fecha inválido. Use YYYY-MM-DD'
                })
        
        # Validar que las fechas no sean futuras (permitir fechas futuras para testing)
        # today = date.today()
        # if fechapol > today:
        #     raise serializers.ValidationError({
        #         'fechapol': 'La fecha de polinización no puede ser futura'
        #     })
        
        # Validar fechamad si está presente
        if data.get('fechamad'):
            fechamad = data['fechamad']
            if isinstance(fechamad, str):
                try:
                    fechamad = parse_date(fechamad)
                    if not fechamad:
                        raise serializers.ValidationError({
                            'fechamad': 'Formato de fecha inválido. Use YYYY-MM-DD'
                        })
                    data['fechamad'] = fechamad
                except Exception:
                    raise serializers.ValidationError({
                        'fechamad': 'Formato de fecha inválido. Use YYYY-MM-DD'
                    })
            
            # Validar que las fechas sean coherentes
            if fechapol > fechamad:
                raise serializers.ValidationError({
                    'fechamad': 'La fecha de polinización no puede ser posterior a la fecha de maduración'
                })
        
        # Validar cantidad si está presente
        if data.get('cantidad'):
            cantidad = data['cantidad']
            if cantidad <= 0:
                raise serializers.ValidationError({
                    'cantidad': 'La cantidad debe ser mayor a 0'
                })
            if cantidad > 1000000: # Límite razonable
                raise serializers.ValidationError({
                    'cantidad': 'La cantidad parece demasiado alta (máximo 1,000,000)'
                })
        
        # Validar campos básicos sin ser tan estricto
        if data.get('codigo') and not data['codigo'].strip():
            raise serializers.ValidationError({
                'codigo': 'El código no puede estar vacío'
            })
        
        # Hacer género y especie opcionales para compatibilidad
        # if not data.get('genero') or not data['genero'].strip():
        #     raise serializers.ValidationError({
        #         'genero': 'El género es obligatorio'
        #     })
        
        # if not data.get('especie') or not data['especie'].strip():
        #     raise serializers.ValidationError({
        #         'especie': 'La especie es obligatoria'
        #     })
        
        return data

class GerminacionSerializer(serializers.ModelSerializer):
    creado_por = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Germinacion
        fields = [
            'id', 'fecha_polinizacion', 'fecha_siembra', 'fecha_ingreso', 'codigo', 'nombre',
            'genero', 'especie_variedad', 'clima', 'percha', 'nivel', 'clima_lab',
            'cantidad_solicitada', 'no_capsulas', 'estado_capsula', 'estado_semilla',
            'cantidad_semilla', 'semilla_en_stock', 'observaciones', 'responsable',
            'fecha_creacion', 'fecha_actualizacion', 'creado_por',
            # Campos de predicción
            'prediccion_dias_estimados', 'prediccion_confianza', 'prediccion_fecha_estimada',
            'prediccion_tipo', 'prediccion_condiciones_climaticas', 'prediccion_especie_info',
            'prediccion_parametros_usados',
            # Campos legacy para compatibilidad
            'fecha_germinacion', 'estado_capsulas', 'tipo_polinizacion',
            'entrega_capsulas', 'recibe_capsulas', 'semilla_vana', 'semillas_stock',
            'disponibles'
        ]
    
    def create(self, validated_data):
        """Crear una nueva germinación con validaciones personalizadas"""
        try:
            # Asegurar que los campos requeridos estén presentes
            if not validated_data.get('codigo'):
                raise serializers.ValidationError({'codigo': 'El código es requerido'})

            if not validated_data.get('especie_variedad'):
                raise serializers.ValidationError({'especie_variedad': 'La especie/variedad es requerida'})

            # Crear la germinación
            germinacion = super().create(validated_data)
            return germinacion

        except serializers.ValidationError:
            # Re-lanzar errores de validación sin modificar
            raise
        except Exception as e:
            raise serializers.ValidationError({
                'non_field_errors': [f'Error interno al crear germinación: {str(e)}']
            })
    
    def validate(self, data):
        """Validaciones personalizadas mejoradas"""
        from datetime import date
        from django.utils.dateparse import parse_date
        
        # Validar campos obligatorios primero
        required_fields = {
            'codigo': 'El código es obligatorio',
            'especie_variedad': 'La especie/variedad es obligatoria',
            'fecha_siembra': 'La fecha de siembra es obligatoria',
            'cantidad_solicitada': 'La cantidad solicitada es obligatoria',
            'no_capsulas': 'El número de cápsulas es obligatorio',
            'responsable': 'El responsable es obligatorio'
        }
        
        errors = {}
        
        for field, message in required_fields.items():
            if not data.get(field):
                errors[field] = message
            elif isinstance(data[field], str) and not data[field].strip():
                errors[field] = f"{field.replace('_', ' ').title()} no puede estar vacío"
        
        # Validar y convertir fechas
        today = date.today()
        max_future_date = today + timedelta(days=30)  # Permitir hasta 30 días en el futuro

        # Fecha de siembra
        if data.get('fecha_siembra'):
            fecha_siembra = data['fecha_siembra']
            if isinstance(fecha_siembra, str):
                try:
                    fecha_siembra = parse_date(fecha_siembra)
                    if not fecha_siembra:
                        errors['fecha_siembra'] = 'Formato de fecha de siembra inválido (use YYYY-MM-DD)'
                    else:
                        data['fecha_siembra'] = fecha_siembra
                except Exception:
                    errors['fecha_siembra'] = 'Formato de fecha de siembra inválido (use YYYY-MM-DD)'

            if fecha_siembra and fecha_siembra > max_future_date:
                errors['fecha_siembra'] = f'La fecha de siembra no puede ser más de 30 días en el futuro'
        
        # Fecha de polinización (opcional)
        if data.get('fecha_polinizacion'):
            fecha_pol = data['fecha_polinizacion']
            if isinstance(fecha_pol, str):
                try:
                    fecha_pol = parse_date(fecha_pol)
                    if not fecha_pol:
                        errors['fecha_polinizacion'] = 'Formato de fecha de polinización inválido (use YYYY-MM-DD)'
                    else:
                        data['fecha_polinizacion'] = fecha_pol
                except Exception:
                    errors['fecha_polinizacion'] = 'Formato de fecha de polinización inválido (use YYYY-MM-DD)'
            
            if fecha_pol and fecha_pol > today:
                errors['fecha_polinizacion'] = 'La fecha de polinización no puede ser futura'
            
            # Validar coherencia de fechas
            if fecha_pol and data.get('fecha_siembra') and fecha_pol > data['fecha_siembra']:
                errors['fecha_polinizacion'] = 'La fecha de polinización no puede ser posterior a la fecha de siembra'
        
        # Validar números positivos
        if data.get('no_capsulas'):
            try:
                capsulas = int(data['no_capsulas'])
                if capsulas <= 0:
                    errors['no_capsulas'] = 'El número de cápsulas debe ser mayor a 0'
                elif capsulas > 10000:
                    errors['no_capsulas'] = 'El número de cápsulas parece demasiado alto (máximo 10,000)'
                else:
                    data['no_capsulas'] = capsulas
            except (ValueError, TypeError):
                errors['no_capsulas'] = 'El número de cápsulas debe ser un número válido'
        
        if data.get('cantidad_solicitada'):
            try:
                cantidad = int(data['cantidad_solicitada'])
                if cantidad <= 0:
                    errors['cantidad_solicitada'] = 'La cantidad solicitada debe ser mayor a 0'
                elif cantidad > 1000000:
                    errors['cantidad_solicitada'] = 'La cantidad solicitada parece demasiado alta (máximo 1,000,000)'
                else:
                    data['cantidad_solicitada'] = cantidad
            except (ValueError, TypeError):
                errors['cantidad_solicitada'] = 'La cantidad solicitada debe ser un número válido'
        
        # Validar código (permitir duplicados para múltiples germinaciones del mismo código)
        if data.get('codigo'):
            codigo = data['codigo'].strip()
            if not codigo:
                errors['codigo'] = 'El código no puede estar vacío'
            else:
                data['codigo'] = codigo
        
        # Validar campos de texto
        text_fields = ['especie_variedad', 'responsable', 'percha']
        for field in text_fields:
            if data.get(field) and isinstance(data[field], str):
                data[field] = data[field].strip()
                if not data[field]:
                    errors[field] = f'{field.replace("_", " ").title()} no puede estar vacío'
        
        if errors:
            raise serializers.ValidationError(errors)

        return data

class SeguimientoGerminacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SeguimientoGerminacion
        fields = '__all__'

class CapsulaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Capsula
        fields = '__all__'

class SiembraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Siembra
        fields = '__all__'

class PersonalUsuarioSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='usuario', read_only=True)
    
    class Meta:
        model = PersonalUsuario
        fields = '__all__'

class InventarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventario
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    germinacion_codigo = serializers.CharField(source='germinacion.codigo', read_only=True)
    germinacion_nombre = serializers.CharField(source='germinacion.nombre', read_only=True)
    germinacion_especie = serializers.CharField(source='germinacion.especie', read_only=True)
    polinizacion_codigo = serializers.CharField(source='polinizacion.codigo', read_only=True)
    polinizacion_genero = serializers.CharField(source='polinizacion.genero', read_only=True)
    polinizacion_especie = serializers.CharField(source='polinizacion.especie', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('fecha_creacion', 'fecha_lectura')


# ============================================================================
# SERIALIZERS PARA SISTEMA RBAC
# ============================================================================

class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer para el perfil de usuario con roles"""
    usuario_info = UserSerializer(source='user', read_only=True)
    rol_display = serializers.CharField(source='get_rol_display', read_only=True)
    permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'user', 'usuario_info', 'rol', 'rol_display', 
            'telefono', 'departamento', 'fecha_ingreso', 'activo',
            'meta_polinizaciones', 'meta_germinaciones', 'tasa_exito_objetivo',
            'polinizaciones_actuales', 'germinaciones_actuales', 'tasa_exito_actual',
            'fecha_creacion', 'fecha_actualizacion', 'permisos'
        ]
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion']
    
    def to_representation(self, instance):
        """Agregar campos calculados de progreso"""
        data = super().to_representation(instance)
        
        # Agregar progreso de metas
        data['progreso_meta_polinizaciones'] = instance.obtener_progreso_meta_polinizaciones()
        data['progreso_meta_germinaciones'] = instance.obtener_progreso_meta_germinaciones()
        data['estado_meta_polinizaciones'] = instance.obtener_estado_meta_polinizaciones()
        data['estado_meta_germinaciones'] = instance.obtener_estado_meta_germinaciones()
        
        return data
    
    def get_permisos(self, obj):
        """Retorna los permisos detallados del usuario"""
        return obj.get_permisos_detallados()


class UpdateUserMetasSerializer(serializers.ModelSerializer):
    """Serializer para actualizar metas de rendimiento de un usuario"""
    
    class Meta:
        model = UserProfile
        fields = [
            'meta_polinizaciones', 'meta_germinaciones', 'tasa_exito_objetivo'
        ]
    
    def validate(self, data):
        """Validar metas según el rol del usuario"""
        user_profile = self.instance
        
        # Validar meta de polinizaciones según rol
        if 'meta_polinizaciones' in data:
            if not user_profile.puede_tener_meta_polinizaciones() and data['meta_polinizaciones'] > 0:
                raise serializers.ValidationError({
                    'meta_polinizaciones': f"El rol {user_profile.get_rol_display()} no puede tener meta de polinizaciones"
                })
        
        # Validar meta de germinaciones según rol
        if 'meta_germinaciones' in data:
            if not user_profile.puede_tener_meta_germinaciones() and data['meta_germinaciones'] > 0:
                raise serializers.ValidationError({
                    'meta_germinaciones': f"El rol {user_profile.get_rol_display()} no puede tener meta de germinaciones"
                })
        
        # Validar tasa de éxito
        if 'tasa_exito_objetivo' in data:
            if data['tasa_exito_objetivo'] < 0 or data['tasa_exito_objetivo'] > 100:
                raise serializers.ValidationError({
                    'tasa_exito_objetivo': 'La tasa de éxito objetivo debe estar entre 0% y 100%'
                })
        
        return data
    
    def update(self, instance, validated_data):
        """Actualizar metas y recalcular progreso"""
        # Actualizar metas
        for field, value in validated_data.items():
            setattr(instance, field, value)
        
        # Actualizar progreso mensual
        instance.actualizar_progreso_mensual()
        
        return instance


class UserWithProfileSerializer(serializers.ModelSerializer):
    """Serializer extendido de usuario que incluye información del perfil"""
    profile = UserProfileSerializer(read_only=True)
    rol = serializers.CharField(source='profile.rol', read_only=True)
    rol_display = serializers.CharField(source='profile.get_rol_display', read_only=True)
    permisos = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_active', 'date_joined', 'profile', 'rol', 'rol_display', 'permisos'
        ]
        read_only_fields = ['id', 'date_joined']
    
    def get_permisos(self, obj):
        """Retorna los permisos del usuario"""
        if hasattr(obj, 'profile'):
            return obj.profile.get_permisos_detallados()
        return {}


class CreateUserWithProfileSerializer(serializers.ModelSerializer):
    """Serializer para crear usuario con perfil"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    rol = serializers.ChoiceField(choices=UserProfile.ROLES_CHOICES, default='TIPO_3')
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)
    departamento = serializers.CharField(max_length=100, required=False, allow_blank=True)
    fecha_ingreso = serializers.DateField(required=False, allow_null=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 
            'password', 'password_confirm', 'rol', 'telefono', 
            'departamento', 'fecha_ingreso'
        ]
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que las contraseñas coincidan
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden'
            })
        
        # Validar que el username no exista
        if User.objects.filter(username=data['username']).exists():
            raise serializers.ValidationError({
                'username': 'Este nombre de usuario ya existe'
            })
        
        # Validar email único si se proporciona
        if data.get('email') and User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({
                'email': 'Este email ya está registrado'
            })
        
        return data
    
    def create(self, validated_data):
        """Crear usuario con perfil"""
        # Extraer datos del perfil
        rol = validated_data.pop('rol', 'TIPO_3')
        telefono = validated_data.pop('telefono', '')
        departamento = validated_data.pop('departamento', '')
        fecha_ingreso = validated_data.pop('fecha_ingreso', None)
        
        # Remover confirmación de contraseña
        validated_data.pop('password_confirm')
        
        # Crear usuario
        user = User.objects.create_user(**validated_data)
        
        # Actualizar o crear perfil
        profile, created = UserProfile.objects.get_or_create(user=user)
        profile.rol = rol
        profile.telefono = telefono
        profile.departamento = departamento
        profile.fecha_ingreso = fecha_ingreso
        profile.save()
        
        return user


class UpdateUserProfileSerializer(serializers.ModelSerializer):
    """Serializer para actualizar perfil de usuario"""
    usuario_info = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = UserProfile
        fields = [
            'id', 'usuario_info', 'rol', 'telefono', 'departamento', 
            'fecha_ingreso', 'activo'
        ]
        read_only_fields = ['id', 'usuario_info']
    
    def validate_rol(self, value):
        """Validar que solo los administradores puedan cambiar roles"""
        request = self.context.get('request')
        if request and hasattr(request.user, 'profile'):
            # Solo los administradores pueden cambiar roles
            if request.user.profile.rol != 'TIPO_4':
                # Los usuarios no admin solo pueden cambiar su propio perfil (excepto rol)
                if self.instance and self.instance.user != request.user:
                    raise serializers.ValidationError(
                        "No tienes permisos para cambiar el rol de otros usuarios"
                    )
                # Mantener el rol actual si no es admin
                return self.instance.rol if self.instance else value
        return value


class PermissionsSerializer(serializers.Serializer):
    """Serializer para mostrar permisos de usuario"""
    germinaciones = serializers.DictField()
    polinizaciones = serializers.DictField()
    reportes = serializers.DictField()
    administracion = serializers.DictField()
    
    def to_representation(self, instance):
        """Convertir permisos a representación"""
        if hasattr(instance, 'profile'):
            return instance.profile.get_permisos_detallados()
        return {
            'germinaciones': {'ver': False, 'crear': False, 'editar': False},
            'polinizaciones': {'ver': False, 'crear': False, 'editar': False},
            'reportes': {'ver': False, 'generar': False, 'exportar': False},
            'administracion': {'usuarios': False, 'estadisticas_globales': False}
        }

# ============================================================================
# SERIALIZERS PARA PREDICCIONES DE POLINIZACIÓN CON MODELO .BIN
# ============================================================================

class CondicionesClimaticasSerializer(serializers.ModelSerializer):
    """Serializer para condiciones climáticas detalladas"""
    
    temperatura_optima = serializers.ReadOnlyField()
    humedad_optima = serializers.ReadOnlyField()
    
    class Meta:
        model = CondicionesClimaticas
        fields = [
            'id', 'temperatura_promedio', 'temperatura_minima', 'temperatura_maxima',
            'humedad', 'precipitacion', 'estacion', 'viento_promedio', 'horas_luz',
            'temperatura_optima', 'humedad_optima', 'fecha_registro', 'fecha_actualizacion'
        ]
        read_only_fields = ['id', 'fecha_registro', 'fecha_actualizacion']


class PrediccionPolinizacionSerializer(serializers.ModelSerializer):
    """Serializer para predicciones de polinización"""
    
    # Campos calculados
    esta_validada = serializers.ReadOnlyField()
    calidad_prediccion = serializers.ReadOnlyField()
    dias_restantes = serializers.ReadOnlyField()
    factores_usados = serializers.SerializerMethodField()
    
    # Relaciones
    usuario_creador_info = UserSerializer(source='usuario_creador', read_only=True)
    condiciones_climaticas = CondicionesClimaticasSerializer(read_only=True)
    
    # Campos de display
    tipo_prediccion_display = serializers.CharField(source='get_tipo_prediccion_display', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    
    class Meta:
        model = PrediccionPolinizacion
        fields = [
            'id', 'codigo', 'especie', 'genero', 'clima', 'ubicacion',
            'fecha_polinizacion', 'tipo_polinizacion', 'dias_estimados',
            'fecha_estimada_semillas', 'confianza', 'tipo_prediccion',
            'tipo_prediccion_display', 'estado', 'estado_display',
            'archivo_modelo_usado', 'version_modelo', 'usuario_creador',
            'usuario_creador_info', 'fecha_creacion', 'fecha_actualizacion',
            'fecha_maduracion_real', 'dias_reales', 'precision', 'desviacion_dias',
            'esta_validada', 'calidad_prediccion', 'dias_restantes',
            'factores_usados', 'condiciones_climaticas'
        ]
        read_only_fields = [
            'id', 'codigo', 'usuario_creador', 'fecha_creacion', 'fecha_actualizacion',
            'dias_reales', 'precision', 'desviacion_dias', 'esta_validada',
            'calidad_prediccion', 'dias_restantes', 'factores_usados'
        ]
    
    def get_factores_usados(self, obj):
        """Obtiene la lista de factores usados en la predicción"""
        return obj.obtener_factores_usados()
    
    def validate(self, data):
        """Validaciones personalizadas"""
        # Validar que la fecha de polinización no sea futura
        if data.get('fecha_polinizacion'):
            from django.utils import timezone
            if data['fecha_polinizacion'] > timezone.now().date():
                raise serializers.ValidationError({
                    'fecha_polinizacion': 'La fecha de polinización no puede ser futura'
                })
        
        # Validar que la fecha de maduración sea posterior a la polinización
        if data.get('fecha_maduracion_real') and data.get('fecha_polinizacion'):
            if data['fecha_maduracion_real'] <= data['fecha_polinizacion']:
                raise serializers.ValidationError({
                    'fecha_maduracion_real': 'La fecha de maduración debe ser posterior a la polinización'
                })
        
        # Validar confianza
        if data.get('confianza') and (data['confianza'] < 0 or data['confianza'] > 100):
            raise serializers.ValidationError({
                'confianza': 'La confianza debe estar entre 0 y 100'
            })
        
        return data


class PrediccionPolinizacionCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear nuevas predicciones de polinización"""
    
    condiciones_climaticas = CondicionesClimaticasSerializer(required=False)
    
    class Meta:
        model = PrediccionPolinizacion
        fields = [
            'especie', 'genero', 'clima', 'ubicacion', 'fecha_polinizacion',
            'tipo_polinizacion', 'dias_estimados', 'fecha_estimada_semillas',
            'confianza', 'tipo_prediccion', 'condiciones_climaticas'
        ]
    
    def create(self, validated_data):
        """Crear predicción con condiciones climáticas opcionales"""
        condiciones_data = validated_data.pop('condiciones_climaticas', None)
        
        # Asignar usuario creador
        validated_data['usuario_creador'] = self.context['request'].user
        
        # Crear la predicción
        prediccion = PrediccionPolinizacion.objects.create(**validated_data)
        
        # Crear condiciones climáticas si se proporcionaron
        if condiciones_data:
            CondicionesClimaticas.objects.create(
                prediccion=prediccion,
                **condiciones_data
            )
        
        return prediccion


class PrediccionPolinizacionUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar predicciones existentes"""
    
    condiciones_climaticas = CondicionesClimaticasSerializer(required=False)
    
    class Meta:
        model = PrediccionPolinizacion
        fields = [
            'clima', 'ubicacion', 'fecha_polinizacion', 'tipo_polinizacion',
            'fecha_maduracion_real', 'condiciones_climaticas'
        ]
    
    def update(self, instance, validated_data):
        """Actualizar predicción y condiciones climáticas"""
        condiciones_data = validated_data.pop('condiciones_climaticas', None)
        
        # Actualizar la predicción
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Actualizar o crear condiciones climáticas
        if condiciones_data:
            if hasattr(instance, 'condiciones_climaticas'):
                # Actualizar existente
                condiciones = instance.condiciones_climaticas
                for attr, value in condiciones_data.items():
                    setattr(condiciones, attr, value)
                condiciones.save()
            else:
                # Crear nueva
                CondicionesClimaticas.objects.create(
                    prediccion=instance,
                    **condiciones_data
                )
        
        return instance


class HistorialPrediccionesSerializer(serializers.ModelSerializer):
    """Serializer para historial de predicciones"""
    
    usuario_generador_info = UserSerializer(source='usuario_generador', read_only=True)
    tasa_validacion = serializers.ReadOnlyField()
    distribucion_calidad = serializers.ReadOnlyField()
    
    class Meta:
        model = HistorialPredicciones
        fields = [
            'id', 'fecha_inicio', 'fecha_fin', 'total_predicciones',
            'predicciones_validadas', 'precision_promedio', 'confianza_promedio',
            'predicciones_iniciales', 'predicciones_refinadas', 'especie_mas_predicha',
            'cantidad_especie_top', 'predicciones_excelentes', 'predicciones_buenas',
            'predicciones_aceptables', 'predicciones_pobres', 'usuario_generador',
            'usuario_generador_info', 'fecha_generacion', 'tasa_validacion',
            'distribucion_calidad'
        ]
        read_only_fields = [
            'id', 'usuario_generador', 'fecha_generacion', 'tasa_validacion',
            'distribucion_calidad'
        ]


class PrediccionPolinizacionResumenSerializer(serializers.ModelSerializer):
    """Serializer resumido para listas de predicciones"""
    
    calidad_prediccion = serializers.ReadOnlyField()
    dias_restantes = serializers.ReadOnlyField()
    tipo_prediccion_display = serializers.CharField(source='get_tipo_prediccion_display', read_only=True)
    
    class Meta:
        model = PrediccionPolinizacion
        fields = [
            'id', 'codigo', 'especie', 'fecha_polinizacion', 'fecha_estimada_semillas',
            'dias_estimados', 'confianza', 'tipo_prediccion', 'tipo_prediccion_display',
            'estado', 'precision', 'calidad_prediccion', 'dias_restantes',
            'fecha_creacion'
        ]


class EstadisticasPrediccionesSerializer(serializers.Serializer):
    """Serializer para estadísticas generales de predicciones"""
    
    total_predicciones = serializers.IntegerField()
    predicciones_validadas = serializers.IntegerField()
    precision_promedio = serializers.DecimalField(max_digits=5, decimal_places=2)
    confianza_promedio = serializers.DecimalField(max_digits=5, decimal_places=2)
    especies_mas_predichas = serializers.ListField(child=serializers.DictField())
    distribucion_por_tipo = serializers.DictField()
    distribucion_por_calidad = serializers.DictField()
    tendencia_mensual = serializers.ListField(child=serializers.DictField())
    
    # Métricas del modelo
    modelo_version = serializers.CharField()
    modelo_precision = serializers.DecimalField(max_digits=5, decimal_places=2)
    ultima_actualizacion = serializers.DateTimeField()




class NotificationSerializer(serializers.ModelSerializer):
    """Serializer para notificaciones"""
    usuario = UserSerializer(read_only=True)
    germinacion_codigo = serializers.SerializerMethodField()
    polinizacion_codigo = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = [
            'id', 'usuario', 'germinacion', 'polinizacion',
            'germinacion_codigo', 'polinizacion_codigo',
            'tipo', 'titulo', 'mensaje', 'leida', 'favorita', 'archivada',
            'fecha_creacion', 'fecha_lectura', 'detalles_adicionales'
        ]
        read_only_fields = ['id', 'usuario', 'fecha_creacion', 'fecha_lectura']
    
    def get_germinacion_codigo(self, obj):
        """Obtiene el código de la germinación si existe"""
        if obj.germinacion:
            return obj.germinacion.codigo or obj.germinacion.nombre
        return None
    
    def get_polinizacion_codigo(self, obj):
        """Obtiene el código de la polinización si existe"""
        if obj.polinizacion:
            return obj.polinizacion.codigo
        return None
