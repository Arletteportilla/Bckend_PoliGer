#!/usr/bin/env python
"""
Test para simular el cambio de filtro y verificar la paginacion.
Uso: python manage.py test laboratorio.tests.test_cambio_filtro
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from laboratorio.view_modules.polinizacion_views import PolinizacionViewSet


class CambioFiltroPaginacionTest(TestCase):
    """Tests para verificar el comportamiento de filtros y paginacion."""

    def setUp(self):
        """Configurar datos de prueba."""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.viewset = PolinizacionViewSet()

    def test_carga_inicial_todos_registros(self):
        """Test: Carga inicial con todos los registros."""
        request = self.factory.get('/api/polinizaciones/mis-polinizaciones/', {
            'page': 1,
            'page_size': 20
        })
        request.user = self.user
        self.viewset.request = request
        self.viewset.format_kwarg = None

        response = self.viewset.mis_polinizaciones(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)

    def test_filtro_historicos_pagina_1(self):
        """Test: Cambio a filtro historicos - Pagina 1."""
        request = self.factory.get('/api/polinizaciones/mis-polinizaciones/', {
            'page': 1,
            'page_size': 20,
            'tipo_registro': 'historicos'
        })
        request.user = self.user
        self.viewset.request = request
        self.viewset.format_kwarg = None

        response = self.viewset.mis_polinizaciones(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('total_pages', response.data)
        self.assertIn('current_page', response.data)

    def test_filtro_historicos_pagina_2(self):
        """Test: Historicos - Pagina 2."""
        request = self.factory.get('/api/polinizaciones/mis-polinizaciones/', {
            'page': 2,
            'page_size': 20,
            'tipo_registro': 'historicos'
        })
        request.user = self.user
        self.viewset.request = request
        self.viewset.format_kwarg = None

        response = self.viewset.mis_polinizaciones(request)

        self.assertEqual(response.status_code, 200)

    def test_filtro_nuevos(self):
        """Test: Cambio a filtro nuevos - Pagina 1."""
        request = self.factory.get('/api/polinizaciones/mis-polinizaciones/', {
            'page': 1,
            'page_size': 20,
            'tipo_registro': 'nuevos'
        })
        request.user = self.user
        self.viewset.request = request
        self.viewset.format_kwarg = None

        response = self.viewset.mis_polinizaciones(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)


def run_manual_test():
    """
    Ejecutar test manual fuera de Django TestRunner.
    Uso: python laboratorio/tests/test_cambio_filtro.py
    """
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    django.setup()

    from django.test import RequestFactory
    from django.contrib.auth.models import User
    from laboratorio.view_modules.polinizacion_views import PolinizacionViewSet

    print("Simulando cambio de filtro y verificando paginacion...\n")

    user = User.objects.first()
    if not user:
        print("No hay usuarios en la base de datos")
        return

    print(f"Usuario: {user.username}")

    factory = RequestFactory()
    viewset = PolinizacionViewSet()

    # Test carga inicial
    print("\n1. Carga inicial - TODOS los registros:")
    request = factory.get('/api/polinizaciones/mis-polinizaciones/', {
        'page': 1,
        'page_size': 20
    })
    request.user = user
    viewset.request = request
    viewset.format_kwarg = None

    try:
        response = viewset.mis_polinizaciones(request)
        data = response.data
        print(f"   Status: {response.status_code}")
        print(f"   Total: {data['count']} registros")
        print(f"   Paginas: {data['total_pages']}")
    except Exception as e:
        print(f"   Error: {e}")

    print("\nTest completado")


if __name__ == "__main__":
    run_manual_test()
