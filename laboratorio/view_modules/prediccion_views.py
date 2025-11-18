"""
Vistas para predicciones y alertas
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.http import JsonResponse
from datetime import datetime, timedelta
import logging

from ..models import Polinizacion, Germinacion
from ..serializers import PolinizacionSerializer
from ..services.prediccion_service import prediccion_service
from ..permissions import require_germinacion_access, require_polinizacion_access

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_germinacion_access('view')
def prediccion_germinacion(request):
    """Predicción de germinación (requiere acceso a germinaciones)"""
    try:
        logger.info(f"Calculando predicción de germinación para usuario: {request.user.username}")
        
        resultado = prediccion_service.calcular_prediccion_germinacion(request.data)
        
        logger.info("Predicción de germinación calculada exitosamente")
        return Response(resultado)
        
    except Exception as e:
        logger.error(f"Error en predicción de germinación: {e}")
        return Response(
            {'error': f'Error en predicción: {str(e)}'},
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_polinizacion_access('view')
def prediccion_polinizacion(request):
    """Predicción de polinización (requiere acceso a polinizaciones)"""
    try:
        logger.info(f"Calculando predicción de polinización para usuario: {request.user.username}")
        
        resultado = prediccion_service.calcular_prediccion_polinizacion(request.data)
        
        logger.info("Predicción de polinización calculada exitosamente")
        return Response(resultado)
        
    except Exception as e:
        logger.error(f"Error en predicción de polinización: {e}")
        return Response(
            {'error': f'Error en predicción: {str(e)}'},
            status=500
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def prediccion_completa(request):
    """Predicción completa (germinación + polinización)"""
    try:
        logger.info(f"Calculando predicción completa para usuario: {request.user.username}")
        
        # Calcular ambas predicciones
        prediccion_germ = prediccion_service.calcular_prediccion_germinacion(request.data)
        prediccion_pol = prediccion_service.calcular_prediccion_polinizacion(request.data)
        
        resultado = {
            'germinacion': prediccion_germ,
            'polinizacion': prediccion_pol,
            'timestamp': datetime.now().isoformat(),
            'usuario': request.user.username
        }
        
        logger.info("Predicción completa calculada exitosamente")
        return Response(resultado)
        
    except Exception as e:
        logger.error(f"Error en predicción completa: {e}")
        return Response(
            {'error': f'Error en predicción: {str(e)}'},
            status=500
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def predicciones_alertas(request):
    """Obtiene predicciones para mostrar alertas filtradas por usuario responsable"""
    try:
        user = request.user
        logger.info(f"Obteniendo alertas para usuario: {user.username}")
        
        # Obtener polinizaciones del usuario que necesitan atención
        fecha_limite = datetime.now().date() + timedelta(days=30)
        
        # Filtrar por usuario (creado_por o responsable)
        from django.db.models import Q
        
        polinizaciones_alertas = Polinizacion.objects.filter(
            fechamad__lte=fecha_limite,
            estado__in=['EN_PROCESO', 'PENDIENTE']
        ).filter(
            Q(creado_por=user) | 
            Q(responsable__icontains=user.username) |
            Q(responsable__icontains=f"{user.first_name} {user.last_name}".strip())
        ).order_by('fechamad')
        
        alertas = []
        for pol in polinizaciones_alertas:
            dias_restantes = (pol.fechamad - datetime.now().date()).days if pol.fechamad else None
            
            alertas.append({
                'id': pol.numero,
                'codigo': pol.codigo,
                'tipo': 'polinizacion',
                'mensaje': f'Polinización {pol.codigo} lista para cosecha',
                'dias_restantes': dias_restantes,
                'fecha_estimada': pol.fechamad.isoformat() if pol.fechamad else None,
                'prioridad': 'alta' if dias_restantes and dias_restantes <= 7 else 'media',
                'datos': PolinizacionSerializer(pol).data
            })
        
        logger.info(f"Encontradas {len(alertas)} alertas para el usuario")
        return Response({
            'alertas': alertas,
            'total': len(alertas),
            'usuario': user.username
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo alertas: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cambiar_estado_polinizacion(request, pk):
    """Cambia el estado de una polinización desde las alertas"""
    try:
        polinizacion = Polinizacion.objects.get(numero=pk)
        nuevo_estado = request.data.get('estado')
        
        if not nuevo_estado:
            return Response(
                {'error': 'El campo estado es requerido'}, 
                status=400
            )
        
        # Validar que el estado sea válido
        estados_validos = [choice[0] for choice in Polinizacion.ESTADOS_POLINIZACION]
        if nuevo_estado not in estados_validos:
            return Response(
                {'error': f'Estado inválido. Estados válidos: {", ".join(estados_validos)}'}, 
                status=400
            )
        
        estado_anterior = polinizacion.estado
        polinizacion.estado = nuevo_estado
        polinizacion.save()
        
        # Crear notificación de cambio de estado
        try:
            from ..services import NotificationService
            notification_service = NotificationService()
            notification_service.crear_notificacion_polinizacion(
                usuario=request.user,
                polinizacion=polinizacion,
                tipo='ESTADO_POLINIZACION_ACTUALIZADO'
            )
        except Exception as e:
            logger.warning(f"Error al crear notificación: {e}")
        
        logger.info(f"Estado de polinización {pk} actualizado de {estado_anterior} a {nuevo_estado}")
        
        return Response({
            'mensaje': f'Estado de polinización actualizado de "{estado_anterior}" a "{nuevo_estado}"',
            'polinizacion': PolinizacionSerializer(polinizacion).data
        })
        
    except Polinizacion.DoesNotExist:
        return Response(
            {'error': 'Polinización no encontrada'}, 
            status=404
        )
    except Exception as e:
        logger.error(f"Error cambiando estado de polinización {pk}: {e}")
        return Response(
            {'error': f'Error interno: {str(e)}'}, 
            status=500
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def estadisticas_modelos(request):
    """Estadísticas de modelos de predicción"""
    try:
        # Estadísticas simuladas de modelos de ML
        # En una implementación real, esto consultaría métricas reales

        estadisticas = {
            'modelo_germinacion': {
                'version': '1.0',
                'precision': 0.85,
                'recall': 0.82,
                'f1_score': 0.83,
                'ultima_actualizacion': '2024-01-15',
                'predicciones_realizadas': 1250,
                'accuracy': 0.84
            },
            'modelo_polinizacion': {
                'version': '1.0',
                'precision': 0.78,
                'recall': 0.75,
                'f1_score': 0.76,
                'ultima_actualizacion': '2024-01-10',
                'predicciones_realizadas': 890,
                'accuracy': 0.77
            },
            'estadisticas_generales': {
                'total_predicciones': 2140,
                'predicciones_exitosas': 1712,
                'tasa_exito': 0.80,
                'tiempo_promedio_respuesta': '0.3s'
            }
        }

        return Response(estadisticas)

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de modelos: {e}")
        return Response({'error': str(e)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@require_germinacion_access('view')
def especies_promedios_germinacion(request):
    """
    Obtiene promedios históricos de germinación por especie
    Requiere acceso a germinaciones
    """
    try:
        logger.info(f"Usuario {request.user.username} consultando promedios de especies")

        # Obtener promedios del servicio
        promedios = prediccion_service.especies_promedios

        # Opcional: filtrar por especie específica
        especie_filtro = request.GET.get('especie', None)
        if especie_filtro:
            if especie_filtro in promedios:
                return Response({
                    'especie': especie_filtro,
                    'datos': promedios[especie_filtro]
                })
            else:
                return Response(
                    {'error': f'No hay datos históricos para la especie "{especie_filtro}"'},
                    status=404
                )

        # Convertir a lista ordenada por promedio de días
        especies_list = []
        for especie, datos in promedios.items():
            especies_list.append({
                'especie': especie,
                **datos
            })

        # Ordenar por número de registros (más confiables primero)
        especies_list.sort(key=lambda x: x['num_registros'], reverse=True)

        return Response({
            'total_especies': len(especies_list),
            'especies': especies_list,
            'mensaje': f'Se encontraron promedios históricos para {len(especies_list)} especies',
            'fuente': 'datos_historicos_csv'
        })

    except Exception as e:
        logger.error(f"Error obteniendo promedios de especies: {e}")
        return Response({'error': str(e)}, status=500)