# Guía de Importación de Datos CSV - PoliGer

Esta guía te explica cómo subir e integrar datos de polinizaciones y germinaciones desde archivos CSV a tu aplicación PoliGer.

## 📁 Ubicación de Archivos

Los archivos CSV deben colocarse en el directorio:
```
BACK/backend/data/
```

## 📋 Formatos de Archivos CSV

### 1. Archivo de Polinizaciones (`polinizaciones.csv`)

**Columnas requeridas:**
- `fecha_pol`: Fecha de polinización (formato: YYYY-MM-DD)
- `codigo`: Código único de la polinización
- `genero`: Género de la orquídea
- `especie`: Especie de la orquídea
- `variedad`: Variedad de la orquídea

**Columnas opcionales:**
- `fecha_mad`: Fecha de maduración (formato: YYYY-MM-DD)
- `ubicacion`: Ubicación donde se realizó la polinización
- `cantidad`: Cantidad de polinizaciones (default: 1)
- `disponible`: Si está disponible (True/False, default: True)
- `archivo_origen`: Nombre del archivo de origen
- `fecha_siembra`: Fecha de siembra (formato: YYYY-MM-DD)
- `fecha_replante`: Fecha de replante (formato: YYYY-MM-DD)
- `clima`: Condiciones climáticas
- `cantidad_solicitada`: Cantidad solicitada (default: 0)
- `estado`: Estado de la polinización (EN_PROCESO/COMPLETADA/FALLIDA, default: EN_PROCESO)
- `observaciones`: Observaciones adicionales

### 2. Archivo de Germinaciones (`germinaciones.csv`)

**Columnas requeridas:**
- `fecha_ingreso`: Fecha de ingreso (formato: YYYY-MM-DD)
- `fecha_polinizacion`: Fecha de polinización (formato: YYYY-MM-DD)
- `nombre`: Nombre del híbrido
- `detalles_padres`: Detalles de los padres del híbrido

**Columnas opcionales:**
- `tipo_polinizacion`: Tipo de polinización
- `finca`: Nombre de la finca
- `numero_vivero`: Número de vivero
- `numero_capsulas`: Número de cápsulas (default: 0)
- `estado_capsulas`: Estado de cápsulas (BUENO/REGULAR/MALO, default: BUENO)
- `cantidad_solicitada`: Cantidad solicitada (default: 0)
- `entrega_capsulas`: Persona que entrega las cápsulas
- `recibe_capsulas`: Persona que recibe las cápsulas
- `etapa_actual`: Etapa actual (SIEMBRA/GERMINACION/CRECIMIENTO/TRASPLANTE, default: SIEMBRA)
- `codigo_polinizacion`: Código de la polinización asociada (opcional)
- `observaciones`: Observaciones adicionales

## 🚀 Métodos de Importación

### Método 1: Comando de Django (Recomendado)

1. **Navega al directorio del proyecto:**
   ```bash
   cd BACK/backend
   ```

2. **Importa polinizaciones:**
   ```bash
   python manage.py import_csv_data --polinizaciones data/polinizaciones.csv --user admin
   ```

3. **Importa germinaciones:**
   ```bash
   python manage.py import_csv_data --germinaciones data/germinaciones.csv --user admin
   ```

4. **Importa ambos archivos:**
   ```bash
   python manage.py import_csv_data --polinizaciones data/polinizaciones.csv --germinaciones data/germinaciones.csv --user admin
   ```

### Método 2: API REST (Interfaz Web)

1. **Inicia el servidor Django:**
   ```bash
   cd BACK/backend
   python manage.py runserver
   ```

2. **Accede a las plantillas de CSV:**
   ```
   GET http://localhost:8000/api/csv-templates/
   ```

3. **Sube archivo de polinizaciones:**
   ```
   POST http://localhost:8000/api/upload/polinizaciones/
   Content-Type: multipart/form-data
   file: [archivo CSV]
   ```

4. **Sube archivo de germinaciones:**
   ```
   POST http://localhost:8000/api/upload/germinaciones/
   Content-Type: multipart/form-data
   file: [archivo CSV]
   ```

## 📝 Ejemplos de Archivos CSV

### Ejemplo de Polinizaciones:
```csv
fecha_pol,fecha_mad,codigo,genero,especie,variedad,ubicacion,cantidad,disponible,archivo_origen,fecha_siembra,fecha_replante,clima,cantidad_solicitada,estado,observaciones
2024-01-15,2024-03-15,POL-001,Orchidaceae,Phalaenopsis,Blanca,Invernadero A,10,True,archivo_origen.pdf,2024-01-20,2024-02-15,Templado,5,EN_PROCESO,Primera polinización de la temporada
```

### Ejemplo de Germinaciones:
```csv
fecha_ingreso,fecha_polinizacion,nombre,detalles_padres,tipo_polinizacion,finca,numero_vivero,numero_capsulas,estado_capsulas,cantidad_solicitada,entrega_capsulas,recibe_capsulas,etapa_actual,codigo_polinizacion,observaciones
2024-01-20,2024-01-15,Híbrido Phalaenopsis Blanca x Amarilla,Padre: Phalaenopsis Blanca, Madre: Phalaenopsis Amarilla,Manual,Finca Principal,VIV-001,5,BUENO,100,Juan Pérez,María García,SIEMBRA,POL-001,Primera germinación del híbrido
```

## ⚠️ Consideraciones Importantes

1. **Codificación de archivos:** Los archivos CSV deben estar en codificación UTF-8
2. **Separador:** Usar coma (,) como separador de campos
3. **Fechas:** Formato obligatorio YYYY-MM-DD
4. **Campos únicos:** Los códigos de polinización deben ser únicos
5. **Relaciones:** Las germinaciones pueden estar asociadas a polinizaciones mediante el campo `codigo_polinizacion`
6. **Usuario:** Se creará automáticamente un usuario si no existe

## 🔧 Solución de Problemas

### Error: "Usuario no encontrado"
- El sistema creará automáticamente un usuario con el nombre especificado
- La contraseña temporal será: `temp_password_123`

### Error: "Formato de fecha inválido"
- Asegúrate de que las fechas estén en formato YYYY-MM-DD
- Ejemplo: `2024-01-15` (no `15/01/2024`)

### Error: "Código duplicado"
- Los códigos de polinización deben ser únicos
- Revisa que no haya códigos duplicados en tu archivo CSV

### Error: "Campo requerido faltante"
- Verifica que todos los campos requeridos estén presentes
- Revisa los nombres de las columnas (deben coincidir exactamente)

## 📊 Verificación de Datos

Después de la importación, puedes verificar los datos:

1. **En la aplicación web:** Navega a las secciones de polinizaciones y germinaciones
2. **En la base de datos:** Usa el admin de Django
3. **Via API:** Consulta los endpoints REST

## 🆘 Soporte

Si encuentras problemas durante la importación:

1. Revisa los mensajes de error en la consola
2. Verifica el formato de tu archivo CSV
3. Asegúrate de que el servidor Django esté ejecutándose
4. Consulta los logs del servidor para más detalles 