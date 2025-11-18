"""
Tests para el sistema RBAC (Control de Acceso Basado en Roles)
"""
from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date

from laboratorio.models import UserProfile, Polinizacion, Germinacion
from laboratorio.permissions import (
    CanViewGerminaciones, CanCreateGerminaciones, CanEditGerminaciones,
    CanViewPolinizaciones, CanCreatePolinizaciones, CanEditPolinizaciones,
    CanViewReportes, CanGenerateReportes, IsAdministrator
)


class UserProfileTest(TestCase):
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='test_user',
            password='test123',
            email='test@example.com'
        )

    def test_perfil_creado_automaticamente(self):
        """Test que el perfil se cree automáticamente"""
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertIsInstance(self.user.profile, UserProfile)
        self.assertEqual(self.user.profile.rol, 'TIPO_3')  # Rol por defecto

    def test_permisos_tipo_1_tecnico_senior(self):
        """Test permisos para TIPO_1 - Técnico de Laboratorio Senior"""
        self.user.profile.rol = 'TIPO_1'
        self.user.profile.save()
        
        # Debe tener acceso a germinaciones
        self.assertTrue(self.user.profile.puede_ver_germinaciones)
        self.assertTrue(self.user.profile.puede_crear_germinaciones)
        self.assertTrue(self.user.profile.puede_editar_germinaciones)
        
        # Debe tener acceso a polinizaciones
        self.assertTrue(self.user.profile.puede_ver_polinizaciones)
        self.assertTrue(self.user.profile.puede_crear_polinizaciones)
        self.assertTrue(self.user.profile.puede_editar_polinizaciones)
        
        # Debe tener acceso a reportes
        self.assertTrue(self.user.profile.puede_ver_reportes)
        self.assertTrue(self.user.profile.puede_generar_reportes)
        self.assertTrue(self.user.profile.puede_exportar_datos)
        
        # No debe ser administrador
        self.assertFalse(self.user.profile.puede_administrar_usuarios)
        self.assertTrue(self.user.profile.puede_ver_estadisticas_globales)

    def test_permisos_tipo_2_especialista_polinizacion(self):
        """Test permisos para TIPO_2 - Especialista en Polinización"""
        self.user.profile.rol = 'TIPO_2'
        self.user.profile.save()
        
        # NO debe tener acceso a germinaciones
        self.assertFalse(self.user.profile.puede_ver_germinaciones)
        self.assertFalse(self.user.profile.puede_crear_germinaciones)
        self.assertFalse(self.user.profile.puede_editar_germinaciones)
        
        # SÍ debe tener acceso a polinizaciones
        self.assertTrue(self.user.profile.puede_ver_polinizaciones)
        self.assertTrue(self.user.profile.puede_crear_polinizaciones)
        self.assertTrue(self.user.profile.puede_editar_polinizaciones)
        
        # NO debe tener acceso a reportes
        self.assertFalse(self.user.profile.puede_ver_reportes)
        self.assertFalse(self.user.profile.puede_generar_reportes)
        self.assertFalse(self.user.profile.puede_exportar_datos)
        
        # NO debe ser administrador
        self.assertFalse(self.user.profile.puede_administrar_usuarios)
        self.assertFalse(self.user.profile.puede_ver_estadisticas_globales)

    def test_permisos_tipo_3_especialista_germinacion(self):
        """Test permisos para TIPO_3 - Especialista en Germinación"""
        self.user.profile.rol = 'TIPO_3'
        self.user.profile.save()
        
        # SÍ debe tener acceso a germinaciones
        self.assertTrue(self.user.profile.puede_ver_germinaciones)
        self.assertTrue(self.user.profile.puede_crear_germinaciones)
        self.assertTrue(self.user.profile.puede_editar_germinaciones)
        
        # NO debe tener acceso a polinizaciones
        self.assertFalse(self.user.profile.puede_ver_polinizaciones)
        self.assertFalse(self.user.profile.puede_crear_polinizaciones)
        self.assertFalse(self.user.profile.puede_editar_polinizaciones)
        
        # NO debe tener acceso a reportes
        self.assertFalse(self.user.profile.puede_ver_reportes)
        self.assertFalse(self.user.profile.puede_generar_reportes)
        self.assertFalse(self.user.profile.puede_exportar_datos)
        
        # NO debe ser administrador
        self.assertFalse(self.user.profile.puede_administrar_usuarios)
        self.assertFalse(self.user.profile.puede_ver_estadisticas_globales)

    def test_permisos_tipo_4_administrador(self):
        """Test permisos para TIPO_4 - Gestor del Sistema"""
        self.user.profile.rol = 'TIPO_4'
        self.user.profile.save()
        
        # Debe tener acceso completo a germinaciones
        self.assertTrue(self.user.profile.puede_ver_germinaciones)
        self.assertTrue(self.user.profile.puede_crear_germinaciones)
        self.assertTrue(self.user.profile.puede_editar_germinaciones)
        
        # Debe tener acceso completo a polinizaciones
        self.assertTrue(self.user.profile.puede_ver_polinizaciones)
        self.assertTrue(self.user.profile.puede_crear_polinizaciones)
        self.assertTrue(self.user.profile.puede_editar_polinizaciones)
        
        # Debe tener acceso completo a reportes
        self.assertTrue(self.user.profile.puede_ver_reportes)
        self.assertTrue(self.user.profile.puede_generar_reportes)
        self.assertTrue(self.user.profile.puede_exportar_datos)
        
        # Debe ser administrador
        self.assertTrue(self.user.profile.puede_administrar_usuarios)
        self.assertTrue(self.user.profile.puede_ver_estadisticas_globales)

    def test_get_permisos_detallados(self):
        """Test obtener permisos detallados"""
        self.user.profile.rol = 'TIPO_1'
        self.user.profile.save()
        
        permisos = self.user.profile.get_permisos_detallados()
        
        # Verificar estructura
        self.assertIn('germinaciones', permisos)
        self.assertIn('polinizaciones', permisos)
        self.assertIn('reportes', permisos)
        self.assertIn('administracion', permisos)
        
        # Verificar permisos específicos
        self.assertTrue(permisos['germinaciones']['ver'])
        self.assertTrue(permisos['germinaciones']['crear'])
        self.assertTrue(permisos['germinaciones']['editar'])
        
        self.assertTrue(permisos['polinizaciones']['ver'])
        self.assertTrue(permisos['polinizaciones']['crear'])
        self.assertTrue(permisos['polinizaciones']['editar'])
        
        self.assertTrue(permisos['reportes']['ver'])
        self.assertTrue(permisos['reportes']['generar'])
        self.assertTrue(permisos['reportes']['exportar'])
        
        self.assertFalse(permisos['administracion']['usuarios'])
        self.assertTrue(permisos['administracion']['estadisticas_globales'])


class MetasRendimientoTest(TestCase):
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='test_user',
            password='test123'
        )

    def test_metas_segun_rol_tipo_1(self):
        """Test metas para TIPO_1"""
        self.user.profile.rol = 'TIPO_1'
        self.user.profile.save()
        
        # Puede tener ambas metas
        self.assertTrue(self.user.profile.puede_tener_meta_polinizaciones())
        self.assertTrue(self.user.profile.puede_tener_meta_germinaciones())

    def test_metas_segun_rol_tipo_2(self):
        """Test metas para TIPO_2"""
        self.user.profile.rol = 'TIPO_2'
        self.user.profile.save()
        
        # Solo puede tener meta de polinizaciones
        self.assertTrue(self.user.profile.puede_tener_meta_polinizaciones())
        self.assertFalse(self.user.profile.puede_tener_meta_germinaciones())

    def test_metas_segun_rol_tipo_3(self):
        """Test metas para TIPO_3"""
        self.user.profile.rol = 'TIPO_3'
        self.user.profile.save()
        
        # Solo puede tener meta de germinaciones
        self.assertFalse(self.user.profile.puede_tener_meta_polinizaciones())
        self.assertTrue(self.user.profile.puede_tener_meta_germinaciones())

    def test_validar_metas_segun_rol(self):
        """Test validación de metas según rol"""
        self.user.profile.rol = 'TIPO_2'  # Solo polinizaciones
        self.user.profile.meta_germinaciones = 10  # Inválido para este rol
        self.user.profile.save()
        
        errores = self.user.profile.validar_metas_segun_rol()
        self.assertTrue(len(errores) > 0)
        self.assertIn('no puede tener meta de germinaciones', errores[0])

    def test_progreso_metas(self):
        """Test cálculo de progreso de metas"""
        self.user.profile.meta_polinizaciones = 10
        self.user.profile.polinizaciones_actuales = 3
        self.user.profile.save()
        
        progreso = self.user.profile.obtener_progreso_meta_polinizaciones()
        self.assertEqual(progreso, 30.0)
        
        estado = self.user.profile.obtener_estado_meta_polinizaciones()
        self.assertEqual(estado, 'En Progreso')

    def test_progreso_meta_completada(self):
        """Test meta completada"""
        self.user.profile.meta_germinaciones = 5
        self.user.profile.germinaciones_actuales = 8  # Más de la meta
        self.user.profile.save()
        
        progreso = self.user.profile.obtener_progreso_meta_germinaciones()
        self.assertEqual(progreso, 100.0)  # Máximo 100%
        
        estado = self.user.profile.obtener_estado_meta_germinaciones()
        self.assertEqual(estado, 'Completada')


class PermissionsTest(APITestCase):
    def setUp(self):
        """Configuración inicial"""
        # Crear usuarios con diferentes roles
        self.admin_user = User.objects.create_user(
            username='admin', password='test123'
        )
        self.admin_user.profile.rol = 'TIPO_4'
        self.admin_user.profile.save()
        
        self.pol_user = User.objects.create_user(
            username='pol_user', password='test123'
        )
        self.pol_user.profile.rol = 'TIPO_2'
        self.pol_user.profile.save()
        
        self.ger_user = User.objects.create_user(
            username='ger_user', password='test123'
        )
        self.ger_user.profile.rol = 'TIPO_3'
        self.ger_user.profile.save()
        
        self.client = APIClient()

    def test_acceso_germinaciones_con_permisos(self):
        """Test acceso a germinaciones con permisos"""
        self.client.force_authenticate(user=self.ger_user)
        
        response = self.client.get('/api/germinaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_acceso_germinaciones_sin_permisos(self):
        """Test acceso a germinaciones sin permisos"""
        self.client.force_authenticate(user=self.pol_user)
        
        response = self.client.get('/api/germinaciones/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_acceso_polinizaciones_con_permisos(self):
        """Test acceso a polinizaciones con permisos"""
        self.client.force_authenticate(user=self.pol_user)
        
        response = self.client.get('/api/polinizaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_acceso_polinizaciones_sin_permisos(self):
        """Test acceso a polinizaciones sin permisos"""
        self.client.force_authenticate(user=self.ger_user)
        
        response = self.client.get('/api/polinizaciones/')
        self.assertEqual(response.status_status, status.HTTP_403_FORBIDDEN)

    def test_crear_germinacion_con_permisos(self):
        """Test crear germinación con permisos"""
        self.client.force_authenticate(user=self.ger_user)
        
        data = {
            'codigo': 'GER001',
            'especie_variedad': 'Test',
            'fecha_siembra': date.today().isoformat(),
            'cantidad_solicitada': 100,
            'no_capsulas': 5,
            'responsable': 'Test User'
        }
        
        response = self.client.post('/api/germinaciones/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_crear_germinacion_sin_permisos(self):
        """Test crear germinación sin permisos"""
        self.client.force_authenticate(user=self.pol_user)
        
        data = {
            'codigo': 'GER001',
            'especie_variedad': 'Test',
            'fecha_siembra': date.today().isoformat(),
            'cantidad_solicitada': 100,
            'no_capsulas': 5,
            'responsable': 'Test User'
        }
        
        response = self.client.post('/api/germinaciones/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_administrador_acceso_total(self):
        """Test que el administrador tenga acceso total"""
        self.client.force_authenticate(user=self.admin_user)
        
        # Debe poder acceder a germinaciones
        response = self.client.get('/api/germinaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Debe poder acceder a polinizaciones
        response = self.client.get('/api/polinizaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Debe poder acceder a gestión de usuarios
        response = self.client.get('/api/user-management/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class IntegrationRBACTest(APITestCase):
    def setUp(self):
        """Configuración para tests de integración"""
        self.pol_user = User.objects.create_user(
            username='pol_specialist',
            password='test123'
        )
        self.pol_user.profile.rol = 'TIPO_2'
        self.pol_user.profile.save()
        
        self.ger_user = User.objects.create_user(
            username='ger_specialist',
            password='test123'
        )
        self.ger_user.profile.rol = 'TIPO_3'
        self.ger_user.profile.save()
        
        self.client = APIClient()

    def test_flujo_completo_especialista_polinizacion(self):
        """Test flujo completo para especialista en polinización"""
        self.client.force_authenticate(user=self.pol_user)
        
        # 1. Debe poder crear polinización
        pol_data = {
            'fechapol': date.today().isoformat(),
            'codigo': 'POL001',
            'genero': 'Cattleya',
            'especie': 'aurantiaca',
            'tipo_polinizacion': 'SELF',
            'madre_genero': 'Cattleya',
            'madre_especie': 'aurantiaca',
            'padre_genero': 'Cattleya',
            'padre_especie': 'aurantiaca',
            'nueva_genero': 'Cattleya',
            'nueva_especie': 'aurantiaca',
            'ubicacion_tipo': 'vivero',
            'cantidad_capsulas': 5,
            'responsable': 'Pol Specialist'
        }
        
        response = self.client.post('/api/polinizaciones/', pol_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Debe poder ver sus polinizaciones
        response = self.client.get('/api/polinizaciones/mis-polinizaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # 3. NO debe poder crear germinaciones
        ger_data = {
            'codigo': 'GER001',
            'especie_variedad': 'Test',
            'fecha_siembra': date.today().isoformat(),
            'cantidad_solicitada': 100,
            'no_capsulas': 5,
            'responsable': 'Pol Specialist'
        }
        
        response = self.client.post('/api/germinaciones/', ger_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 4. NO debe poder ver germinaciones
        response = self.client.get('/api/germinaciones/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_flujo_completo_especialista_germinacion(self):
        """Test flujo completo para especialista en germinación"""
        self.client.force_authenticate(user=self.ger_user)
        
        # 1. Debe poder crear germinación
        ger_data = {
            'codigo': 'GER001',
            'especie_variedad': 'Cattleya aurantiaca',
            'fecha_siembra': date.today().isoformat(),
            'fecha_polinizacion': (date.today() - timedelta(days=30)).isoformat(),
            'clima': 'I',
            'percha': '131',
            'nivel': '1',
            'cantidad_solicitada': 100,
            'no_capsulas': 5,
            'responsable': 'Ger Specialist'
        }
        
        response = self.client.post('/api/germinaciones/', ger_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # 2. Debe poder ver sus germinaciones
        response = self.client.get('/api/germinaciones/mis_germinaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        
        # 3. NO debe poder crear polinizaciones
        pol_data = {
            'fechapol': date.today().isoformat(),
            'codigo': 'POL001',
            'genero': 'Cattleya',
            'especie': 'aurantiaca',
            'responsable': 'Ger Specialist'
        }
        
        response = self.client.post('/api/polinizaciones/', pol_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # 4. NO debe poder ver polinizaciones
        response = self.client.get('/api/polinizaciones/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_aislamiento_datos_entre_usuarios(self):
        """Test que los usuarios solo vean sus propios datos"""
        # Crear datos para cada usuario
        pol_polinizacion = Polinizacion.objects.create(
            fechapol=date.today(),
            codigo='POL_POL',
            genero='Cattleya',
            especie='aurantiaca',
            creado_por=self.pol_user
        )
        
        ger_germinacion = Germinacion.objects.create(
            codigo='GER_GER',
            especie_variedad='Cattleya aurantiaca',
            fecha_siembra=date.today(),
            cantidad_solicitada=100,
            no_capsulas=5,
            creado_por=self.ger_user
        )
        
        # Usuario de polinización solo ve sus polinizaciones
        self.client.force_authenticate(user=self.pol_user)
        response = self.client.get('/api/polinizaciones/mis-polinizaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['codigo'], 'POL_POL')
        
        # Usuario de germinación solo ve sus germinaciones
        self.client.force_authenticate(user=self.ger_user)
        response = self.client.get('/api/germinaciones/mis_germinaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['codigo'], 'GER_GER')