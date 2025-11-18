import csv
import io
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..core.models import (
    Genero, Especie, Variedad, Ubicacion, Polinizacion, 
    Germinacion, SeguimientoGerminacion
)
from django.contrib.auth.models import User

# PELIGRO: NO EJECUTAR ESTOS COMANDOS - BORRAN TODOS LOS DATOS
# Solo descomentar si realmente necesitas limpiar la base de datos
#Polinizacion.objects.all().delete()
#Variedad.objects.all().delete()
#Especie.objects.all().delete()
#Genero.objects.all().delete()

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_csv_polinizaciones(request):
    """
    Sube e importa datos de polinizaciones desde un archivo CSV
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No se proporcionó ningún archivo'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    csv_file = request.FILES['file']
    
    if not csv_file.name.endswith('.csv'):
        return Response(
            {'error': 'El archivo debe ser un CSV'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Decodificar el archivo CSV
        decoded_file = csv_file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(decoded_file))
        
        imported_count = 0
        errors = []
        
        for row in csv_data:
            try:
                # Crear o obtener género
                genero, created = Genero.objects.get_or_create(
                    nombre=row.get('genero', '').strip()
                )
                
                # Crear o obtener especie
                especie, created = Especie.objects.get_or_create(
                    nombre=row.get('especie', '').strip(),
                    genero=genero
                )
                
                # Crear o obtener variedad
                variedad, created = Variedad.objects.get_or_create(
                    nombre=row.get('variedad', '').strip(),
                    especie=especie,
                    defaults={
                        'temporada_inicio': row.get('temporada_inicio', 'PRIMAVERA'),
                        'temporada_polinizacion': row.get('temporada_polinizacion', 'PRIMAVERA'),
                        'dias_germinacion_min': int(row.get('dias_germinacion_min', 30)),
                        'dias_germinacion_max': int(row.get('dias_germinacion_max', 60))
                    }
                )
                
                # Crear o obtener ubicación
                ubicacion = None
                if row.get('ubicacion'):
                    ubicacion, created = Ubicacion.objects.get_or_create(
                        nombre=row.get('ubicacion', '').strip()
                    )
                
                # Crear polinización
                fecha_pol = datetime.strptime(row.get('fecha_pol', ''), '%Y-%m-%d').date()
                fecha_mad = None
                if row.get('fecha_mad'):
                    fecha_mad = datetime.strptime(row.get('fecha_mad', ''), '%Y-%m-%d').date()
                
                fecha_siembra = None
                if row.get('fecha_siembra'):
                    fecha_siembra = datetime.strptime(row.get('fecha_siembra', ''), '%Y-%m-%d').date()
                
                fecha_replante = None
                if row.get('fecha_replante'):
                    fecha_replante = datetime.strptime(row.get('fecha_replante', ''), '%Y-%m-%d').date()
                
                polinizacion = Polinizacion.objects.create(
                    fecha_pol=fecha_pol,
                    fecha_mad=fecha_mad,
                    codigo=row.get('codigo', '').strip(),
                    variedad=variedad,
                    ubicacion=ubicacion,
                    responsable=request.user.get_full_name() or request.user.username,
                    creado_por=request.user,
                    cantidad=int(row.get('cantidad', 1)),
                    disponible=row.get('disponible', 'True').lower() == 'true',
                    archivo_origen=row.get('archivo_origen', ''),
                    fecha_siembra=fecha_siembra,
                    fecha_replante=fecha_replante,
                    clima=row.get('clima', ''),
                    cantidad_solicitada=int(row.get('cantidad_solicitada', 0)),
                    estado=row.get('estado', 'EN_PROCESO'),
                    observaciones=row.get('observaciones', '')
                )
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error en fila {imported_count + 1}: {str(e)}")
        
        return Response({
            'message': f'Se importaron {imported_count} polinizaciones exitosamente',
            'imported_count': imported_count,
            'errors': errors
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Error procesando el archivo: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_csv_germinaciones(request):
    """
    Sube e importa datos de germinaciones desde un archivo CSV
    """
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No se proporcionó ningún archivo'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    csv_file = request.FILES['file']
    
    if not csv_file.name.endswith('.csv'):
        return Response(
            {'error': 'El archivo debe ser un CSV'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Decodificar el archivo CSV
        decoded_file = csv_file.read().decode('utf-8')
        csv_data = csv.DictReader(io.StringIO(decoded_file))
        
        imported_count = 0
        errors = []
        
        for row in csv_data:
            try:
                # Buscar polinización por código si se proporciona
                polinizacion = None
                if row.get('codigo_polinizacion'):
                    try:
                        polinizacion = Polinizacion.objects.get(
                            codigo=row.get('codigo_polinizacion', '').strip()
                        )
                    except Polinizacion.DoesNotExist:
                        pass
                
                # Procesar fechas
                fecha_ingreso = datetime.strptime(row.get('fecha_ingreso', ''), '%Y-%m-%d').date()
                fecha_polinizacion = datetime.strptime(row.get('fecha_polinizacion', ''), '%Y-%m-%d').date()
                
                # Calcular días desde polinización
                dias_polinizacion = (fecha_ingreso - fecha_polinizacion).days
                
                germinacion = Germinacion.objects.create(
                    fecha_ingreso=fecha_ingreso,
                    fecha_polinizacion=fecha_polinizacion,
                    dias_polinizacion=dias_polinizacion,
                    nombre=row.get('nombre', '').strip(),
                    detalles_padres=row.get('detalles_padres', '').strip(),
                    tipo_polinizacion=row.get('tipo_polinizacion', ''),
                    finca=row.get('finca', ''),
                    numero_vivero=row.get('numero_vivero', ''),
                    numero_capsulas=int(row.get('numero_capsulas', 0)),
                    estado_capsulas=row.get('estado_capsulas', 'BUENO'),
                    cantidad_solicitada=int(row.get('cantidad_solicitada', 0)),
                    entrega_capsulas=row.get('entrega_capsulas', ''),
                    recibe_capsulas=row.get('recibe_capsulas', ''),
                    etapa_actual=row.get('etapa_actual', 'SIEMBRA'),
                    polinizacion=polinizacion,
                    observaciones=row.get('observaciones', ''),
                    creado_por=request.user,
                    responsable=request.user.get_full_name() or request.user.username
                )
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Error en fila {imported_count + 1}: {str(e)}")
        
        return Response({
            'message': f'Se importaron {imported_count} germinaciones exitosamente',
            'imported_count': imported_count,
            'errors': errors
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Error procesando el archivo: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_csv_templates(request):
    """
    Devuelve plantillas de CSV para que el usuario sepa qué formato usar
    """
    polinizaciones_template = [
        {
            'fecha_pol': '2024-01-15',
            'fecha_mad': '2024-03-15',
            'codigo': 'POL-001',
            'genero': 'Orchidaceae',
            'especie': 'Phalaenopsis',
            'variedad': 'Blanca',
            'ubicacion': 'Invernadero A',
            'cantidad': '10',
            'disponible': 'True',
            'archivo_origen': 'archivo_origen.pdf',
            'fecha_siembra': '2024-01-20',
            'fecha_replante': '2024-02-15',
            'clima': 'Templado',
            'cantidad_solicitada': '5',
            'estado': 'EN_PROCESO',
            'observaciones': 'Observaciones de la polinización'
        }
    ]
    
    germinaciones_template = [
        {
            'fecha_ingreso': '2024-01-20',
            'fecha_polinizacion': '2024-01-15',
            'nombre': 'Híbrido Phalaenopsis Blanca x Amarilla',
            'detalles_padres': 'Padre: Phalaenopsis Blanca, Madre: Phalaenopsis Amarilla',
            'tipo_polinizacion': 'Manual',
            'finca': 'Finca Principal',
            'numero_vivero': 'VIV-001',
            'numero_capsulas': '5',
            'estado_capsulas': 'BUENO',
            'cantidad_solicitada': '100',
            'entrega_capsulas': 'Juan Pérez',
            'recibe_capsulas': 'María García',
            'etapa_actual': 'SIEMBRA',
            'codigo_polinizacion': 'POL-001',
            'observaciones': 'Observaciones de la germinación'
        }
    ]
    
    return Response({
        'polinizaciones_template': polinizaciones_template,
        'germinaciones_template': germinaciones_template
    }) 