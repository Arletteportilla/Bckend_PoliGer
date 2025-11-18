"""
Tests para las vistas del sistema de laboratorio
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
import json

from laboratorio.models import (
    Polinizacion, Germinacion, UserProfile, Notification
)


class PolinizacionViewSetTest(APITestCase):
    def setUp(self):
        """Configuración inicial para tests"""
        # Crear usuarios de prueba
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='test123',
            email='admin@test.com'
        )
        self.admin_user.profile.rol = 'TIPO_4'
        self.admin_user.profile.save()
        
        self.pol_user = User.objects.create_user(
            username='pol_test',
            password='test123',
            email='pol@test.com'
        )
        self.pol_user.profile.rol = 'TIPO_2'
        self.pol_user.profile.save()
        
        self.ger_user = User.objects.create_user(
            username='ger_test',
            password='test123',
            email='ger@test.com'
        )
        self.ger_user.profile.rol = 'TIPO_3'
        self.ger_user.profile.save()
        
        # Crear datos de prueba
        self.polinizacion_data = {
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
            'ubicacion_nombre': 'Vivero 1',
            'cantidad_capsulas': 5,
            'responsable': 'Test User'
        }
        
        self.client = APIClient()

    def test_crear_polinizacion_con_permisos(self):
        """Test crear polinización con usuario que tiene permisos"""
        self.client.force_authenticate(user=self.pol_user)
        
        response = self.client.post(
            '/api/polinizaciones/',
            self.polinizacion_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Polinizacion.objects.count(), 1)
        
        polinizacion = Polinizacion.objects.first()
        self.assertEqual(polinizacion.codigo, 'POL001')
        self.assertEqual(polinizacion.creado_por, self.pol_user)

    def test_crear_polinizacion_sin_permisos(self):
        """Test crear polinización con usuario sin permisos"""
        self.client.force_authenticate(user=self.ger_user)
        
        response = self.client.post(
            '/api/polinizaciones/',
            self.polinizacion_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Polinizacion.objects.count(), 0)

    def test_listar_polinizaciones(self):
        """Test listar polinizaciones"""
        # Crear polinización
        Polinizacion.objects.create(
            fechapol=date.today(),
            codigo='POL001',
            genero='Cattleya',
            especie='aurantiaca',
            creado_por=self.pol_user
        )
        
        self.client.force_authenticate(user=self.pol_user)
        response = self.client.get('/api/polinizaciones/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_validacion_fecha_futura(self):
        """Test validación de fecha futura"""
        self.client.force_authenticate(user=self.pol_user)
        
        data = self.polinizacion_data.copy()
        data['fechapol'] = (date.today() + timedelta(days=1)).isoformat()
        
        response = self.client.post(
            '/api/polinizaciones/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fechapol', response.data)

    def test_validacion_campos_requeridos(self):
        """Test validación de campos requeridos"""
        self.client.force_authenticate(user=self.pol_user)
        
        data = {}  # Datos vacíos
        
        response = self.client.post(
            '/api/polinizaciones/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('fechapol', response.data)
        self.assertIn('genero', response.data)
        self.assertIn('especie', response.data)

    def test_mis_polinizaciones(self):
        """Test endpoint mis-polinizaciones"""
        # Crear polinizaciones de diferentes usuarios
        Polinizacion.objects.create(
            fechapol=date.today(),
            codigo='POL001',
            genero='Cattleya',
            especie='aurantiaca',
            creado_por=self.pol_user
        )
        
        Polinizacion.objects.create(
            fechapol=date.today(),
            codigo='POL002',
            genero='Dendrobium',
            especie='nobile',
            creado_por=self.admin_user
        )
        
        self.client.force_authenticate(user=self.pol_user)
        response = self.client.get('/api/polinizaciones/mis-polinizaciones/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['codigo'], 'POL001')


class GerminacionViewSetTest(APITestCase):
    def setUp(self):
        """Configuración inicial para tests"""
        self.ger_user = User.objects.create_user(
            username='ger_test',
            password='test123',
            email='ger@test.com'
        )
        self.ger_user.profile.rol = 'TIPO_3'
        self.ger_user.profile.save()
        
        self.pol_user = User.objects.create_user(
            username='pol_test',
            password='test123',
            email='pol@test.com'
        )
        self.pol_user.profile.rol = 'TIPO_2'
        self.pol_user.profile.save()
        
        self.germinacion_data = {
            'codigo': 'GER001',
            'especie_variedad': 'Cattleya aurantiaca',
            'fecha_siembra': date.today().isoformat(),
            'fecha_polinizacion': (date.today() - timedelta(days=30)).isoformat(),
            'clima': 'I',
            'percha': '131',
            'nivel': '1',
            'clima_lab': 'I',
            'cantidad_solicitada': 100,
            'no_capsulas': 5,
            'responsable': 'Test User'
        }
        
        self.client = APIClient()

    def test_crear_germinacion_con_permisos(self):
        """Test crear germinación con usuario que tiene permisos"""
        self.client.force_authenticate(user=self.ger_user)
        
        response = self.client.post(
            '/api/germinaciones/',
            self.germinacion_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Germinacion.objects.count(), 1)
        
        germinacion = Germinacion.objects.first()
        self.assertEqual(germinacion.codigo, 'GER001')
        self.assertEqual(germinacion.creado_por, self.ger_user)

    def test_crear_germinacion_sin_permisos(self):
        """Test crear germinación con usuario sin permisos"""
        self.client.force_authenticate(user=self.pol_user)
        
        response = self.client.post(
            '/api/germinaciones/',
            self.germinacion_data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Germinacion.objects.count(), 0)

    def test_validacion_numeros_positivos(self):
        """Test validación de números positivos"""
        self.client.force_authenticate(user=self.ger_user)
        
        data = self.germinacion_data.copy()
        data['cantidad_solicitada'] = -10
        
        response = self.client.post(
            '/api/germinaciones/',
            data,
            format='json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mis_germinaciones(self):
        """Test endpoint mis-germinaciones"""
        Germinacion.objects.create(
            codigo='GER001',
            especie_variedad='Cattleya aurantiaca',
            fecha_siembra=date.today(),
            cantidad_solicitada=100,
            no_capsulas=5,
            creado_por=self.ger_user
        )
        
        self.client.force_authenticate(user=self.ger_user)
        response = self.client.get('/api/germinaciones/mis_germinaciones/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class NotificationViewSetTest(APITestCase):
    def setUp(self):
        """Configuración inicial para tests"""
        self.user = User.objects.create_user(
            username='test_user',
            password='test123'
        )
        
        self.notification = Notification.objects.create(
            usuario=self.user,
            tipo='NUEVA_GERMINACION',
            titulo='Test Notification',
            mensaje='Test message'
        )
        
        self.client = APIClient()

    def test_listar_notificaciones_usuario(self):
        """Test que solo se muestren notificaciones del usuario"""
        # Crear notificación de otro usuario
        other_user = User.objects.create_user(
            username='other_user',
            password='test123'
        )
        Notification.objects.create(
            usuario=other_user,
            tipo='NUEVA_POLINIZACION',
            titulo='Other Notification',
            mensaje='Other message'
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/notifications/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['titulo'], 'Test Notification')

    def test_marcar_notificacion_leida(self):
        """Test marcar notificación como leída"""
        self.client.force_authenticate(user=self.user)
        
        response = self.client.post(
            f'/api/notifications/{self.notification.id}/marcar_leida/'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que se marcó como leída
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.leida)
        self.assertIsNotNone(self.notification.fecha_lectura)

    def test_marcar_todas_leidas(self):
        """Test marcar todas las notificaciones como leídas"""
        # Crear otra notificación
        Notification.objects.create(
            usuario=self.user,
            tipo='ESTADO_ACTUALIZADO',
            titulo='Another Notification',
            mensaje='Another message'
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/notifications/marcar_todas_leidas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verificar que todas se marcaron como leídas
        notifications = Notification.objects.filter(usuario=self.user)
        for notification in notifications:
            self.assertTrue(notification.leida)

    def test_notificaciones_no_leidas(self):
        """Test endpoint de notificaciones no leídas"""
        # Crear notificación leída
        Notification.objects.create(
            usuario=self.user,
            tipo='ESTADO_ACTUALIZADO',
            titulo='Read Notification',
            mensaje='Read message',
            leida=True
        )
        
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/notifications/no_leidas/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Solo la no leída
        self.assertEqual(response.data[0]['titulo'], 'Test Notification')


class PerformanceTest(APITestCase):
    def setUp(self):
        """Configuración para tests de performance"""
        self.user = User.objects.create_user(
            username='perf_test',
            password='test123'
        )
        self.user.profile.rol = 'TIPO_1'
        self.user.profile.save()
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_paginacion_polinizaciones(self):
        """Test que la paginación funcione correctamente"""
        # Crear múltiples polinizaciones
        for i in range(25):
            Polinizacion.objects.create(
                fechapol=date.today(),
                codigo=f'POL{i:03d}',
                genero='Cattleya',
                especie='aurantiaca',
                creado_por=self.user
            )
        
        # Test primera página
        response = self.client.get('/api/polinizaciones/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 20)  # Tamaño de página por defecto
        self.assertIsNotNone(response.data['next'])
        
        # Test segunda página
        response = self.client.get('/api/polinizaciones/?page=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 5)  # Restantes

    def test_consulta_optimizada_con_select_related(self):
        """Test que las consultas estén optimizadas"""
        # Crear datos relacionados
        polinizacion = Polinizacion.objects.create(
            fechapol=date.today(),
            codigo='POL001',
            genero='Cattleya',
            especie='aurantiaca',
            creado_por=self.user
        )
        
        Germinacion.objects.create(
            codigo='GER001',
            especie_variedad='Cattleya aurantiaca',
            fecha_siembra=date.today(),
            cantidad_solicitada=100,
            no_capsulas=5,
            polinizacion=polinizacion,
            creado_por=self.user
        )
        
        # Verificar que la consulta no genere N+1 queries
        with self.assertNumQueries(3):  # Máximo 3 queries esperadas
            response = self.client.get('/api/germinaciones/')
            self.assertEqual(response.status_code, status.HTTP_200_OK)


class PrediccionPolinizacionAPITest(APITestCase):
    """Tests para los endpoints de predicción de polinización"""
    
    def setUp(self):
        """Configuración inicial para tests de API"""
        # Crear usuario con permisos
        self.user = User.objects.create_user(
            username='test_user',
            password='test123',
            email='test@example.com'
        )
        self.user.profile.rol = 'TIPO_4'  # Admin con todos los permisos
        self.user.profile.save()
        
        # Configurar cliente API
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        # URLs de los endpoints
        self.url_inicial = reverse('prediccion_polinizacion_inicial')
        self.url_refinar = reverse('prediccion_polinizacion_refinar')
        self.url_validar = reverse('prediccion_polinizacion_validar')
        self.url_historial = reverse('prediccion_polinizacion_historial')
    
    @patch('laboratorio.views.generar_inicial')
    def test_prediccion_inicial_exitosa(self, mock_generar_inicial):
        """Test endpoint de predicción inicial exitoso"""
        # Configurar mock
        mock_resultado = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': None,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        mock_generar_inicial.return_value = mock_resultado
        
        # Datos de entrada
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        # Ejecutar request
        response = self.client.post(self.url_inicial, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertIn('prediccion', response.data)
        self.assertEqual(response.data['prediccion']['dias_estimados'], 120)
        
        # Verificar que se llamó la función correcta
        mock_generar_inicial.assert_called_once()
    
    @patch('laboratorio.views.generar_inicial')
    def test_prediccion_inicial_modelo_no_encontrado(self, mock_generar_inicial):
        """Test endpoint cuando el modelo no se encuentra"""
        # Configurar mock para error
        mock_resultado = {
            'error': 'Modelo no encontrado',
            'error_code': 'MODELO_NO_ENCONTRADO',
            'confianza': 0
        }
        mock_generar_inicial.return_value = mock_resultado
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        response = self.client.post(self.url_inicial, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['success'], False)
        self.assertIn('error', response.data)
    
    @patch('laboratorio.views.generar_inicial')
    def test_prediccion_inicial_datos_insuficientes(self, mock_generar_inicial):
        """Test endpoint con datos insuficientes"""
        # Configurar mock para error de datos
        mock_resultado = {
            'error': 'Datos insuficientes',
            'error_code': 'DATOS_INSUFICIENTES',
            'confianza': 0
        }
        mock_generar_inicial.return_value = mock_resultado
        
        data = {
            'especie': None,  # Dato faltante
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        response = self.client.post(self.url_inicial, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
    
    def test_prediccion_inicial_sin_autenticacion(self):
        """Test endpoint sin autenticación"""
        # Remover autenticación
        self.client.force_authenticate(user=None)
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        response = self.client.post(self.url_inicial, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('laboratorio.views.refinar_prediccion_polinizacion')
    def test_refinar_prediccion_exitosa(self, mock_refinar):
        """Test endpoint de refinamiento exitoso"""
        # Configurar mock
        mock_resultado = {
            'dias_estimados': 115,
            'fecha_estimada_semillas': '2024-05-01',
            'confianza': 75,
            'tipo_prediccion': 'refinada'
        }
        mock_refinar.return_value = mock_resultado
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero',
            'fecha_polinizacion': '2024-01-01',
            'tipo_polinizacion': 'artificial'
        }
        
        response = self.client.post(self.url_refinar, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertIn('prediccion', response.data)
        self.assertEqual(response.data['prediccion']['tipo_prediccion'], 'refinada')
        self.assertGreater(response.data['prediccion']['confianza'], 50)
    
    @patch('laboratorio.views.refinar_prediccion_polinizacion')
    def test_refinar_prediccion_fecha_invalida(self, mock_refinar):
        """Test refinamiento con fecha inválida"""
        # Configurar mock para error de fecha
        mock_resultado = {
            'error': 'Error de formato de fecha',
            'error_code': 'FECHA_INVALIDA',
            'confianza': 0
        }
        mock_refinar.return_value = mock_resultado
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero',
            'fecha_polinizacion': 'fecha-invalida'
        }
        
        response = self.client.post(self.url_refinar, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
    
    @patch('laboratorio.views.validar_prediccion_polinizacion')
    def test_validar_prediccion_exitosa(self, mock_validar):
        """Test endpoint de validación exitoso"""
        # Configurar mock
        mock_resultado = {
            'precision': 95.5,
            'diferencia_dias': 2,
            'calidad_prediccion': 'Excelente',
            'dias_reales': 118,
            'fecha_real': '2024-05-03'
        }
        mock_validar.return_value = mock_resultado
        
        prediccion_original = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': '2024-05-01',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        data = {
            'prediccion_original': prediccion_original,
            'fecha_maduracion_real': '2024-05-03'
        }
        
        response = self.client.post(self.url_validar, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertIn('validacion', response.data)
        self.assertEqual(response.data['validacion']['precision'], 95.5)
    
    def test_validar_prediccion_sin_datos(self):
        """Test validación sin datos requeridos"""
        data = {}  # Sin datos
        
        response = self.client.post(self.url_validar, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['success'], False)
        self.assertIn('error', response.data)
    
    @patch('laboratorio.models.PrediccionPolinizacion.objects.filter')
    def test_historial_predicciones_exitoso(self, mock_filter):
        """Test endpoint de historial exitoso"""
        # Configurar mock de queryset
        mock_prediccion = MagicMock()
        mock_prediccion.id = 1
        mock_prediccion.fecha_creacion = '2024-01-01T10:00:00Z'
        mock_prediccion.especie = 'Cattleya'
        mock_prediccion.dias_estimados = 120
        mock_prediccion.precision = 95.5
        
        mock_queryset = MagicMock()
        mock_queryset.order_by.return_value = [mock_prediccion]
        mock_filter.return_value = mock_queryset
        
        response = self.client.get(self.url_historial)
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertIn('predicciones', response.data)
    
    def test_historial_predicciones_sin_autenticacion(self):
        """Test historial sin autenticación"""
        # Remover autenticación
        self.client.force_authenticate(user=None)
        
        response = self.client.get(self.url_historial)
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    @patch('laboratorio.views.generar_inicial')
    def test_manejo_excepcion_inesperada(self, mock_generar_inicial):
        """Test manejo de excepciones inesperadas"""
        # Configurar mock para lanzar excepción
        mock_generar_inicial.side_effect = Exception("Error inesperado")
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        response = self.client.post(self.url_inicial, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.data['success'], False)
        self.assertIn('error', response.data)
    
    def test_metodo_no_permitido(self):
        """Test método HTTP no permitido"""
        # Intentar GET en endpoint que solo acepta POST
        response = self.client.get(self.url_inicial)
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
    
    @patch('laboratorio.views.refinar_prediccion_polinizacion')
    def test_condiciones_climaticas_complejas(self, mock_refinar):
        """Test refinamiento con condiciones climáticas complejas"""
        mock_resultado = {
            'dias_estimados': 110,
            'fecha_estimada_semillas': '2024-04-25',
            'confianza': 85,
            'tipo_prediccion': 'refinada'
        }
        mock_refinar.return_value = mock_resultado
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero',
            'fecha_polinizacion': '2024-01-01',
            'condiciones_climaticas': {
                'temperatura': {
                    'promedio': 25,
                    'minima': 18,
                    'maxima': 32
                },
                'humedad': 75,
                'precipitacion': 45,
                'estacion': 'primavera'
            }
        }
        
        response = self.client.post(self.url_refinar, data, format='json')
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['success'], True)
        self.assertGreater(response.data['prediccion']['confianza'], 80)


class PrediccionPolinizacionPerformanceTest(APITestCase):
    """Tests de rendimiento para endpoints de predicción"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='perf_user',
            password='test123',
            email='perf@example.com'
        )
        self.user.profile.rol = 'TIPO_4'
        self.user.profile.save()
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        
        self.url_inicial = reverse('prediccion_polinizacion_inicial')
    
    @patch('laboratorio.views.generar_inicial')
    def test_tiempo_respuesta_prediccion_inicial(self, mock_generar_inicial):
        """Test tiempo de respuesta del endpoint inicial"""
        import time
        
        # Configurar mock
        mock_resultado = {
            'dias_estimados': 120,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        mock_generar_inicial.return_value = mock_resultado
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        # Medir tiempo de respuesta
        start_time = time.time()
        response = self.client.post(self.url_inicial, data, format='json')
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Verificaciones
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(response_time, 2.0)  # Menos de 2 segundos
    
    @patch('laboratorio.views.generar_inicial')
    def test_multiples_requests_concurrentes(self, mock_generar_inicial):
        """Test múltiples requests concurrentes"""
        import threading
        import time
        
        # Configurar mock
        mock_resultado = {
            'dias_estimados': 120,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        mock_generar_inicial.return_value = mock_resultado
        
        data = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        results = []
        
        def make_request():
            response = self.client.post(self.url_inicial, data, format='json')
            results.append(response.status_code)
        
        # Crear múltiples threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Ejecutar threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        end_time = time.time()
        
        # Verificaciones
        self.assertEqual(len(results), 5)
        self.assertTrue(all(status_code == 200 for status_code in results))
        self.assertLess(end_time - start_time, 5.0)  # Menos de 5 segundos total


class PrediccionPolinizacionIntegrationTest(APITestCase):
    """Tests de integración para el flujo completo de predicciones"""
    
    def setUp(self):
        """Configuración inicial"""
        self.user = User.objects.create_user(
            username='integration_user',
            password='test123',
            email='integration@example.com'
        )
        self.user.profile.rol = 'TIPO_4'
        self.user.profile.save()
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    
    @patch('laboratorio.views.generar_inicial')
    @patch('laboratorio.views.refinar_prediccion_polinizacion')
    @patch('laboratorio.views.validar_prediccion_polinizacion')
    def test_flujo_completo_api(self, mock_validar, mock_refinar, mock_inicial):
        """Test del flujo completo a través de la API"""
        # Configurar mocks
        mock_inicial.return_value = {
            'dias_estimados': 120,
            'fecha_estimada_semillas': None,
            'confianza': 40,
            'tipo_prediccion': 'inicial'
        }
        
        mock_refinar.return_value = {
            'dias_estimados': 115,
            'fecha_estimada_semillas': '2024-05-01',
            'confianza': 75,
            'tipo_prediccion': 'refinada',
            'parametros_usados': {
                'fecha_polinizacion': '2024-01-01'
            }
        }
        
        mock_validar.return_value = {
            'precision': 95.5,
            'diferencia_dias': 2,
            'calidad_prediccion': 'Excelente'
        }
        
        # 1. Predicción inicial
        data_inicial = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero'
        }
        
        response_inicial = self.client.post(
            reverse('prediccion_polinizacion_inicial'),
            data_inicial,
            format='json'
        )
        
        self.assertEqual(response_inicial.status_code, status.HTTP_200_OK)
        self.assertEqual(response_inicial.data['prediccion']['tipo_prediccion'], 'inicial')
        
        # 2. Refinamiento
        data_refinar = {
            'especie': 'Cattleya',
            'clima': 'templado',
            'ubicacion': 'invernadero',
            'fecha_polinizacion': '2024-01-01',
            'tipo_polinizacion': 'artificial'
        }
        
        response_refinar = self.client.post(
            reverse('prediccion_polinizacion_refinar'),
            data_refinar,
            format='json'
        )
        
        self.assertEqual(response_refinar.status_code, status.HTTP_200_OK)
        self.assertEqual(response_refinar.data['prediccion']['tipo_prediccion'], 'refinada')
        self.assertGreater(
            response_refinar.data['prediccion']['confianza'],
            response_inicial.data['prediccion']['confianza']
        )
        
        # 3. Validación
        data_validar = {
            'prediccion_original': response_refinar.data['prediccion'],
            'fecha_maduracion_real': '2024-05-03'
        }
        
        response_validar = self.client.post(
            reverse('prediccion_polinizacion_validar'),
            data_validar,
            format='json'
        )
        
        self.assertEqual(response_validar.status_code, status.HTTP_200_OK)
        self.assertIn('validacion', response_validar.data)
        self.assertGreater(response_validar.data['validacion']['precision'], 90)