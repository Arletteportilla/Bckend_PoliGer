#!/usr/bin/env python
"""
Script específico para ejecutar tests de predicciones de polinización
Incluye tests unitarios, de integración y de rendimiento
"""
import os
import sys
import subprocess
import time
from pathlib import Path

def run_command(command, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n{'='*70}")
    print(f"🧪 {description}")
    print(f"{'='*70}")
    
    start_time = time.time()
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    end_time = time.time()
    
    execution_time = end_time - start_time
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:", result.stderr)
    
    print(f"\n⏱️ Tiempo de ejecución: {execution_time:.2f} segundos")
    
    return result.returncode == 0

def main():
    """Función principal para ejecutar tests de polinización"""
    # Cambiar al directorio del backend
    backend_dir = Path(__file__).parent.parent.parent
    os.chdir(backend_dir)
    
    print("🌸 Iniciando Tests de Predicciones de Polinización")
    print("=" * 70)
    
    all_tests_passed = True
    
    # 1. Tests unitarios de funciones de predicción
    print("\n📋 FASE 1: Tests Unitarios de Funciones")
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.CargarModeloPolinizacionTest --verbosity=2",
        "Tests de Carga del Modelo .bin"
    )
    all_tests_passed = all_tests_passed and success
    
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.GenerarCacheKeyPolinizacionTest --verbosity=2",
        "Tests de Generación de Cache Keys"
    )
    all_tests_passed = all_tests_passed and success
    
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.ObtenerParametrosEspeciePolinizacionTest --verbosity=2",
        "Tests de Parámetros de Especies"
    )
    all_tests_passed = all_tests_passed and success
    
    # 2. Tests de predicciones
    print("\n📋 FASE 2: Tests de Predicciones")
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.PrediccionPolinizacionInicialTest --verbosity=2",
        "Tests de Predicción Inicial"
    )
    all_tests_passed = all_tests_passed and success
    
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.RefinarPrediccionPolinizacionTest --verbosity=2",
        "Tests de Refinamiento de Predicciones"
    )
    all_tests_passed = all_tests_passed and success
    
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.ValidarPrediccionPolinizacionTest --verbosity=2",
        "Tests de Validación de Predicciones"
    )
    all_tests_passed = all_tests_passed and success
    
    # 3. Tests de manejo de errores
    print("\n📋 FASE 3: Tests de Manejo de Errores")
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.ExcepcionesTest --verbosity=2",
        "Tests de Excepciones Personalizadas"
    )
    all_tests_passed = all_tests_passed and success
    
    # 4. Tests de API endpoints
    print("\n📋 FASE 4: Tests de API Endpoints")
    success = run_command(
        "python manage.py test laboratorio.tests.test_views.PrediccionPolinizacionAPITest --verbosity=2",
        "Tests de Endpoints de Predicción"
    )
    all_tests_passed = all_tests_passed and success
    
    # 5. Tests de rendimiento
    print("\n📋 FASE 5: Tests de Rendimiento")
    success = run_command(
        "python manage.py test laboratorio.tests.test_views.PrediccionPolinizacionPerformanceTest --verbosity=2",
        "Tests de Performance de API"
    )
    all_tests_passed = all_tests_passed and success
    
    # 6. Tests de integración
    print("\n📋 FASE 6: Tests de Integración")
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion.IntegracionTest --verbosity=2",
        "Tests de Integración de Funciones"
    )
    all_tests_passed = all_tests_passed and success
    
    success = run_command(
        "python manage.py test laboratorio.tests.test_views.PrediccionPolinizacionIntegrationTest --verbosity=2",
        "Tests de Integración de API"
    )
    all_tests_passed = all_tests_passed and success
    
    # 7. Coverage específico para predicciones de polinización
    print("\n📋 FASE 7: Coverage Report")
    try:
        run_command(
            "coverage run --source='laboratorio.predicciones_polinizaciones' manage.py test laboratorio.tests.test_predicciones_polinizacion",
            "Generando Coverage para Predicciones de Polinización"
        )
        
        run_command(
            "coverage report --show-missing --include='*predicciones_polinizaciones*'",
            "Coverage Report - Predicciones de Polinización"
        )
        
        run_command(
            "coverage html --include='*predicciones_polinizaciones*'",
            "Coverage HTML Report"
        )
        
        print("\n📊 Coverage report específico generado en htmlcov/index.html")
        
    except Exception as e:
        print(f"⚠️ No se pudo generar coverage report: {e}")
    
    # 8. Tests completos de predicciones de polinización
    print("\n📋 FASE 8: Suite Completa de Tests")
    success = run_command(
        "python manage.py test laboratorio.tests.test_predicciones_polinizacion --verbosity=2",
        "Suite Completa - Tests de Predicciones de Polinización"
    )
    all_tests_passed = all_tests_passed and success
    
    # Resumen final
    print("\n" + "="*70)
    if all_tests_passed:
        print("✅ TODOS LOS TESTS DE PREDICCIONES DE POLINIZACIÓN PASARON")
        print("\n📈 Resumen de Tests Ejecutados:")
        print("   - ✅ Tests de Carga del Modelo .bin")
        print("   - ✅ Tests de Cache y Parámetros")
        print("   - ✅ Tests de Predicción Inicial")
        print("   - ✅ Tests de Refinamiento Progresivo")
        print("   - ✅ Tests de Validación con Fechas Reales")
        print("   - ✅ Tests de Manejo de Errores")
        print("   - ✅ Tests de Endpoints API")
        print("   - ✅ Tests de Rendimiento")
        print("   - ✅ Tests de Integración")
        print("   - 📊 Coverage Report Generado")
        
        print("\n🎯 Cobertura de Requirements:")
        print("   - ✅ Requirement 1.1: Carga automática del archivo .bin")
        print("   - ✅ Requirement 1.2: Manejo de errores de archivo corrupto/inexistente")
        print("   - ✅ Requirement 3.4: Actualización en tiempo real de predicciones")
        print("   - ✅ Requirement 5.3: Comparación con resultados reales")
        print("   - ✅ Requirement 5.4: Uso de información para mejorar predicciones")
        
        return True
    else:
        print("❌ ALGUNOS TESTS FALLARON")
        print("\n🔍 Revisa los logs anteriores para identificar los problemas")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)