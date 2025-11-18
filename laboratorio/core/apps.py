from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver

class LaboratorioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'laboratorio'

    def ready(self):
        """
        Ejecuta cuando la aplicación está lista
        """
        # Importar signals para que se registren
        import laboratorio.signals
        
        # Configurar optimizaciones de SQLite
        @receiver(connection_created)
        def setup_sqlite_pragmas(sender, connection, **kwargs):
            """
            Configura PRAGMAs de SQLite para optimizar el rendimiento
            Compatible con Python 3.12+
            """
            if connection.vendor == 'sqlite':
                cursor = connection.cursor()
                # Configuraciones de rendimiento
                cursor.execute('PRAGMA journal_mode=WAL;')
                cursor.execute('PRAGMA synchronous=NORMAL;')
                cursor.execute('PRAGMA cache_size=10000;')
                cursor.execute('PRAGMA temp_store=MEMORY;')
                cursor.close()