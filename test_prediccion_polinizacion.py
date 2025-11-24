"""
Script de prueba para verificar que el sistema de predicción de polinizaciones funciona
"""
import os
import sys
import django

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.services.ml_polinizacion_service import ml_polinizacion_service
from laboratorio.services.polinizacion_service import polinizacion_service
from datetime import date

def test_modelo_cargado():
    """Prueba 1: Verificar que el modelo está cargado"""
    print("="*80)
    print("PRUEBA 1: Verificar carga del modelo")
    print("="*80)
    
    model_info = ml_polinizacion_service.get_model_info()
    
    if model_info['loaded']:
        print("✓ Modelo cargado exitosamente")
        print(f"  - Modelo: {model_info['modelo']}")
        print(f"  - Precisión: {model_info.get('precision_percent', 'N/A')}%")
        print(f"  - MAE: {model_info.get('mae_test', 'N/A')} días")
        print(f"  - Features: {model_info.get('n_features', 'N/A')}")
        print(f"  - Muestras: {model_info.get('n_samples', 'N/A')}")
        return True
    else:
        print("✗ Modelo NO cargado")
        print(f"  Error: {model_info.get('error', 'Desconocido')}")
        return False

def test_prediccion_directa():
    """Prueba 2: Predicción directa con el servicio ML"""
    print("\n" + "="*80)
    print("PRUEBA 2: Predicción directa con ML")
    print("="*80)
    
    try:
        prediccion = ml_polinizacion_service.predecir_dias_maduracion(
            genero='Cattleya',
            especie='maxima',
            tipo='SELF',
            fecha_pol=date(2025, 1, 15),
            cantidad=1
        )
        
        if prediccion:
            print("✓ Predicción exitosa")
            print(f"  - Días estimados: {prediccion['dias_estimados']}")
            print(f"  - Fecha estimada: {prediccion['fecha_estimada']}")
            print(f"  - Método: {prediccion['metodo']}")
            print(f"  - Modelo: {prediccion['modelo']}")
            print(f"  - Confianza: {prediccion['confianza']}%")
            print(f"  - Nivel: {prediccion['nivel_confianza']}")
            print(f"  - Rango: {prediccion['rango_probable']['min']}-{prediccion['rango_probable']['max']} días")
            return True
        else:
            print("✗ No se pudo generar predicción")
            return False
            
    except Exception as e:
        print(f"✗ Error en predicción: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prediccion_servicio():
    """Prueba 3: Predicción a través del servicio de polinización"""
    print("\n" + "="*80)
    print("PRUEBA 3: Predicción a través del servicio de polinización")
    print("="*80)
    
    try:
        prediccion = polinizacion_service.predecir_maduracion(
            genero='Phalaenopsis',
            especie='amabilis',
            tipo='HYBRID',
            fecha_pol=date(2025, 2, 1),
            cantidad=2
        )
        
        if prediccion:
            print("✓ Predicción exitosa")
            print(f"  - Días estimados: {prediccion['dias_estimados']}")
            print(f"  - Fecha estimada: {prediccion['fecha_estimada']}")
            print(f"  - Método: {prediccion['metodo']}")
            print(f"  - Confianza: {prediccion['confianza']}%")
            return True
        else:
            print("✗ No se pudo generar predicción")
            return False
            
    except Exception as e:
        print(f"✗ Error en predicción: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_especie_nueva():
    """Prueba 4: Predicción con especie nueva (fallback)"""
    print("\n" + "="*80)
    print("PRUEBA 4: Predicción con especie nueva (fallback)")
    print("="*80)
    
    try:
        prediccion = ml_polinizacion_service.predecir_dias_maduracion(
            genero='GeneroNuevo',
            especie='especieNueva',
            tipo='SELF',
            fecha_pol=date(2025, 3, 1),
            cantidad=1
        )
        
        if prediccion:
            print("✓ Predicción con fallback exitosa")
            print(f"  - Días estimados: {prediccion['dias_estimados']}")
            print(f"  - Confianza: {prediccion['confianza']}% (esperado: baja)")
            print(f"  - Nivel: {prediccion['nivel_confianza']}")
            return True
        else:
            print("✗ No se pudo generar predicción")
            return False
            
    except Exception as e:
        print(f"✗ Error en predicción: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_prediccion_heuristica():
    """Prueba 5: Predicción heurística (sin ML)"""
    print("\n" + "="*80)
    print("PRUEBA 5: Predicción heurística (fallback sin ML)")
    print("="*80)
    
    try:
        prediccion = polinizacion_service._predecir_heuristico(
            genero='Test',
            especie='test',
            tipo='HYBRID',
            fecha_pol=date(2025, 1, 1)
        )
        
        if prediccion:
            print("✓ Predicción heurística exitosa")
            print(f"  - Días estimados: {prediccion['dias_estimados']}")
            print(f"  - Método: {prediccion['metodo']}")
            print(f"  - Confianza: {prediccion['confianza']}%")
            return True
        else:
            print("✗ No se pudo generar predicción heurística")
            return False
            
    except Exception as e:
        print(f"✗ Error en predicción heurística: {e}")
        return False

def main():
    """Ejecutar todas las pruebas"""
    print("\n" + "="*80)
    print(" PRUEBAS DEL SISTEMA DE PREDICCIÓN DE POLINIZACIONES")
    print("="*80)
    
    resultados = []
    
    # Ejecutar pruebas
    resultados.append(("Carga del modelo", test_modelo_cargado()))
    resultados.append(("Predicción directa ML", test_prediccion_directa()))
    resultados.append(("Predicción servicio", test_prediccion_servicio()))
    resultados.append(("Especie nueva (fallback)", test_especie_nueva()))
    resultados.append(("Predicción heurística", test_prediccion_heuristica()))
    
    # Resumen
    print("\n" + "="*80)
    print(" RESUMEN DE PRUEBAS")
    print("="*80)
    
    exitosas = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nombre, resultado in resultados:
        estado = "✓ PASS" if resultado else "✗ FAIL"
        print(f"{estado} - {nombre}")
    
    print("\n" + "="*80)
    print(f" RESULTADO: {exitosas}/{total} pruebas exitosas")
    print("="*80)
    
    if exitosas == total:
        print("\n✓ Todas las pruebas pasaron exitosamente!")
        return 0
    else:
        print(f"\n✗ {total - exitosas} prueba(s) fallaron")
        return 1

if __name__ == '__main__':
    sys.exit(main())
