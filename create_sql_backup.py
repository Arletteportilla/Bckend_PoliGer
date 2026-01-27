"""
Crear backup SQL de las tablas principales
"""
import sys
from django.db import connection

def create_sql_backup():
    """Crear backup SQL de datos"""

    output_file = "backups/poliger_data_backup.sql"

    print(f"Creando backup SQL en: {output_file}")
    print("Esto puede tomar varios minutos...")

    with open(output_file, 'w', encoding='utf-8') as f:
        # Escribir encabezado
        f.write("-- Backup de base de datos PoliGer\n")
        f.write("-- Generado automáticamente\n\n")
        f.write("BEGIN;\n\n")

        # Deshabilitar triggers temporalmente
        f.write("SET session_replication_role = 'replica';\n\n")

        #Tablas a exportar en orden
        tables = [
            'auth_user',
            'laboratorio_userprofile',
            'laboratorio_genero',
            'laboratorio_especie',
            'laboratorio_ubicacion',
            'laboratorio_polinizacion',
            'laboratorio_germinacion',
        ]

        cursor = connection.cursor()

        for table in tables:
            print(f"Exportando tabla: {table}")

            try:
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {count} registros")

                if count == 0:
                    continue

                # Obtener nombres de columnas
                cursor.execute(f"""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = '{table}'
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in cursor.fetchall()]
                columns_str = ', '.join([f'"{col}"' for col in columns])

                # Exportar datos en lotes
                batch_size = 1000
                offset = 0

                f.write(f"\n-- Tabla: {table}\n")
                f.write(f"-- {count} registros\n\n")

                while offset < count:
                    cursor.execute(f'SELECT * FROM {table} LIMIT {batch_size} OFFSET {offset}')
                    rows = cursor.fetchall()

                    for row in rows:
                        # Escapar valores
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, bool):
                                values.append('TRUE' if val else 'FALSE')
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            else:
                                # Escapar comillas simples
                                val_str = str(val).replace("'", "''")
                                values.append(f"'{val_str}'")

                        values_str = ', '.join(values)
                        f.write(f"INSERT INTO {table} ({columns_str}) VALUES ({values_str});\n")

                    offset += batch_size

                    if offset % 10000 == 0:
                        print(f"  ... {offset}/{count}")

                print(f"  ✓ Completado")

            except Exception as e:
                print(f"  ✗ Error: {e}")
                continue

        # Restaurar triggers
        f.write("\nSET session_replication_role = 'origin';\n\n")

        # Actualizar secuencias
        f.write("-- Actualizar secuencias\n")
        cursor.execute("""
            SELECT sequence_name
            FROM information_schema.sequences
            WHERE sequence_schema='public'
        """)
        sequences = cursor.fetchall()

        for seq in sequences:
            seq_name = seq[0]
            table_name = seq_name.replace('_id_seq', '')
            f.write(f"SELECT setval('{seq_name}', (SELECT COALESCE(MAX(id), 1) FROM {table_name}), true);\n")

        f.write("\nCOMMIT;\n")

    print(f"\n✓ Backup completado: {output_file}")

    # Mostrar tamaño
    import os
    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"  Tamaño: {size_mb:.2f} MB")

if __name__ == "__main__":
    try:
        create_sql_backup()
    except KeyboardInterrupt:
        print("\n\nBackup interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
