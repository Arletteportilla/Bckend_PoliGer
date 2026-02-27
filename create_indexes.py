import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.db import connection

print("Creando índices en la base de datos...")

with connection.cursor() as cursor:
    # Índices para Polinizacion
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polinizacion_codigo ON laboratorio_polinizacion(codigo);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polinizacion_fechapol ON laboratorio_polinizacion(fechapol);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polinizacion_fechamad ON laboratorio_polinizacion(fechamad);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polinizacion_especie ON laboratorio_polinizacion(especie);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polinizacion_genero ON laboratorio_polinizacion(genero);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_polinizacion_creado_por ON laboratorio_polinizacion(creado_por_id);")
    
    # Índices para Germinacion  
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_germinacion_codigo ON laboratorio_germinacion(codigo);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_germinacion_fecha_siembra ON laboratorio_germinacion(fecha_siembra);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_germinacion_fecha_ingreso ON laboratorio_germinacion(fecha_ingreso);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_germinacion_genero ON laboratorio_germinacion(genero);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_germinacion_creado_por ON laboratorio_germinacion(creado_por_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_germinacion_polinizacion ON laboratorio_germinacion(polinizacion_id);")
    
    print("✅ Índices creados exitosamente")

