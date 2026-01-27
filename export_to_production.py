"""
Script para exportar datos de local a producción
"""
import requests
import json
from django.contrib.auth.models import User
from laboratorio.core.models import UserProfile, Germinacion, Polinizacion, Genero, Especie, Ubicacion

# Configuración del servidor de producción
PROD_URL = "http://207.180.230.88/api"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

def get_prod_token():
    """Obtener token de producción"""
    response = requests.post(f"{PROD_URL}/login/", json={
        "username": ADMIN_USER,
        "password": ADMIN_PASS
    })
    if response.status_code == 200:
        return response.json()['access']
    else:
        raise Exception(f"Error login: {response.status_code} - {response.text}")

def export_germinaciones_batch(token, batch_size=100):
    """Exportar germinaciones en lotes"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    total = Germinacion.objects.count()
    print(f"\nExportando {total} germinaciones...")

    success_count = 0
    error_count = 0

    # Procesar en lotes
    for i in range(0, total, batch_size):
        germinaciones = Germinacion.objects.all()[i:i+batch_size]

        for germ in germinaciones:
            try:
                data = {
                    "codigo": germ.codigo,
                    "especie": germ.especie,
                    "genero": germ.genero,
                    "clima": germ.clima,
                    "responsable": germ.responsable,
                    "estado_capsulas": germ.estado_capsulas,
                    "cantidad_solicitada": germ.cantidad_solicitada,
                    "percha": germ.percha,
                    "nivel": germ.nivel,
                    # Agregar más campos según necesites
                }

                response = requests.post(
                    f"{PROD_URL}/germinaciones/",
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    success_count += 1
                    if success_count % 10 == 0:
                        print(f"  Exportadas: {success_count}/{total}")
                else:
                    error_count += 1
                    print(f"  ERROR en {germ.codigo}: {response.status_code}")

            except Exception as e:
                error_count += 1
                print(f"  ERROR en {germ.codigo}: {str(e)}")

    print(f"\nResumen Germinaciones:")
    print(f"  Exitosas: {success_count}")
    print(f"  Errores: {error_count}")

    return success_count, error_count

def export_polinizaciones_batch(token, batch_size=100):
    """Exportar polinizaciones en lotes"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    total = Polinizacion.objects.count()
    print(f"\nExportando {total} polinizaciones...")

    success_count = 0
    error_count = 0

    # Procesar en lotes
    for i in range(0, total, batch_size):
        polinizaciones = Polinizacion.objects.all()[i:i+batch_size]

        for poli in polinizaciones:
            try:
                data = {
                    "codigo": poli.codigo,
                    "madre_genero": poli.madre_genero,
                    "madre_especie": poli.madre_especie,
                    "padre_genero": poli.padre_genero,
                    "padre_especie": poli.padre_especie,
                    "responsable": poli.responsable,
                    "estado_polinizacion": poli.estado_polinizacion,
                    # Agregar más campos según necesites
                }

                response = requests.post(
                    f"{PROD_URL}/polinizaciones/",
                    headers=headers,
                    json=data,
                    timeout=30
                )

                if response.status_code in [200, 201]:
                    success_count += 1
                    if success_count % 10 == 0:
                        print(f"  Exportadas: {success_count}/{total}")
                else:
                    error_count += 1
                    print(f"  ERROR en {poli.codigo}: {response.status_code}")

            except Exception as e:
                error_count += 1
                print(f"  ERROR en {poli.codigo}: {str(e)}")

    print(f"\nResumen Polinizaciones:")
    print(f"  Exitosas: {success_count}")
    print(f"  Errores: {error_count}")

    return success_count, error_count

def main():
    """Función principal"""
    print("="*60)
    print("EXPORTACIÓN DE DATOS A PRODUCCIÓN")
    print("="*60)

    # Estadísticas locales
    total_germ = Germinacion.objects.count()
    total_poli = Polinizacion.objects.count()

    print(f"\nDatos en base de datos LOCAL:")
    print(f"  Germinaciones: {total_germ}")
    print(f"  Polinizaciones: {total_poli}")

    # Obtener token de producción
    print(f"\nConectando a producción ({PROD_URL})...")
    try:
        token = get_prod_token()
        print("✓ Token obtenido exitosamente")
    except Exception as e:
        print(f"✗ Error obteniendo token: {e}")
        return

    # Preguntar confirmación
    respuesta = input(f"\n¿Deseas exportar {total_germ + total_poli} registros a producción? (si/no): ")
    if respuesta.lower() != 'si':
        print("Exportación cancelada.")
        return

    # Exportar germinaciones
    germ_success, germ_errors = export_germinaciones_batch(token, batch_size=50)

    # Exportar polinizaciones
    poli_success, poli_errors = export_polinizaciones_batch(token, batch_size=50)

    print("\n" + "="*60)
    print("EXPORTACIÓN COMPLETADA")
    print("="*60)
    print(f"Germinaciones exportadas: {germ_success}/{total_germ}")
    print(f"Polinizaciones exportadas: {poli_success}/{total_poli}")
    print(f"Total errores: {germ_errors + poli_errors}")

if __name__ == "__main__":
    main()
