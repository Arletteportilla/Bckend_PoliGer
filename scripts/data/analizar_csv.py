"""
Script para analizar el CSV de germinaciones y encontrar duplicados
"""
import csv
from collections import Counter

archivo_csv = 'data/GERMINACION.csv'

codigos = []
registros_sin_codigo = 0

print("[*] Analizando CSV...")

with open(archivo_csv, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')

    for idx, row in enumerate(reader, start=1):
        codigo = row.get('CODIGO', '').strip()

        if not codigo or codigo == '':
            registros_sin_codigo += 1
        else:
            codigos.append(codigo)

print("\n" + "="*80)
print("ANÁLISIS DEL CSV")
print("="*80)
print(f"Total de líneas (sin header): {len(codigos) + registros_sin_codigo}")
print(f"Registros con código: {len(codigos)}")
print(f"Registros sin código: {registros_sin_codigo}")
print(f"Códigos únicos: {len(set(codigos))}")
print(f"Códigos duplicados: {len(codigos) - len(set(codigos))}")
print("="*80)

# Encontrar los códigos duplicados
contador_codigos = Counter(codigos)
duplicados = {codigo: count for codigo, count in contador_codigos.items() if count > 1}

if duplicados:
    print(f"\n[!] Se encontraron {len(duplicados)} códigos con duplicados:")
    print("\nCÓDIGOS DUPLICADOS (primeros 20):")
    print("-"*80)

    for idx, (codigo, count) in enumerate(sorted(duplicados.items(), key=lambda x: x[1], reverse=True)[:20], start=1):
        print(f"{idx}. {codigo}: {count} veces")

    if len(duplicados) > 20:
        print(f"... y {len(duplicados) - 20} más")
else:
    print("\n[OK] No se encontraron códigos duplicados")

print("\n" + "="*80)
