from django.core.management.base import BaseCommand
from django.utils import timezone
from laboratorio.services import NotificationService

class Command(BaseCommand):
    help = 'Verifica las germinaciones que necesitan recordatorios y crea notificaciones'

    def handle(self, *args, **options):
        self.stdout.write('Verificando recordatorios de germinaciones...')
        
        try:
            # Verificar recordatorios pendientes
            NotificationService.verificar_recordatorios_pendientes()
            
            self.stdout.write(
                self.style.SUCCESS('Verificación de recordatorios completada exitosamente')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error al verificar recordatorios: {str(e)}')
            )
