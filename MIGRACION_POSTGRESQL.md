# 🐘 Migración a PostgreSQL - Proyecto PoliGer

Este documento guía la migración de SQLite a PostgreSQL.

## ✅ Estado Actual

Tu proyecto **YA ESTÁ CONFIGURADO** para PostgreSQL con las siguientes credenciales:

```env
DB_ENGINE=postgresql
DB_NAME=poliger_db
DB_USER=postgres
DB_PASSWORD=root
DB_HOST=localhost
DB_PORT=5432
```

## 📋 Requisitos Previos

1. **PostgreSQL instalado** (versión 12 o superior)
2. **Servidor PostgreSQL ejecutándose**
3. **Python 3.8+** con todas las dependencias instaladas

## 🚀 Opción 1: Migración Automática (Recomendado)

Ejecuta el script automatizado que verifica todo y ejecuta las migraciones:

```bash
cd c:\Users\arlet\Desktop\78\BACK\backend
python migrate_to_postgresql.py
```

Este script:
- ✅ Verifica la configuración
- ✅ Verifica psycopg2 instalado
- ✅ Verifica conexión a PostgreSQL
- ✅ Crea la base de datos si no existe
- ✅ Ejecuta las migraciones
- ✅ Verifica que las tablas se crearon correctamente

## 🔧 Opción 2: Migración Manual

### Paso 1: Verificar PostgreSQL

Asegúrate de que PostgreSQL esté ejecutándose:

```bash
# Windows (en PowerShell como administrador)
Get-Service -Name postgresql*

# Si no está ejecutándose, iniciarlo:
Start-Service -Name postgresql-x64-14  # Ajusta el nombre según tu versión
```

### Paso 2: Crear Base de Datos

Opción A - Usando pgAdmin:
1. Abre pgAdmin
2. Click derecho en "Databases" → Create → Database
3. Nombre: `poliger_db`
4. Owner: `postgres`
5. Click "Save"

Opción B - Usando psql:
```bash
psql -U postgres -c "CREATE DATABASE poliger_db;"
```

### Paso 3: Verificar Dependencias

```bash
cd c:\Users\arlet\Desktop\78\BACK\backend
pip install psycopg2-binary==2.9.9
```

### Paso 4: Ejecutar Migraciones

```bash
# Generar migraciones (si hay cambios)
python manage.py makemigrations

# Aplicar todas las migraciones a PostgreSQL
python manage.py migrate

# Verificar el estado de las migraciones
python manage.py showmigrations
```

Deberías ver algo como:
```
laboratorio
 [X] 0001_initial
 [X] 0002_auto_...
 [X] 0003_auto_...
 ...
 [X] 0044_add_ml_prediction_fields_polinizacion
```

### Paso 5: Crear Superusuario (Opcional)

```bash
python manage.py createsuperuser
```

Ingresa:
- Username: `admin`
- Email: `admin@poliger.com`
- Password: (tu contraseña segura)

### Paso 6: Verificar Instalación

Inicia el servidor:
```bash
python manage.py runserver
```

Accede a:
- Admin: http://127.0.0.1:8000/admin/
- API: http://127.0.0.1:8000/api/

## 🔍 Verificación de Tablas

Conecta a PostgreSQL para verificar las tablas:

```sql
-- Conectar a la base de datos
\c poliger_db

-- Listar todas las tablas
\dt

-- Ver estructura de tabla importante
\d laboratorio_polinizacion
\d laboratorio_germinacion
```

Deberías ver 13+ tablas principales:
- `laboratorio_polinizacion`
- `laboratorio_germinacion`
- `laboratorio_genero`
- `laboratorio_especie`
- `laboratorio_ubicacion`
- `laboratorio_notification`
- `laboratorio_userprofile`
- `auth_user`
- `django_migrations`
- Y más...

## 📊 Migración de Datos (Si tenías datos en SQLite)

Si tenías datos importantes en SQLite y quieres migrarlos a PostgreSQL:

### Opción 1: Exportar/Importar con Django

```bash
# 1. Con SQLite activo, exportar datos
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes --exclude auth.permission \
    --indent 2 -o backup_data.json

# 2. Cambiar a PostgreSQL en .env
# (Ya lo tienes configurado)

# 3. Aplicar migraciones a PostgreSQL
python manage.py migrate

# 4. Importar datos
python manage.py loaddata backup_data.json
```

### Opción 2: Migración Selectiva

Si solo quieres migrar ciertas tablas:

```bash
# Exportar solo polinizaciones
python manage.py dumpdata laboratorio.Polinizacion \
    --indent 2 -o polinizaciones.json

# Exportar solo germinaciones
python manage.py dumpdata laboratorio.Germinacion \
    --indent 2 -o germinaciones.json

# Cambiar a PostgreSQL y migrar
python manage.py migrate

# Importar datos específicos
python manage.py loaddata polinizaciones.json
python manage.py loaddata germinaciones.json
```

## ⚠️ Solución de Problemas

### Error: "could not connect to server"

**Solución:**
1. Verifica que PostgreSQL esté ejecutándose
2. Verifica las credenciales en `.env`
3. Verifica el puerto (por defecto 5432)

```bash
# Windows - Verificar servicio
Get-Service -Name postgresql*

# Iniciar servicio si está detenido
Start-Service -Name postgresql-x64-14
```

### Error: "database does not exist"

**Solución:**
Crea la base de datos manualmente:

```sql
CREATE DATABASE poliger_db;
```

O usa el script automático:
```bash
python migrate_to_postgresql.py
```

### Error: "psycopg2 not found"

**Solución:**
```bash
pip install psycopg2-binary==2.9.9
```

### Error: "FATAL: password authentication failed"

**Solución:**
Verifica la contraseña en `.env`:
```env
DB_PASSWORD=root  # O tu contraseña correcta
```

### Error: Migraciones ya aplicadas

Si ves errores de que las migraciones ya existen:

```bash
# Ver estado actual
python manage.py showmigrations

# Si necesitas resetear (CUIDADO: borra datos)
python manage.py migrate laboratorio zero
python manage.py migrate
```

## 🎯 Ventajas de PostgreSQL

Ahora con PostgreSQL tienes:

1. ✅ **Mejor rendimiento** con grandes volúmenes de datos
2. ✅ **Concurrencia real** - múltiples usuarios simultáneos
3. ✅ **Tipos de datos avanzados** - JSON, arrays, etc.
4. ✅ **Índices más eficientes**
5. ✅ **Transacciones ACID completas**
6. ✅ **Mejor para producción**
7. ✅ **Backups y replicación**

## 📈 Optimizaciones Recomendadas

### 1. Configurar Connection Pooling

Ya está configurado en `settings.py`:
```python
CONN_MAX_AGE = 600  # 10 minutos
```

### 2. Índices ya configurados

Tu proyecto ya tiene índices optimizados:
- `models.Index(fields=['fecha_creacion'])`
- `models.Index(fields=['codigo'])`
- `models.Index(fields=['genero', 'especie'])`  # Compuesto

### 3. Backups Automáticos

Crea un script de backup:

```bash
# backup_postgresql.bat
@echo off
set PGPASSWORD=root
set BACKUP_DIR=C:\Users\arlet\Desktop\78\BACK\backups
set DATE=%date:~-4,4%%date:~-7,2%%date:~-10,2%
set TIME=%time:~0,2%%time:~3,2%

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

pg_dump -U postgres -h localhost -d poliger_db > "%BACKUP_DIR%\poliger_db_%DATE%_%TIME%.sql"

echo Backup completado: poliger_db_%DATE%_%TIME%.sql
```

Programa este script en el Programador de tareas de Windows para backups automáticos.

## 🔐 Seguridad en Producción

Cuando despliegues a producción:

1. **Cambia la contraseña:**
```sql
ALTER USER postgres WITH PASSWORD 'una_contraseña_muy_segura_y_larga';
```

2. **Crea un usuario específico:**
```sql
CREATE USER poliger_user WITH PASSWORD 'contraseña_segura';
GRANT ALL PRIVILEGES ON DATABASE poliger_db TO poliger_user;
```

3. **Actualiza `.env`:**
```env
DB_USER=poliger_user
DB_PASSWORD=contraseña_segura
```

4. **Restringe acceso externo** en `postgresql.conf` y `pg_hba.conf`

## 📞 Soporte

Si encuentras problemas:

1. Revisa los logs:
   - Django: `BACK/backend/logs/django.log`
   - PostgreSQL: `C:\Program Files\PostgreSQL\14\data\log\`

2. Verifica la configuración:
   ```bash
   python manage.py check
   ```

3. Prueba la conexión:
   ```python
   python manage.py shell
   >>> from django.db import connection
   >>> connection.ensure_connection()
   >>> print("Conexión exitosa!")
   ```

## ✅ Checklist Post-Migración

- [ ] PostgreSQL ejecutándose
- [ ] Base de datos `poliger_db` creada
- [ ] Migraciones aplicadas (44 migraciones)
- [ ] Tablas creadas correctamente
- [ ] Superusuario creado
- [ ] Servidor Django inicia sin errores
- [ ] API responde correctamente
- [ ] Admin de Django accesible
- [ ] Modelos ML funcionando
- [ ] Predicciones ML operativas

## 🎉 ¡Listo!

Tu proyecto ahora usa PostgreSQL y está listo para **escalar a producción**.

---

**Fecha:** 25 de noviembre de 2025
**Proyecto:** PoliGer - Sistema de Gestión de Laboratorio de Orquídeas
