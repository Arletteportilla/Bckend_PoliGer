#!/usr/bin/env python
"""
Script para entrenar TODOS los modelos de predicción
Ejecuta los comandos Django para entrenar Polinización y Germinación
"""
import subprocess
import sys
import os

def run_command(command, description):
    """Ejecuta un comando y muestra el resultado"""
    print(f"\n{'='*70}")
    print(f"  {description}")
    print(f"{'='*70}\n")

    result = subprocess.run(command, shell=True, capture_output=False, text=True)

    if result.returncode != 0:
        print(f"\n❌ Error ejecutando: {description}")
        return False

    return True

def main():
    """Función principal"""
    print("\n" + "="*70)
    print("  ENTRENAMIENTO DE MODELOS DE PREDICCIÓN - PoliGer")
    print("="*70)
    print("\nEste script entrenará ambos modelos:")
    print("  1. Modelo de Polinización (predicción de días hasta maduración)")
    print("  2. Modelo de Germinación (predicción de días hasta germinación)")
    print("\nUsando LightGBM para modelos ligeros y rápidos")
    print("="*70)

    # Confirmar
    response = input("\n¿Deseas continuar? (s/n): ")
    if response.lower() != 's':
        print("\nCancelado por el usuario.")
        return

    # 1. Entrenar modelo de Polinización
    success = run_command(
        "python manage.py train_polinizacion_model --model-type=lightgbm",
        "Entrenando Modelo de Polinización"
    )

    if not success:
        print("\n❌ Error entrenando modelo de Polinización")
        sys.exit(1)

    # 2. Entrenar modelo de Germinación
    success = run_command(
        "python manage.py train_germinacion_model --model-type=lightgbm",
        "Entrenando Modelo de Germinación"
    )

    if not success:
        print("\n❌ Error entrenando modelo de Germinación")
        sys.exit(1)

    # Resumen final
    print("\n" + "="*70)
    print("  ✓ TODOS LOS MODELOS ENTRENADOS EXITOSAMENTE")
    print("="*70)
    print("\nModelos generados:")
    print("  1. laboratorio/modelos/Polinizacion_fallback.bin")
    print("  2. laboratorio/modelos/Polinizacion_fallback_encoders.bin")
    print("  3. laboratorio/modelos/germinacion.pkl")
    print("  4. laboratorio/modelos/germinacion_encoders.pkl")
    print("\nPróximos pasos:")
    print("  - Los modelos están listos para usar")
    print("  - Son mucho más ligeros que los anteriores")
    print("  - Reinicia el servidor Django para usar los nuevos modelos")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
