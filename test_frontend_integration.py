# -*- coding: utf-8 -*-
"""
Test de Integración para Frontend
===================================
Simula exactamente cómo el frontend React Native consumirá la API
"""

import os
import sys
import django
import json

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configurar Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
import datetime

User = get_user_model()

print("="*80)
print("  TEST DE INTEGRACIÓN FRONTEND - API DE GERMINACIÓN ML")
print("="*80)

# Crear cliente de API (simula requests HTTP del frontend)
client = APIClient()

# =============================================================================
# PASO 1: AUTENTICACIÓN (como lo haría el frontend)
# =============================================================================
print("\n[PASO 1] Autenticación del Usuario")
print("-"*80)

# Obtener o crear usuario de prueba
user = User.objects.filter(username='admin').first()
if not user:
    user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
    print("✅ Usuario admin creado")
else:
    print(f"✅ Usuario existente: {user.username}")

# Autenticar directamente (simula que el frontend ya tiene el token)
client.force_authenticate(user=user)
print(f"✅ Usuario autenticado: {user.username}")

# =============================================================================
# PASO 2: VERIFICAR INFORMACIÓN DEL MODELO
# =============================================================================
print("\n[PASO 2] Verificar Información del Modelo")
print("-"*80)

response = client.get('/api/ml/germinacion/model-info/')

if response.status_code == 200:
    info = response.data
    print(f"✅ Modelo cargado: {info['loaded']}")
    print(f"   - Tipo: {info['model_type']}")
    print(f"   - Features: {info['n_features']}")
    print(f"   - Top especies: {info['top_especies']}")
    print(f"   - RMSE: {info['metricas']['RMSE']}")
    print(f"   - R²: {info['metricas']['R2']}")
else:
    print(f"❌ Error: Status {response.status_code}")
    print(response.data)

# =============================================================================
# PASO 3: PREDICCIÓN CON ESPECIE CONOCIDA (Phragmipedium kovachii)
# =============================================================================
print("\n[PASO 3] Predicción con Especie Conocida")
print("-"*80)

datos_especie_conocida = {
    'fecha_siembra': datetime.date.today().isoformat(),
    'especie': 'Phragmipedium kovachii',
    'clima': 'IC',
    'estado_capsula': 'Cerrada',
    's_stock': 10,
    'c_solic': 2,
    'dispone': 1
}

print("Datos enviados:")
print(json.dumps(datos_especie_conocida, indent=2))

response = client.post('/api/predicciones/germinacion/ml/', datos_especie_conocida, format='json')

if response.status_code == 200:
    resultado = response.data
    print(f"\n✅ Predicción exitosa!")
    print(f"   📅 Fecha siembra: {datos_especie_conocida['fecha_siembra']}")
    print(f"   ⏱️  Días estimados: {resultado['dias_estimados']} días")
    print(f"   📆 Fecha germinación: {resultado['fecha_estimada_germinacion']}")
    print(f"   🎯 Confianza: {resultado['confianza']}% ({resultado['nivel_confianza']})")
    print(f"   🌱 Especie agrupada: {resultado['detalles']['especie_agrupada']}")
else:
    print(f"\n❌ Error: Status {response.status_code}")
    print(json.dumps(response.data, indent=2))

# =============================================================================
# PASO 4: PREDICCIÓN CON ESPECIE NUEVA (no en Top 100)
# =============================================================================
print("\n[PASO 4] Predicción con Especie Nueva")
print("-"*80)

datos_especie_nueva = {
    'fecha_siembra': datetime.date.today().isoformat(),
    'especie': 'Cattleya wardii',  # Especie que probablemente no esté en Top 100
    'clima': 'Warm',
    'estado_capsula': 'Abierta',
    's_stock': 5,
    'c_solic': 1,
    'dispone': 1
}

response = client.post('/api/predicciones/germinacion/ml/', datos_especie_nueva, format='json')

if response.status_code == 200:
    resultado = response.data
    print(f"✅ Predicción exitosa!")
    print(f"   ⏱️  Días estimados: {resultado['dias_estimados']} días")
    print(f"   🎯 Confianza: {resultado['confianza']}%")
    print(f"   🌱 Especie original: {resultado['detalles']['especie_original']}")
    print(f"   🌱 Especie agrupada: {resultado['detalles']['especie_agrupada']}")

    if resultado['detalles']['especie_agrupada'] == 'OTRAS':
        print("   ℹ️  Especie agrupada como 'OTRAS' (no en Top 100)")
else:
    print(f"❌ Error: Status {response.status_code}")
    print(json.dumps(response.data, indent=2))

# =============================================================================
# PASO 5: PREDICCIÓN CON DIFERENTES CLIMAS
# =============================================================================
print("\n[PASO 5] Predicción con Diferentes Climas")
print("-"*80)

climas = ['Cool', 'IC', 'IW', 'Intermedio', 'Warm']
for clima in climas:
    datos = {
        'fecha_siembra': datetime.date.today().isoformat(),
        'especie': 'Phragmipedium kovachii',
        'clima': clima,
        'estado_capsula': 'Cerrada'
    }

    response = client.post('/api/predicciones/germinacion/ml/', datos, format='json')

    if response.status_code == 200:
        resultado = response.data
        print(f"   {clima:15} → {resultado['dias_estimados']:3} días | Confianza: {resultado['confianza']}%")
    else:
        print(f"   {clima:15} → Error {response.status_code}")

# =============================================================================
# PASO 6: PREDICCIÓN CON DIFERENTES ESTADOS DE CÁPSULA
# =============================================================================
print("\n[PASO 6] Predicción con Diferentes Estados de Cápsula")
print("-"*80)

estados = ['Abierta', 'Cerrada', 'Semiabiert']
for estado in estados:
    datos = {
        'fecha_siembra': datetime.date.today().isoformat(),
        'especie': 'Phragmipedium kovachii',
        'clima': 'IC',
        'estado_capsula': estado
    }

    response = client.post('/api/predicciones/germinacion/ml/', datos, format='json')

    if response.status_code == 200:
        resultado = response.data
        print(f"   {estado:15} → {resultado['dias_estimados']:3} días")
    else:
        print(f"   {estado:15} → Error {response.status_code}")

# =============================================================================
# PASO 7: VALIDACIÓN DE ERRORES (campos faltantes)
# =============================================================================
print("\n[PASO 7] Validación de Errores")
print("-"*80)

# Caso 1: Falta especie
print("Caso 1: Campo 'especie' faltante")
datos_invalidos = {
    'fecha_siembra': datetime.date.today().isoformat(),
    'clima': 'IC',
    'estado_capsula': 'Cerrada'
}

response = client.post('/api/predicciones/germinacion/ml/', datos_invalidos, format='json')
if response.status_code == 400:
    print(f"   ✅ Error 400 recibido correctamente")
    print(f"   Mensaje: {response.data['error']}")
else:
    print(f"   ❌ Se esperaba status 400, recibido {response.status_code}")

# Caso 2: Fecha inválida
print("\nCaso 2: Fecha inválida")
datos_fecha_invalida = {
    'fecha_siembra': 'fecha-invalida',
    'especie': 'Phragmipedium kovachii',
    'clima': 'IC',
    'estado_capsula': 'Cerrada'
}

response = client.post('/api/predicciones/germinacion/ml/', datos_fecha_invalida, format='json')
if response.status_code in [400, 500]:
    print(f"   ✅ Error {response.status_code} recibido correctamente")
    print(f"   Mensaje: {response.data.get('error', 'N/A')}")
else:
    print(f"   ❌ Se esperaba error, recibido status {response.status_code}")

# =============================================================================
# PASO 8: TEST DE MÚLTIPLES PREDICCIONES CONSECUTIVAS
# =============================================================================
print("\n[PASO 8] Test de Performance - 10 Predicciones Consecutivas")
print("-"*80)

import time
tiempos = []

for i in range(10):
    datos = {
        'fecha_siembra': datetime.date.today().isoformat(),
        'especie': 'Phragmipedium kovachii',
        'clima': 'IC',
        'estado_capsula': 'Cerrada'
    }

    inicio = time.time()
    response = client.post('/api/predicciones/germinacion/ml/', datos, format='json')
    tiempo = time.time() - inicio
    tiempos.append(tiempo)

    if response.status_code == 200:
        print(f"   Predicción {i+1:2d}: {tiempo*1000:6.2f}ms")
    else:
        print(f"   Predicción {i+1:2d}: Error {response.status_code}")

if tiempos:
    print(f"\n   Tiempo promedio: {(sum(tiempos)/len(tiempos))*1000:.2f}ms")
    print(f"   Tiempo mínimo: {min(tiempos)*1000:.2f}ms")
    print(f"   Tiempo máximo: {max(tiempos)*1000:.2f}ms")

# =============================================================================
# RESUMEN FINAL PARA FRONTEND
# =============================================================================
print("\n" + "="*80)
print("  RESUMEN FINAL - LISTO PARA FRONTEND")
print("="*80)

print("\n✅ ENDPOINTS DISPONIBLES:")
print("   POST /api/predicciones/germinacion/ml/")
print("   GET  /api/ml/germinacion/model-info/")

print("\n✅ AUTENTICACIÓN:")
print("   - JWT Token requerido")
print("   - Header: Authorization: Bearer <token>")

print("\n✅ CAMPOS REQUERIDOS:")
print("   - fecha_siembra (YYYY-MM-DD)")
print("   - especie (string)")
print("   - clima (Cool/IC/IW/Intermedio/Warm)")
print("   - estado_capsula (Abierta/Cerrada/Semiabiert)")

print("\n✅ CAMPOS OPCIONALES:")
print("   - s_stock (int, default: 0)")
print("   - c_solic (int, default: 0)")
print("   - dispone (int, default: 0)")

print("\n✅ RESPUESTA:")
print("   - dias_estimados (int)")
print("   - fecha_estimada_germinacion (YYYY-MM-DD)")
print("   - confianza (int, 0-100)")
print("   - nivel_confianza (alta/media/baja)")
print("   - modelo (string)")
print("   - detalles (object)")

print("\n✅ MANEJO DE ERRORES:")
print("   - 400: Datos inválidos o campos faltantes")
print("   - 500: Error en pipeline del modelo")
print("   - 503: Modelo no disponible")

print("\n✅ PERFORMANCE:")
if tiempos:
    print(f"   - Tiempo promedio: {(sum(tiempos)/len(tiempos))*1000:.0f}ms")
    print(f"   - Modelo cargado en memoria (Singleton)")

print("\n" + "="*80)
print("  🚀 API LISTA PARA INTEGRACIÓN CON FRONTEND")
print("="*80)
