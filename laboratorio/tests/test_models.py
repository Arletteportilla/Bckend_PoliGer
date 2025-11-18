"""
Tests para los modelos del sistema de laboratorio
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import date, timedelta
from laboratorio.models import (
    Genero, Especie, Variedad, Polinizacion, 
    Germinacion, UserProfile
)


class GeneroModelTest(TestCase):
    def test_crear_genero(self):
        """Test crear género"""
        genero = Genero.objects.create(nombre="Cattleya")
        self.assertEqual(genero.nombre, "Cattleya")
        self.assertEqual(str(genero), "Cattleya")

    def test_genero_nombre_unico(self):
        """Test que el nombre del género sea único"""
        Genero.objects.create(nombre="Cattleya")
        with self.assertRaises(Exception):
            Genero.objects.create(nombre="Cattleya")


class EspecieModelTest(TestCase):
    def setUp(self):
        self.genero = Genero.objects.create(nombre="Cattleya")

    def test_crear_especie(self):
        """Test crear especie"""
        especie = Especie.objects.create(
            nombre="aurantiaca",
            genero=self.genero
        )
        self.assertEqual(especie.nombre, "aurantiaca")
        self.assertEqual(especie.genero, self.genero)
        self.assertEqual(str(especie), "Cattleya aurantiaca")


class PolinizacionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_crear_polinizacion(self):
        """Test crear polinización"""
        polinizacion = Polinizacion.objects.create(
            fechapol=date.today(),
            codigo="POL001",
            genero="Cattleya",
            especie="aurantiaca",
            tipo_polinizacion="SELF",
            responsable="Test User",
            creado_por=self.user
        )
        
        self.assertEqual(polinizacion.codigo, "POL001")
        self.assertEqual(polinizacion.genero, "Cattleya")
        self.assertEqual(polinizacion.creado_por, self.user)

    def test_codigo_unico(self):
        """Test que el código sea único"""
        Polinizacion.objects.create(
            fechapol=date.today(),
            codigo="POL001",
            genero="Cattleya",
            especie="aurantiaca",
            creado_por=self.user
        )
        
        with self.assertRaises(Exception):
            Polinizacion.objects.create(
                fechapol=date.today(),
                codigo="POL001",
                genero="Dendrobium",
                especie="nobile",
                creado_por=self.user
            )


class GerminacionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_crear_germinacion(self):
        """Test crear germinación"""
        germinacion = Germinacion.objects.create(
            codigo="GER001",
            especie_variedad="Cattleya aurantiaca",
            fecha_siembra=date.today(),
            responsable="Test User",
            creado_por=self.user,
            cantidad_solicitada=100,
            no_capsulas=5
        )
        
        self.assertEqual(germinacion.codigo, "GER001")
        self.assertEqual(germinacion.especie_variedad, "Cattleya aurantiaca")
        self.assertEqual(germinacion.creado_por, self.user)

    def test_calcular_dias_polinizacion(self):
        """Test cálculo automático de días de polinización"""
        fecha_pol = date.today() - timedelta(days=30)
        fecha_ing = date.today()
        
        germinacion = Germinacion.objects.create(
            codigo="GER002",
            especie_variedad="Test",
            fecha_polinizacion=fecha_pol,
            fecha_ingreso=fecha_ing,
            responsable="Test User",
            creado_por=self.user,
            cantidad_solicitada=50,
            no_capsulas=3
        )
        
        # El modelo debería calcular automáticamente los días
        self.assertEqual(germinacion.dias_polinizacion, 30)


class UserProfileModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )

    def test_crear_perfil_automatico(self):
        """Test que se cree automáticamente el perfil"""
        # El perfil se crea automáticamente por la señal
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.rol, 'TIPO_3')  # Rol por defecto

    def test_permisos_tipo_1(self):
        """Test permisos para TIPO_1"""
        self.user.profile.rol = 'TIPO_1'
        self.user.profile.save()
        
        self.assertTrue(self.user.profile.puede_ver_germinaciones)
        self.assertTrue(self.user.profile.puede_crear_germinaciones)
        self.assertTrue(self.user.profile.puede_ver_polinizaciones)
        self.assertTrue(self.user.profile.puede_crear_polinizaciones)
        self.assertTrue(self.user.profile.puede_ver_reportes)
        self.assertFalse(self.user.profile.puede_administrar_usuarios)

    def test_permisos_tipo_2(self):
        """Test permisos para TIPO_2"""
        self.user.profile.rol = 'TIPO_2'
        self.user.profile.save()
        
        self.assertFalse(self.user.profile.puede_ver_germinaciones)
        self.assertFalse(self.user.profile.puede_crear_germinaciones)
        self.assertTrue(self.user.profile.puede_ver_polinizaciones)
        self.assertTrue(self.user.profile.puede_crear_polinizaciones)
        self.assertFalse(self.user.profile.puede_ver_reportes)

    def test_permisos_tipo_3(self):
        """Test permisos para TIPO_3"""
        self.user.profile.rol = 'TIPO_3'
        self.user.profile.save()
        
        self.assertTrue(self.user.profile.puede_ver_germinaciones)
        self.assertTrue(self.user.profile.puede_crear_germinaciones)
        self.assertFalse(self.user.profile.puede_ver_polinizaciones)
        self.assertFalse(self.user.profile.puede_crear_polinizaciones)
        self.assertFalse(self.user.profile.puede_ver_reportes)

    def test_permisos_tipo_4(self):
        """Test permisos para TIPO_4 (Administrador)"""
        self.user.profile.rol = 'TIPO_4'
        self.user.profile.save()
        
        self.assertTrue(self.user.profile.puede_ver_germinaciones)
        self.assertTrue(self.user.profile.puede_crear_germinaciones)
        self.assertTrue(self.user.profile.puede_ver_polinizaciones)
        self.assertTrue(self.user.profile.puede_crear_polinizaciones)
        self.assertTrue(self.user.profile.puede_ver_reportes)
        self.assertTrue(self.user.profile.puede_administrar_usuarios)

    def test_validar_metas_segun_rol(self):
        """Test validación de metas según rol"""
        # TIPO_2 no puede tener meta de germinaciones
        self.user.profile.rol = 'TIPO_2'
        self.user.profile.meta_germinaciones = 10
        
        errores = self.user.profile.validar_metas_segun_rol()
        self.assertIn("no puede tener meta de germinaciones", errores[0])

    def test_progreso_metas(self):
        """Test cálculo de progreso de metas"""
        self.user.profile.meta_polinizaciones = 10
        self.user.profile.polinizaciones_actuales = 5
        
        progreso = self.user.profile.obtener_progreso_meta_polinizaciones()
        self.assertEqual(progreso, 50.0)
        
        estado = self.user.profile.obtener_estado_meta_polinizaciones()
        self.assertEqual(estado, 'En Progreso')