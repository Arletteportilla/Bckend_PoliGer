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


# =============================================================================
# PREDICCIÓN CON ML (XGBoost)
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_polinizacion_access('view')
def prediccion_polinizacion_ml(request):
    """
    Predicción de DIAS_MADURACION usando XGBoost
    Endpoint mejorado que usa el modelo de Machine Learning entrenado

    Requiere acceso a polinizaciones

    Request body:
        {
            "fechapol": "2024-01-15",
            "genero": "Cattleya",
            "especie": "Cattleya maxima",
            "ubicacion": "Vivero 1",
            "responsable": "Usuario Ejemplo",
            "Tipo": "SELF",
            "cantidad": 3,
            "disponible": 1
        }

    Response:
        {
            "dias_estimados": 120,
            "fecha_polinizacion": "2024-01-15",
            "fecha_estimada_maduracion": "2024-05-14",
            "confianza": 85.0,
            "nivel_confianza": "alta",
            "metodo": "XGBoost",
            "modelo": "polinizacion.joblib",
            ...
        }
    """
    try:
        # USAR NUEVO PREDICTOR XGBOOST
        from ..ml.predictors import get_predictor

        logger.info(f"🔮 Usuario {request.user.username} solicitando predicción de polinización (XGBoost)")
        logger.info(f"Datos recibidos: {request.data}")

        # Validar campos requeridos
        required_fields = ['fechapol', 'genero', 'especie', 'ubicacion', 'responsable', 'Tipo', 'cantidad', 'disponible']
        missing_fields = [field for field in required_fields if field not in request.data]

        if missing_fields:
            logger.warning(f"Campos faltantes: {missing_fields}")
            return Response({
                'error': 'Datos de entrada inválidos',
                'details': {field: ['Este campo es requerido'] for field in missing_fields}
            }, status=400)

        # Obtener predictor (singleton)
        predictor = get_predictor()

        # Verificar que el modelo esté cargado
        if not predictor.model_loaded:
            logger.error("Modelo XGBoost no está cargado")
            return Response({
                'error': 'Modelo de predicción no disponible',
                'details': 'El modelo XGBoost no pudo ser cargado. Verifique los archivos del modelo.',
                'codigo': 'MODEL_NOT_LOADED'
            }, status=503)

        try:
            # Realizar predicción usando el nuevo predictor XGBoost
            logger.info("🎯 Llamando a XGBoostPolinizacionPredictor.predecir()...")

            resultado = predictor.predecir(
                fechapol=request.data['fechapol'],
                genero=request.data['genero'],
                especie=request.data['especie'],
                ubicacion=request.data['ubicacion'],
                responsable=request.data['responsable'],
                tipo=request.data['Tipo'],
                cantidad=request.data.get('cantidad', 1),
                disponible=request.data.get('disponible', 1)
            )

            logger.info("=" * 80)
            logger.info("✅ PREDICCIÓN EXITOSA - XGBOOST")
            logger.info("=" * 80)
            logger.info(f"📊 Días estimados: {resultado['dias_estimados']} días")
            logger.info(f"📅 Fecha estimada: {resultado['fecha_estimada_maduracion']}")
            logger.info(f"💯 Confianza: {resultado['confianza']}%")
            logger.info(f"🔢 Features usadas: {resultado['features_count']}")
            logger.info(f"⚠️  Categorías nuevas: {resultado.get('categorias_nuevas', 0)}")
            logger.info("=" * 80)

            return Response(resultado, status=200)

        except ValueError as e:
            logger.error("=" * 80)
            logger.error("❌ ERROR: VALOR INVÁLIDO (ValueError)")
            logger.error("=" * 80)
            logger.error(f"Mensaje: {e}")
            logger.exception(e)
            return Response({
                'error': 'Error de valor en predicción',
                'details': str(e),
                'codigo': 'INVALID_VALUE',
                'tipo': 'ValueError'
            }, status=400)

        except KeyError as e:
            logger.error("=" * 80)
            logger.error("❌ ERROR: CLAVE FALTANTE (KeyError)")
            logger.error("=" * 80)
            logger.error(f"Clave faltante: {e}")
            logger.exception(e)
            return Response({
                'error': 'Error de datos faltantes',
                'details': f'Campo requerido faltante: {str(e)}',
                'codigo': 'MISSING_FIELD',
                'tipo': 'KeyError'
            }, status=400)

        except Exception as e:
            logger.error("=" * 80)
            logger.error("❌ ERROR INESPERADO EN PREDICCIÓN")
            logger.error("=" * 80)
            logger.error(f"Tipo: {type(e).__name__}")
            logger.error(f"Mensaje: {e}")
            logger.exception(e)
            return Response({
                'error': 'Error inesperado durante la predicción',
                'details': str(e),
                'error_type': type(e).__name__,
                'codigo': 'UNEXPECTED_ERROR'
            }, status=500)

    except Exception as e:
        logger.error(f"❌ Error inesperado en predicción ML: {e}")
        logger.exception(e)
        return Response({
            'error': 'Error inesperado en la predicción',
            'details': str(e),
            'codigo': 'INTERNAL_ERROR'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def model_info(request):
    """
    Obtiene información sobre el modelo de predicción de polinización

    Response:
        {
            "loaded": true,
            "model_type": "XGBRegressor",
            "n_features": 17,
            "features": [...],
            "categorical_columns": [...],
            ...
        }
    """
    try:
        from ..ml.predictors.pollination_predictor import pollination_predictor

        logger.info(f"Usuario {request.user.username} consultando información del modelo")

        info = pollination_predictor.get_model_info()

        return Response(info, status=200)

    except Exception as e:
        logger.error(f"Error obteniendo información del modelo: {e}")
        return Response({
            'error': 'Error obteniendo información del modelo',
            'details': str(e)
        }, status=500)


# =============================================================================
# PREDICCIÓN DE GERMINACIÓN CON ML (Random Forest)
# =============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@require_germinacion_access('view')
def prediccion_germinacion_ml(request):
    """
    Predicción de DIAS_GERMINACION usando Random Forest
    Endpoint que usa el modelo Random Forest entrenado con pipeline estructurado

    Requiere acceso a germinaciones

    Request body:
        {
            "fecha_siembra": "2024-12-04",
            "especie": "Phragmipedium kovachii",
            "clima": "IC",
            "estado_capsula": "Cerrada",
            "s_stock": 10,
            "c_solic": 2,
            "dispone": 1
        }

    Response:
        {
            "dias_estimados": 87,
            "fecha_estimada_germinacion": "2025-03-01",
            "confianza": 85,
            "nivel_confianza": "alta",
            "modelo": "Random Forest",
            "detalles": {
                "especie_agrupada": "Phragmipedium kovachii",
                "especie_original": "Phragmipedium kovachii",
                "clima": "IC",
                "estado_capsula": "Cerrada",
                "features_usadas": 129
            }
        }
    """
    try:
        # USAR PREDICTOR RANDOM FOREST
        from ..ml.predictors import get_germinacion_predictor

        logger.info(f"Usuario {request.user.username} solicitando prediccion de germinacion (Random Forest)")
        logger.info(f"Datos recibidos: {request.data}")

        # Validar campos requeridos
        required_fields = ['fecha_siembra', 'especie', 'clima', 'estado_capsula']
        missing_fields = [field for field in required_fields if field not in request.data]

        if missing_fields:
            logger.warning(f"Campos faltantes: {missing_fields}")
            return Response({
                'error': 'Datos de entrada invalidos',
                'details': {field: ['Este campo es requerido'] for field in missing_fields}
            }, status=400)

        # Obtener predictor (singleton)
        predictor = get_germinacion_predictor()

        # Verificar que el modelo esté cargado
        if not predictor.model_loaded:
            logger.error("Modelo Random Forest de germinacion no esta cargado")
            return Response({
                'error': 'Modelo de prediccion no disponible',
                'details': 'El modelo Random Forest no pudo ser cargado. Verifique los archivos del modelo.',
                'codigo': 'MODEL_NOT_LOADED'
            }, status=503)

        try:
            # Realizar predicción usando el predictor Random Forest
            logger.info("Llamando a GerminacionPredictor.predict_dias_germinacion()...")

            resultado = predictor.predict_dias_germinacion(
                fecha_siembra=request.data['fecha_siembra'],
                especie=request.data['especie'],
                clima=request.data['clima'],
                estado_capsula=request.data['estado_capsula'],
                s_stock=request.data.get('s_stock', 0),
                c_solic=request.data.get('c_solic', 0),
                dispone=request.data.get('dispone', 0)
            )

            logger.info("=" * 80)
            logger.info("PREDICCION EXITOSA - RANDOM FOREST GERMINACION")
            logger.info("=" * 80)
            logger.info(f"Dias estimados: {resultado['dias_estimados']} dias")
            logger.info(f"Fecha estimada: {resultado['fecha_estimada_germinacion']}")
            logger.info(f"Confianza: {resultado['confianza']}%")
            logger.info(f"Features usadas: {resultado['detalles']['features_usadas']}")
            logger.info(f"Especie agrupada: {resultado['detalles']['especie_agrupada']}")
            logger.info("=" * 80)

            return Response(resultado, status=200)

        except ValueError as e:
            logger.error("=" * 80)
            logger.error("ERROR: VALOR INVALIDO (ValueError)")
            logger.error("=" * 80)
            logger.error(f"Mensaje: {e}")
            logger.exception(e)
            return Response({
                'error': 'Error de valor en prediccion',
                'details': str(e),
                'codigo': 'INVALID_VALUE',
                'tipo': 'ValueError'
            }, status=400)

        except KeyError as e:
            logger.error("=" * 80)
            logger.error("ERROR: CLAVE FALTANTE (KeyError)")
            logger.error("=" * 80)
            logger.error(f"Clave faltante: {e}")
            logger.exception(e)
            return Response({
                'error': 'Error de datos faltantes',
                'details': f'Campo requerido faltante: {str(e)}',
                'codigo': 'MISSING_FIELD',
                'tipo': 'KeyError'
            }, status=400)

        except Exception as e:
            # Error en el pipeline del modelo (alineación, procesamiento, etc.)
            logger.error("=" * 80)
            logger.error("ERROR EN PIPELINE DEL MODELO")
            logger.error("=" * 80)
            logger.error(f"Tipo: {type(e).__name__}")
            logger.error(f"Mensaje: {e}")
            logger.exception(e)
            return Response({
                'error': 'Error en el pipeline de prediccion',
                'details': str(e),
                'error_type': type(e).__name__,
                'codigo': 'PIPELINE_ERROR',
                'mensaje': 'Ocurrio un error durante el procesamiento de los datos o la alineacion de features'
            }, status=500)

    except Exception as e:
        logger.error(f"Error inesperado en prediccion ML de germinacion: {e}")
        logger.exception(e)
        return Response({
            'error': 'Error inesperado en la prediccion',
            'details': str(e),
            'codigo': 'INTERNAL_ERROR'
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def germinacion_model_info(request):
    """
    Obtiene información sobre el modelo de predicción de germinación

    Response:
        {
            "loaded": true,
            "model_type": "RandomForestRegressor",
            "n_features": 129,
            "top_especies": 100,
            "encoding": "One-Hot",
            "scaler": "RobustScaler",
            ...
        }
    """
    try:
        from ..ml.predictors import get_germinacion_predictor

        logger.info(f"Usuario {request.user.username} consultando informacion del modelo de germinacion")

        predictor = get_germinacion_predictor()

        if not predictor.model_loaded:
            return Response({
                'loaded': False,
                'error': 'Modelo no cargado'
            }, status=503)

        info = {
            'loaded': True,
            'model_type': 'RandomForestRegressor',
            'n_features': len(predictor.feature_order) if predictor.feature_order else 0,
            'n_numeric_features': len(predictor.numeric_cols) if predictor.numeric_cols else 0,
            'top_especies': len(predictor.top_especies) if predictor.top_especies else 0,
            'categorical_features': predictor.categorical_features if predictor.categorical_features else [],
            'numerical_features': predictor.numerical_features if predictor.numerical_features else [],
            'encoding': 'One-Hot',
            'scaler': 'RobustScaler',
            'pipeline_steps': [
                '1. Feature Engineering (temporales, ciclicas, derivadas)',
                '2. One-Hot Encoding',
                '3. Feature Alignment',
                '4. Normalization + Prediction'
            ],
            'metricas': {
                'RMSE': '~52 dias',
                'MAE': '~37 dias',
                'R2': '~0.85'
            }
        }

        return Response(info, status=200)

    except Exception as e:
        logger.error(f"Error obteniendo informacion del modelo de germinacion: {e}")
        return Response({
            'error': 'Error obteniendo informacion del modelo',
            'details': str(e)
        }, status=500)