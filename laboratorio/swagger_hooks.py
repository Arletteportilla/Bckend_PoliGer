"""
Hooks de postprocesamiento para drf-spectacular.

Renombra los tags auto-generados en inglés/minúsculas a sus equivalentes
en español tal como están definidos en SPECTACULAR_SETTINGS['TAGS'].
"""

# Mapeo: tag auto-generado por drf-spectacular → tag en español
TAG_MAPPING = {
    # ViewSets registrados en el router
    'polinizaciones': 'Polinizaciones',
    'germinaciones': 'Germinaciones',
    'notifications': 'Notificaciones',
    'user-profiles': 'Usuarios',
    'user-management': 'Usuarios',
    'user-metas': 'Usuarios',
    'generos': 'Géneros',
    'especies': 'Especies',
    'ubicaciones': 'Ubicaciones',
    'seguimientos': 'Seguimientos',
    'capsulas': 'Cápsulas',
    'siembras': 'Siembras',
    'personal': 'Personal',
    'inventarios': 'Inventario',

    # Vistas de autenticación
    'token': 'Autenticación',
    'register': 'Autenticación',
    'login': 'Autenticación',
    'protected': 'Autenticación',

    # Salud del sistema
    'health': 'Salud',

    # Predicciones y ML
    'predicciones': 'Predicciones',
    'ml': 'Predicciones',

    # Estadísticas y reportes
    'estadisticas': 'Estadísticas',
    'reportes': 'Estadísticas',

    # Importación CSV
    'upload': 'Importación CSV',
    'csv-templates': 'Importación CSV',
}


def rename_tags_hook(result, generator, **kwargs):
    """
    Renombra los tags auto-generados a sus equivalentes en español.
    Se ejecuta después de que drf-spectacular genera el schema OpenAPI.
    """
    # 1. Renombrar tags en cada operación de cada path
    for path_data in result.get('paths', {}).values():
        for operation in path_data.values():
            if isinstance(operation, dict) and 'tags' in operation:
                operation['tags'] = [
                    TAG_MAPPING.get(tag, tag) for tag in operation['tags']
                ]

    # 2. Eliminar del listado de tags raíz los nombres auto-generados
    #    (quedan solo los tags en español definidos en SPECTACULAR_SETTINGS)
    auto_tags = set(TAG_MAPPING.keys())
    result['tags'] = [
        t for t in result.get('tags', [])
        if t.get('name') not in auto_tags
    ]

    return result
