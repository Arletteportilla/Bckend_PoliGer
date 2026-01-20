"""
Comando para enviar recordatorios automáticos de revisión.

LÓGICA CORRECTA:
- Usar fecha_siembra (germinación) o fechapol (polinización) como fecha base
- NO usar fecha de creación (created_at / fecha_creacion)
- Enviar recordatorio si: fecha_base + 5 días <= hoy
- Evitar duplicados con flag recordatorio_5_dias_enviado
- Considerar zona horaria del servidor

ESCENARIOS:
1. Registro creado el mismo día de la fecha ingresada:
   - fecha_base = 15 enero, creado = 15 enero
   - Recordatorio se envía el 20 enero (fecha_base + 5)

2. Registro creado hoy con fecha ya pasada:
   - fecha_base = 10 enero, creado = 20 enero
   - Recordatorio se envía INMEDIATAMENTE (ya pasaron más de 5 días)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import date, timedelta
from laboratorio.core.models import Germinacion, Polinizacion, Notification
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Envía recordatorios automáticos para registros que llevan 5+ días desde su fecha base'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dias',
            type=int,
            default=5,
            help='Días después de la fecha base para enviar recordatorio (default: 5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la ejecución sin crear notificaciones ni modificar registros'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Muestra información detallada de cada registro procesado'
        )

    def handle(self, *args, **options):
        dias_recordatorio = options['dias']
        dry_run = options['dry_run']
        verbose = options['verbose']

        # Fecha de corte: registros con fecha_base <= (hoy - dias_recordatorio)
        hoy = timezone.now().date()
        fecha_corte = hoy - timedelta(days=dias_recordatorio)

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'SISTEMA DE RECORDATORIOS AUTOMÁTICOS\n'
            f'{"="*70}\n'
            f'Fecha actual: {hoy}\n'
            f'Días para recordatorio: {dias_recordatorio}\n'
            f'Fecha de corte: {fecha_corte}\n'
            f'Modo: {"SIMULACIÓN (dry-run)" if dry_run else "PRODUCCIÓN"}\n'
            f'{"="*70}\n'
        ))

        # Procesar germinaciones (5 días después de siembra)
        notif_germinaciones = self._procesar_germinaciones(fecha_corte, dry_run, verbose)

        # Procesar polinizaciones (5 días después de polinización)
        notif_polinizaciones = self._procesar_polinizaciones(fecha_corte, dry_run, verbose)

        # Procesar recordatorios de predicción (5 días antes de fecha estimada)
        fecha_prediccion = hoy + timedelta(days=dias_recordatorio)
        notif_prediccion_germinaciones = self._procesar_prediccion_germinaciones(fecha_prediccion, dry_run, verbose)
        notif_prediccion_polinizaciones = self._procesar_prediccion_polinizaciones(fecha_prediccion, dry_run, verbose)

        # Resumen
        total = notif_germinaciones + notif_polinizaciones + notif_prediccion_germinaciones + notif_prediccion_polinizaciones

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'RESUMEN\n'
            f'{"="*70}\n'
            f'Recordatorios de germinación (post-siembra): {notif_germinaciones}\n'
            f'Recordatorios de polinización (post-polinización): {notif_polinizaciones}\n'
            f'Recordatorios de predicción germinación: {notif_prediccion_germinaciones}\n'
            f'Recordatorios de predicción polinización: {notif_prediccion_polinizaciones}\n'
            f'TOTAL: {total}\n'
            f'{"="*70}\n'
        ))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                '\n⚠️  Modo DRY RUN: No se crearon notificaciones reales\n'
            ))

        return str(total)

    def _procesar_germinaciones(self, fecha_corte, dry_run, verbose):
        """
        Procesa germinaciones que requieren recordatorio.

        Condiciones:
        - fecha_siembra <= fecha_corte (ya pasaron 5+ días desde la siembra)
        - recordatorio_5_dias_enviado = False (no se ha enviado aún)
        - estado_germinacion = 'INICIAL' (no ha sido actualizado)
        - creado_por no es nulo (tiene usuario asignado)
        """
        self.stdout.write('\n🌱 PROCESANDO GERMINACIONES...\n')

        # Consulta con las condiciones correctas
        germinaciones = Germinacion.objects.filter(
            fecha_siembra__lte=fecha_corte,  # Fecha base >= 5 días atrás
            recordatorio_5_dias_enviado=False,  # No enviado aún
            estado_germinacion='INICIAL',  # Solo estado inicial
            creado_por__isnull=False  # Tiene usuario
        ).exclude(
            Q(archivo_origen__isnull=False) & ~Q(archivo_origen='')  # Excluir importados
        ).select_related('creado_por')

        count = 0
        hoy = timezone.now().date()

        for germ in germinaciones:
            # Calcular días transcurridos desde fecha_siembra
            dias_transcurridos = (hoy - germ.fecha_siembra).days if germ.fecha_siembra else 0

            if verbose:
                self.stdout.write(
                    f'  📋 {germ.codigo} | '
                    f'Siembra: {germ.fecha_siembra} | '
                    f'Días: {dias_transcurridos} | '
                    f'Usuario: {germ.creado_por.username if germ.creado_por else "N/A"}'
                )

            # Verificar duplicado por si acaso (doble seguridad)
            if self._existe_recordatorio_reciente(germ.creado_por, germinacion=germ):
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f'    ⏭️  Ya tiene recordatorio reciente - SALTANDO'
                    ))
                continue

            if not dry_run:
                # Crear notificación
                self._crear_notificacion_germinacion(germ, dias_transcurridos)

                # Marcar como enviado (CRÍTICO para evitar duplicados)
                germ.recordatorio_5_dias_enviado = True
                germ.save(update_fields=['recordatorio_5_dias_enviado'])

            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {"[DRY-RUN] " if dry_run else ""}Recordatorio enviado: {germ.codigo} '
                f'({dias_transcurridos} días desde siembra)'
            ))
            count += 1

        if count == 0:
            self.stdout.write('  ℹ️  No hay germinaciones pendientes de recordatorio\n')

        return count

    def _procesar_polinizaciones(self, fecha_corte, dry_run, verbose):
        """
        Procesa polinizaciones que requieren recordatorio.

        Condiciones:
        - fechapol <= fecha_corte (ya pasaron 5+ días desde la polinización)
        - recordatorio_5_dias_enviado = False (no se ha enviado aún)
        - estado_polinizacion = 'INICIAL' (no ha sido actualizado)
        - creado_por no es nulo (tiene usuario asignado)
        """
        self.stdout.write('\n🌸 PROCESANDO POLINIZACIONES...\n')

        # Consulta con las condiciones correctas
        polinizaciones = Polinizacion.objects.filter(
            fechapol__lte=fecha_corte,  # Fecha base >= 5 días atrás
            recordatorio_5_dias_enviado=False,  # No enviado aún
            estado_polinizacion='INICIAL',  # Solo estado inicial
            creado_por__isnull=False  # Tiene usuario
        ).exclude(
            Q(archivo_origen__isnull=False) & ~Q(archivo_origen='')  # Excluir importados
        ).select_related('creado_por')

        count = 0
        hoy = timezone.now().date()

        for pol in polinizaciones:
            # Calcular días transcurridos desde fechapol
            dias_transcurridos = (hoy - pol.fechapol).days if pol.fechapol else 0

            if verbose:
                self.stdout.write(
                    f'  📋 {pol.codigo} | '
                    f'Polinización: {pol.fechapol} | '
                    f'Días: {dias_transcurridos} | '
                    f'Usuario: {pol.creado_por.username if pol.creado_por else "N/A"}'
                )

            # Verificar duplicado por si acaso (doble seguridad)
            if self._existe_recordatorio_reciente(pol.creado_por, polinizacion=pol):
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f'    ⏭️  Ya tiene recordatorio reciente - SALTANDO'
                    ))
                continue

            if not dry_run:
                # Crear notificación
                self._crear_notificacion_polinizacion(pol, dias_transcurridos)

                # Marcar como enviado (CRÍTICO para evitar duplicados)
                pol.recordatorio_5_dias_enviado = True
                pol.save(update_fields=['recordatorio_5_dias_enviado'])

            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {"[DRY-RUN] " if dry_run else ""}Recordatorio enviado: {pol.codigo} '
                f'({dias_transcurridos} días desde polinización)'
            ))
            count += 1

        if count == 0:
            self.stdout.write('  ℹ️  No hay polinizaciones pendientes de recordatorio\n')

        return count

    def _existe_recordatorio_reciente(self, usuario, germinacion=None, polinizacion=None):
        """
        Verifica si ya existe un recordatorio de 5 días para este registro.
        Doble seguridad además del flag en la BD.
        """
        filtro = Q(
            usuario=usuario,
            tipo='RECORDATORIO_5_DIAS'
        )

        if germinacion:
            filtro &= Q(germinacion=germinacion)
        elif polinizacion:
            filtro &= Q(polinizacion=polinizacion)

        return Notification.objects.filter(filtro).exists()

    def _crear_notificacion_germinacion(self, germinacion, dias_transcurridos):
        """Crea la notificación de recordatorio para una germinación"""
        try:
            titulo = f"📋 Revisa la germinación {germinacion.codigo}"

            mensaje = (
                f"Han pasado {dias_transcurridos} días desde la siembra.\n\n"
                f"🌱 Especie: {germinacion.genero} {germinacion.especie_variedad}\n"
                f"📅 Fecha de siembra: {germinacion.fecha_siembra.strftime('%d/%m/%Y') if germinacion.fecha_siembra else 'N/A'}\n"
                f"📊 Estado actual: {germinacion.estado_germinacion}\n"
                f"📈 Progreso: {germinacion.progreso_germinacion}%\n\n"
            )

            if germinacion.prediccion_fecha_estimada:
                dias_restantes = (germinacion.prediccion_fecha_estimada - timezone.now().date()).days
                if dias_restantes > 0:
                    mensaje += f"🔮 Fecha estimada: {germinacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')} ({dias_restantes} días restantes)\n\n"
                else:
                    mensaje += f"⚠️ Fecha estimada ya pasó: {germinacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')}\n\n"

            mensaje += "💡 Revisa la germinación y actualiza el estado del registro."

            detalles = {
                'germinacion_id': germinacion.id,
                'codigo': germinacion.codigo,
                'genero': germinacion.genero,
                'especie': germinacion.especie_variedad,
                'fecha_siembra': str(germinacion.fecha_siembra) if germinacion.fecha_siembra else None,
                'dias_transcurridos': dias_transcurridos,
                'estado': germinacion.estado_germinacion,
                'tipo_recordatorio': 'recordatorio_5_dias',
                'fecha_envio': str(timezone.now().date())
            }

            Notification.objects.create(
                usuario=germinacion.creado_por,
                germinacion=germinacion,
                tipo='RECORDATORIO_5_DIAS',
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )

            logger.info(f"Recordatorio 5 días creado para germinación {germinacion.id}")

        except Exception as e:
            logger.error(f"Error creando recordatorio para germinación {germinacion.id}: {e}")
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))

    def _crear_notificacion_polinizacion(self, polinizacion, dias_transcurridos):
        """Crea la notificación de recordatorio para una polinización"""
        try:
            titulo = f"📋 Revisa la polinización {polinizacion.codigo}"

            mensaje = (
                f"Han pasado {dias_transcurridos} días desde la polinización.\n\n"
                f"🌸 Tipo: {polinizacion.tipo_polinizacion}\n"
                f"📅 Fecha de polinización: {polinizacion.fechapol.strftime('%d/%m/%Y') if polinizacion.fechapol else 'N/A'}\n"
                f"📊 Estado actual: {polinizacion.estado_polinizacion}\n"
                f"📈 Progreso: {polinizacion.progreso_polinizacion}%\n"
            )

            if polinizacion.madre_especie:
                mensaje += f"🌱 Madre: {polinizacion.madre_genero} {polinizacion.madre_especie}\n"

            if polinizacion.padre_especie and polinizacion.tipo_polinizacion != 'SELF':
                mensaje += f"🌱 Padre: {polinizacion.padre_genero} {polinizacion.padre_especie}\n"

            mensaje += "\n"

            # Usar campos de predicción correctos
            fecha_predicha = polinizacion.fecha_maduracion_predicha or polinizacion.prediccion_fecha_estimada
            if fecha_predicha:
                dias_restantes = (fecha_predicha - timezone.now().date()).days
                if dias_restantes > 0:
                    mensaje += f"🔮 Fecha estimada maduración: {fecha_predicha.strftime('%d/%m/%Y')} ({dias_restantes} días restantes)\n\n"
                else:
                    mensaje += f"⚠️ Fecha estimada ya pasó: {fecha_predicha.strftime('%d/%m/%Y')}\n\n"

            mensaje += "💡 Revisa la polinización y actualiza el estado del registro."

            detalles = {
                'polinizacion_id': polinizacion.numero,
                'codigo': polinizacion.codigo,
                'tipo_polinizacion': polinizacion.tipo_polinizacion,
                'madre_especie': polinizacion.madre_especie,
                'padre_especie': polinizacion.padre_especie,
                'fecha_polinizacion': str(polinizacion.fechapol) if polinizacion.fechapol else None,
                'dias_transcurridos': dias_transcurridos,
                'estado': polinizacion.estado_polinizacion,
                'tipo_recordatorio': 'recordatorio_5_dias',
                'fecha_envio': str(timezone.now().date())
            }

            Notification.objects.create(
                usuario=polinizacion.creado_por,
                polinizacion=polinizacion,
                tipo='RECORDATORIO_5_DIAS',
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )

            logger.info(f"Recordatorio 5 días creado para polinización {polinizacion.numero}")

        except Exception as e:
            logger.error(f"Error creando recordatorio para polinización {polinizacion.numero}: {e}")
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))

    def _procesar_prediccion_germinaciones(self, fecha_prediccion, dry_run, verbose):
        """
        Procesa germinaciones con fecha de predicción próxima (5 días antes).

        Condiciones:
        - prediccion_fecha_estimada = fecha_prediccion (exactamente en 5 días)
        - No tiene recordatorio_prediccion_enviado
        - estado_germinacion != 'FINALIZADO'
        - creado_por no es nulo
        """
        self.stdout.write('\n🔮 PROCESANDO PREDICCIONES DE GERMINACIÓN...\n')

        germinaciones = Germinacion.objects.filter(
            prediccion_fecha_estimada=fecha_prediccion,
            creado_por__isnull=False
        ).exclude(
            estado_germinacion='FINALIZADO'
        ).exclude(
            Q(archivo_origen__isnull=False) & ~Q(archivo_origen='')
        ).select_related('creado_por')

        count = 0
        hoy = timezone.now().date()

        for germ in germinaciones:
            # Verificar si ya se envió notificación de predicción
            if self._existe_recordatorio_prediccion(germ.creado_por, germinacion=germ):
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f'    ⏭️  Ya tiene recordatorio de predicción - SALTANDO'
                    ))
                continue

            dias_restantes = (germ.prediccion_fecha_estimada - hoy).days

            if verbose:
                self.stdout.write(
                    f'  📋 {germ.codigo} | '
                    f'Predicción: {germ.prediccion_fecha_estimada} | '
                    f'Días restantes: {dias_restantes} | '
                    f'Usuario: {germ.creado_por.username if germ.creado_por else "N/A"}'
                )

            if not dry_run:
                # Crear notificación de predicción
                self._crear_notificacion_prediccion_germinacion(germ, dias_restantes)

            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {"[DRY-RUN] " if dry_run else ""}Recordatorio de predicción enviado: {germ.codigo} '
                f'(faltan {dias_restantes} días)'
            ))
            count += 1

        if count == 0:
            self.stdout.write('  ℹ️  No hay germinaciones con predicción próxima\n')

        return count

    def _procesar_prediccion_polinizaciones(self, fecha_prediccion, dry_run, verbose):
        """
        Procesa polinizaciones con fecha de predicción próxima (5 días antes).

        Condiciones:
        - prediccion_fecha_estimada o fecha_maduracion_predicha = fecha_prediccion
        - No tiene recordatorio_prediccion_enviado
        - estado_polinizacion != 'FINALIZADO'
        - creado_por no es nulo
        """
        self.stdout.write('\n🔮 PROCESANDO PREDICCIONES DE POLINIZACIÓN...\n')

        polinizaciones = Polinizacion.objects.filter(
            Q(prediccion_fecha_estimada=fecha_prediccion) | Q(fecha_maduracion_predicha=fecha_prediccion),
            creado_por__isnull=False
        ).exclude(
            estado_polinizacion='FINALIZADO'
        ).exclude(
            Q(archivo_origen__isnull=False) & ~Q(archivo_origen='')
        ).select_related('creado_por')

        count = 0
        hoy = timezone.now().date()

        for pol in polinizaciones:
            # Verificar si ya se envió notificación de predicción
            if self._existe_recordatorio_prediccion(pol.creado_por, polinizacion=pol):
                if verbose:
                    self.stdout.write(self.style.WARNING(
                        f'    ⏭️  Ya tiene recordatorio de predicción - SALTANDO'
                    ))
                continue

            fecha_pred = pol.fecha_maduracion_predicha or pol.prediccion_fecha_estimada
            dias_restantes = (fecha_pred - hoy).days

            if verbose:
                self.stdout.write(
                    f'  📋 {pol.codigo} | '
                    f'Predicción: {fecha_pred} | '
                    f'Días restantes: {dias_restantes} | '
                    f'Usuario: {pol.creado_por.username if pol.creado_por else "N/A"}'
                )

            if not dry_run:
                # Crear notificación de predicción
                self._crear_notificacion_prediccion_polinizacion(pol, dias_restantes)

            self.stdout.write(self.style.SUCCESS(
                f'  ✅ {"[DRY-RUN] " if dry_run else ""}Recordatorio de predicción enviado: {pol.codigo} '
                f'(faltan {dias_restantes} días)'
            ))
            count += 1

        if count == 0:
            self.stdout.write('  ℹ️  No hay polinizaciones con predicción próxima\n')

        return count

    def _existe_recordatorio_prediccion(self, usuario, germinacion=None, polinizacion=None):
        """
        Verifica si ya existe un recordatorio de predicción para este registro.
        """
        filtro = Q(
            usuario=usuario,
            tipo='RECORDATORIO_PREDICCION'
        )

        if germinacion:
            filtro &= Q(germinacion=germinacion)
        elif polinizacion:
            filtro &= Q(polinizacion=polinizacion)

        return Notification.objects.filter(filtro).exists()

    def _crear_notificacion_prediccion_germinacion(self, germinacion, dias_restantes):
        """Crea notificación de recordatorio de predicción para germinación"""
        try:
            titulo = f"🔮 Predicción próxima: {germinacion.codigo}"

            mensaje = (
                f"La fecha de germinación estimada está a {dias_restantes} días.\n\n"
                f"🌱 Especie: {germinacion.genero} {germinacion.especie_variedad}\n"
                f"📅 Fecha estimada: {germinacion.prediccion_fecha_estimada.strftime('%d/%m/%Y')}\n"
                f"📊 Estado actual: {germinacion.estado_germinacion}\n"
                f"📈 Progreso: {germinacion.progreso_germinacion}%\n\n"
                f"💡 Prepárate para revisar la germinación en los próximos días."
            )

            detalles = {
                'germinacion_id': germinacion.id,
                'codigo': germinacion.codigo,
                'genero': germinacion.genero,
                'especie': germinacion.especie_variedad,
                'fecha_prediccion': str(germinacion.prediccion_fecha_estimada),
                'dias_restantes': dias_restantes,
                'estado': germinacion.estado_germinacion,
                'tipo_recordatorio': 'recordatorio_prediccion',
                'fecha_envio': str(timezone.now().date())
            }

            Notification.objects.create(
                usuario=germinacion.creado_por,
                germinacion=germinacion,
                tipo='RECORDATORIO_PREDICCION',
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )

            logger.info(f"Recordatorio de predicción creado para germinación {germinacion.id}")

        except Exception as e:
            logger.error(f"Error creando recordatorio de predicción para germinación {germinacion.id}: {e}")
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))

    def _crear_notificacion_prediccion_polinizacion(self, polinizacion, dias_restantes):
        """Crea notificación de recordatorio de predicción para polinización"""
        try:
            titulo = f"🔮 Predicción próxima: {polinizacion.codigo}"

            fecha_pred = polinizacion.fecha_maduracion_predicha or polinizacion.prediccion_fecha_estimada
            tipo_pred = "maduración" if polinizacion.fecha_maduracion_predicha else "semillas"

            mensaje = (
                f"La fecha de {tipo_pred} estimada está a {dias_restantes} días.\n\n"
                f"🌸 Tipo: {polinizacion.tipo_polinizacion}\n"
                f"📅 Fecha estimada: {fecha_pred.strftime('%d/%m/%Y')}\n"
                f"📊 Estado actual: {polinizacion.estado_polinizacion}\n"
                f"📈 Progreso: {polinizacion.progreso_polinizacion}%\n"
            )

            if polinizacion.madre_especie:
                mensaje += f"🌱 Madre: {polinizacion.madre_genero} {polinizacion.madre_especie}\n"

            if polinizacion.padre_especie and polinizacion.tipo_polinizacion != 'SELF':
                mensaje += f"🌱 Padre: {polinizacion.padre_genero} {polinizacion.padre_especie}\n"

            mensaje += f"\n💡 Prepárate para revisar la polinización en los próximos días."

            detalles = {
                'polinizacion_id': polinizacion.numero,
                'codigo': polinizacion.codigo,
                'tipo_polinizacion': polinizacion.tipo_polinizacion,
                'madre_especie': polinizacion.madre_especie,
                'padre_especie': polinizacion.padre_especie,
                'fecha_prediccion': str(fecha_pred),
                'dias_restantes': dias_restantes,
                'estado': polinizacion.estado_polinizacion,
                'tipo_recordatorio': 'recordatorio_prediccion',
                'fecha_envio': str(timezone.now().date())
            }

            Notification.objects.create(
                usuario=polinizacion.creado_por,
                polinizacion=polinizacion,
                tipo='RECORDATORIO_PREDICCION',
                titulo=titulo,
                mensaje=mensaje,
                detalles_adicionales=detalles
            )

            logger.info(f"Recordatorio de predicción creado para polinización {polinizacion.numero}")

        except Exception as e:
            logger.error(f"Error creando recordatorio de predicción para polinización {polinizacion.numero}: {e}")
            self.stdout.write(self.style.ERROR(f'  ❌ Error: {e}'))
