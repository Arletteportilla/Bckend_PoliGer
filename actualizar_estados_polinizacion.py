"""
Script para actualizar estados de polinizaciones existentes
Sincroniza el estado_polinizacion basado en fechamad
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from laboratorio.core.models import Polinizacion
from django.utils import timezone

def actualizar_estados_polinizacion():
    """Actualiza los estados de todas las polinizaciones"""
    print("🔄 Actualizando estados de polinizaciones...")
    
    polinizaciones = Polinizacion.objects.all()
    total = polinizaciones.count()
    actualizadas = 0
    
    for pol in polinizaciones:
        estado_anterior = pol.estado_polinizacion
        progreso_anterior = pol.progreso_polinizacion
        
        # Determinar estado basado en fechamad
        if pol.fechamad:
            # Si tiene fecha de maduración, está finalizada
            pol.estado_polinizacion = 'FINALIZADO'
            pol.progreso_polinizacion = 100
        elif pol.fechapol:
            # Si tiene fecha de polinización pero no de maduración, está en proceso
            pol.estado_polinizacion = 'EN_PROCESO'
            pol.progreso_polinizacion = 50
        else:
            # Si no tiene ninguna fecha, está inicial
            pol.estado_polinizacion = 'INICIAL'
            pol.progreso_polinizacion = 0
        
        # Guardar solo si cambió
        if (pol.estado_polinizacion != estado_anterior or 
            pol.progreso_polinizacion != progreso_anterior):
            pol.save()
            actualizadas += 1
            print(f"  ✅ Polinización {pol.numero} ({pol.codigo}): "
                  f"{estado_anterior} -> {pol.estado_polinizacion}, "
                  f"{progreso_anterior}% -> {pol.progreso_polinizacion}%")
    
    print(f"\n✅ Proceso completado:")
    print(f"   Total de polinizaciones: {total}")
    print(f"   Actualizadas: {actualizadas}")
    print(f"   Sin cambios: {total - actualizadas}")

if __name__ == '__main__':
    actualizar_estados_polinizacion()
