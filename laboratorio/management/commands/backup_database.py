"""
Management command para crear backup SQL de las tablas principales.
Uso: python manage.py create_sql_backup [--output archivo.sql]
"""
import os
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Crear backup SQL de las tablas principales de la base de datos'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='backups/poliger_data_backup.sql',
            help='Ruta del archivo de salida (default: backups/poliger_data_backup.sql)'
        )

    def handle(self, *args, **options):
        output_file = options['output']

        # Crear directorio si no existe
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.stdout.write(f"Directorio creado: {output_dir}")

        self.stdout.write(f"Creando backup SQL en: {output_file}")
        self.stdout.write("Esto puede tomar varios minutos...")

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Escribir encabezado
                f.write("-- Backup de base de datos PoliGer\n")
                f.write("-- Generado automaticamente\n\n")
                f.write("BEGIN;\n\n")

                # Deshabilitar triggers temporalmente
                f.write("SET session_replication_role = 'replica';\n\n")

                # Tablas a exportar en orden
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
                    self.stdout.write(f"Exportando tabla: {table}")

                    try:
                        # Contar registros
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")
                        count = cursor.fetchone()[0]
                        self.stdout.write(f"  {count} registros")

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
                                self.stdout.write(f"  ... {offset}/{count}")

                        self.stdout.write(self.style.SUCCESS(f"  Completado"))

                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  Error: {e}"))
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

            self.stdout.write(self.style.SUCCESS(f"\nBackup completado: {output_file}"))

            # Mostrar tamano
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            self.stdout.write(f"  Tamano: {size_mb:.2f} MB")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error fatal: {e}"))
            import traceback
            traceback.print_exc()
