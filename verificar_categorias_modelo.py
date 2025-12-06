"""
Script para verificar qué categorías conoce el modelo ML de polinización

Este script muestra TODOS los valores que el modelo conoce para cada columna categórica.
Útil para debugging cuando la confianza es baja.
"""

import os
import sys
import django

# Configurar Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.ml.predictors.pollination_predictor import PollinationPredictor

def main():
    print("=" * 80)
    print("VERIFICACIÓN DE CATEGORÍAS CONOCIDAS POR EL MODELO ML")
    print("=" * 80)
    print()

    try:
        # Cargar predictor
        print("📦 Cargando modelo...")
        predictor = PollinationPredictor()
        print("✅ Modelo cargado correctamente")
        print()

        # Verificar encoders
        if not hasattr(predictor, 'label_encoders'):
            print("❌ ERROR: El modelo no tiene encoders cargados")
            return

        print(f"📊 Encoders cargados: {len(predictor.label_encoders)}")
        print()

        # Mostrar categorías conocidas para cada columna
        print("=" * 80)
        print("CATEGORÍAS CONOCIDAS POR COLUMNA")
        print("=" * 80)
        print()

        columnas_categoricas = ['genero', 'especie', 'ubicacion', 'responsable', 'Tipo']

        for col in columnas_categoricas:
            if col in predictor.label_encoders:
                encoder = predictor.label_encoders[col]
                categorias = encoder.classes_

                print(f"📁 {col.upper()}")
                print(f"   Total de categorías conocidas: {len(categorias)}")
                print(f"   Valores:")

                for i, valor in enumerate(categorias, 1):
                    print(f"      {i}. '{valor}'")

                print()
            else:
                print(f"❌ {col.upper()}: NO TIENE ENCODER")
                print()

        print("=" * 80)
        print("INSTRUCCIONES")
        print("=" * 80)
        print()
        print("Para obtener confianza ALTA (85%):")
        print("1. Usa EXACTAMENTE los valores listados arriba")
        print("2. Respeta mayúsculas/minúsculas")
        print("3. Respeta espacios y caracteres especiales")
        print()
        print("Ejemplo de datos con confianza ALTA:")
        if 'genero' in predictor.label_encoders and len(predictor.label_encoders['genero'].classes_) > 0:
            ejemplo_genero = predictor.label_encoders['genero'].classes_[0]
            print(f"   - Género: '{ejemplo_genero}'")
        if 'especie' in predictor.label_encoders and len(predictor.label_encoders['especie'].classes_) > 0:
            ejemplo_especie = predictor.label_encoders['especie'].classes_[0]
            print(f"   - Especie: '{ejemplo_especie}'")
        if 'Tipo' in predictor.label_encoders and len(predictor.label_encoders['Tipo'].classes_) > 0:
            ejemplo_tipo = predictor.label_encoders['Tipo'].classes_[0]
            print(f"   - Tipo: '{ejemplo_tipo}'")
        print()

        print("✅ Verificación completada")

    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
