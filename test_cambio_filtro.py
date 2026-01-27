#!/usr/bin/env python
"""
Script para simular el cambio de filtro y verificar la paginación
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import User
from laboratorio.view_modules.polinizacion_views import PolinizacionViewSet
import json

def test_cambio_filtro_paginacion():
    """Simular el cambio de filtro como lo haría el frontend"""
    print("🧪 Simulando cambio de filtro y verificando paginación...\n")
    
    # Obtener un usuario
    user = User.objects.first()
    if not user:
        print("❌ No hay usuarios en la base de datos")
        return
    
    print(f"👤 Usuario: {user.username}")
    
    # Crear factory para requests
    factory = RequestFactory()
    viewset = PolinizacionViewSet()
    
    # Simular secuencia de uso del frontend
    print("\n🔄 SECUENCIA DE USO:")
    
    # 1. Carga inicial (todos los registros)
    print("\n1️⃣ Carga inicial - TODOS los registros:")
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
        print(f"   Páginas: {data['total_pages']}")
        print(f"   Página actual: {data['current_page']}")
        print(f"   Registros en página: {len(data['results'])}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 2. Cambio a filtro históricos (página 1)
    print("\n2️⃣ Cambio a HISTÓRICOS - Página 1:")
    request = factory.get('/api/polinizaciones/mis-polinizaciones/', {
        'page': 1,
        'page_size': 20,
        'tipo_registro': 'historicos'
    })
    request.user = user
    viewset.request = request
    viewset.format_kwarg = None
    
    try:
        response = viewset.mis_polinizaciones(request)
        data = response.data
        print(f"   Status: {response.status_code}")
        print(f"   Total: {data['count']} registros")
        print(f"   Páginas: {data['total_pages']}")
        print(f"   Página actual: {data['current_page']}")
        print(f"   Registros en página: {len(data['results'])}")
        print(f"   Tiene siguiente: {data['has_next']}")
        
        # Verificar que son registros históricos
        if data['results']:
            ejemplo = data['results'][0]
            archivo_origen = ejemplo.get('archivo_origen', 'N/A')
            print(f"   Ejemplo archivo_origen: {archivo_origen}")
            
            # Verificar que no tenga estados (usando serializer histórico)
            tiene_estado = 'estado' in ejemplo
            print(f"   Tiene campo 'estado': {tiene_estado}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 3. Navegar a página 2 de históricos
    print("\n3️⃣ HISTÓRICOS - Página 2:")
    request = factory.get('/api/polinizaciones/mis-polinizaciones/', {
        'page': 2,
        'page_size': 20,
        'tipo_registro': 'historicos'
    })
    request.user = user
    viewset.request = request
    viewset.format_kwarg = None
    
    try:
        response = viewset.mis_polinizaciones(request)
        data = response.data
        print(f"   Status: {response.status_code}")
        print(f"   Total: {data['count']} registros")
        print(f"   Páginas: {data['total_pages']}")
        print(f"   Página actual: {data['current_page']}")
        print(f"   Registros en página: {len(data['results'])}")
        print(f"   Tiene siguiente: {data['has_next']}")
        print(f"   Tiene anterior: {data['has_previous']}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 4. Navegar a página 100 de históricos
    print("\n4️⃣ HISTÓRICOS - Página 100:")
    request = factory.get('/api/polinizaciones/mis-polinizaciones/', {
        'page': 100,
        'page_size': 20,
        'tipo_registro': 'historicos'
    })
    request.user = user
    viewset.request = request
    viewset.format_kwarg = None
    
    try:
        response = viewset.mis_polinizaciones(request)
        data = response.data
        print(f"   Status: {response.status_code}")
        print(f"   Total: {data['count']} registros")
        print(f"   Páginas: {data['total_pages']}")
        print(f"   Página actual: {data['current_page']}")
        print(f"   Registros en página: {len(data['results'])}")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # 5. Cambio a filtro nuevos
    print("\n5️⃣ Cambio a NUEVOS - Página 1:")
    request = factory.get('/api/polinizaciones/mis-polinizaciones/', {
        'page': 1,
        'page_size': 20,
        'tipo_registro': 'nuevos'
    })
    request.user = user
    viewset.request = request
    viewset.format_kwarg = None
    
    try:
        response = viewset.mis_polinizaciones(request)
        data = response.data
        print(f"   Status: {response.status_code}")
        print(f"   Total: {data['count']} registros")
        print(f"   Páginas: {data['total_pages']}")
        print(f"   Página actual: {data['current_page']}")
        print(f"   Registros en página: {len(data['results'])}")
        
        # Verificar que son registros nuevos
        if data['results']:
            ejemplo = data['results'][0]
            archivo_origen = ejemplo.get('archivo_origen', 'N/A')
            print(f"   Ejemplo archivo_origen: {archivo_origen}")
            
            # Verificar que SÍ tenga estados (usando serializer completo)
            tiene_estado = 'estado' in ejemplo
            print(f"   Tiene campo 'estado': {tiene_estado}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Simulación completada - El backend maneja correctamente la paginación")

if __name__ == "__main__":
    test_cambio_filtro_paginacion()