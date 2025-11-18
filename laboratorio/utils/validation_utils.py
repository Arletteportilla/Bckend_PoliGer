"""
Utilidades de validación para el backend
"""
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from django.core.exceptions import ValidationError
import re


def validate_codigo(codigo: str, max_length: int = 50) -> str:
    """
    Valida y limpia un código
    """
    if not codigo:
        raise ValidationError("El código es obligatorio")
    
    cleaned_codigo = str(codigo).strip()
    
    if not cleaned_codigo:
        raise ValidationError("El código no puede estar vacío")
    
    if len(cleaned_codigo) > max_length:
        raise ValidationError(f"El código no puede tener más de {max_length} caracteres")
    
    # Validar caracteres permitidos (opcional)
    if not re.match(r'^[A-Za-z0-9\-_]+$', cleaned_codigo):
        raise ValidationError("El código solo puede contener letras, números, guiones y guiones bajos")
    
    return cleaned_codigo


def validate_date_field(date_value: Any, field_name: str, allow_future: bool = False) -> date:
    """
    Valida un campo de fecha
    """
    if not date_value:
        raise ValidationError(f"La {field_name} es obligatoria")
    
    if isinstance(date_value, str):
        try:
            parsed_date = datetime.strptime(date_value, '%Y-%m-%d').date()
        except ValueError:
            raise ValidationError(f"Formato de {field_name} inválido (use YYYY-MM-DD)")
    elif isinstance(date_value, date):
        parsed_date = date_value
    else:
        raise ValidationError(f"Tipo de {field_name} inválido")
    
    if not allow_future and parsed_date > date.today():
        raise ValidationError(f"La {field_name} no puede ser futura")
    
    return parsed_date


def validate_positive_integer(value: Any, field_name: str, max_value: Optional[int] = None) -> int:
    """
    Valida un entero positivo
    """
    try:
        int_value = int(value)
    except (ValueError, TypeError):
        raise ValidationError(f"El {field_name} debe ser un número válido")
    
    if int_value <= 0:
        raise ValidationError(f"El {field_name} debe ser mayor a 0")
    
    if max_value and int_value > max_value:
        raise ValidationError(f"El {field_name} no puede ser mayor a {max_value}")
    
    return int_value


def validate_text_field(value: Any, field_name: str, max_length: int, required: bool = False) -> str:
    """
    Valida un campo de texto
    """
    if not value:
        if required:
            raise ValidationError(f"El {field_name} es obligatorio")
        return ""
    
    cleaned_value = str(value).strip()
    
    if required and not cleaned_value:
        raise ValidationError(f"El {field_name} no puede estar vacío")
    
    if len(cleaned_value) > max_length:
        raise ValidationError(f"El {field_name} no puede tener más de {max_length} caracteres")
    
    return cleaned_value


def validate_date_range(start_date: date, end_date: date, start_field: str, end_field: str):
    """
    Valida que una fecha de inicio sea anterior a una fecha de fin
    """
    if start_date >= end_date:
        raise ValidationError(f"La {start_field} debe ser anterior a la {end_field}")


def collect_validation_errors(validation_functions: List[callable]) -> Dict[str, List[str]]:
    """
    Ejecuta múltiples funciones de validación y recolecta los errores
    """
    errors = {}
    
    for validation_func in validation_functions:
        try:
            validation_func()
        except ValidationError as e:
            field_name = getattr(validation_func, 'field_name', 'general')
            if field_name not in errors:
                errors[field_name] = []
            errors[field_name].append(str(e))
    
    return errors


class ValidationHelper:
    """
    Clase helper para validaciones complejas
    """
    
    def __init__(self):
        self.errors = {}
    
    def add_error(self, field: str, message: str):
        """Agrega un error de validación"""
        if field not in self.errors:
            self.errors[field] = []
        self.errors[field].append(message)
    
    def validate_codigo_unique(self, codigo: str, model_class, instance=None, field_name='codigo'):
        """Valida que un código sea único"""
        if not codigo:
            return
        
        queryset = model_class.objects.filter(**{field_name: codigo})
        if instance:
            queryset = queryset.exclude(pk=instance.pk)
        
        if queryset.exists():
            self.add_error(field_name, f'Ya existe un registro con el código "{codigo}"')
    
    def validate_required_fields(self, data: Dict[str, Any], required_fields: Dict[str, str]):
        """Valida campos obligatorios"""
        for field, message in required_fields.items():
            if not data.get(field):
                self.add_error(field, message)
            elif isinstance(data[field], str) and not data[field].strip():
                self.add_error(field, f"{field.replace('_', ' ').title()} no puede estar vacío")
    
    def validate_date_coherence(self, data: Dict[str, Any], date_pairs: List[tuple]):
        """Valida coherencia entre fechas"""
        for start_field, end_field, message in date_pairs:
            start_date = data.get(start_field)
            end_date = data.get(end_field)
            
            if start_date and end_date:
                if isinstance(start_date, str):
                    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                if isinstance(end_date, str):
                    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if start_date >= end_date:
                    self.add_error(end_field, message)
    
    def has_errors(self) -> bool:
        """Verifica si hay errores"""
        return bool(self.errors)
    
    def raise_if_errors(self):
        """Lanza ValidationError si hay errores"""
        if self.has_errors():
            raise ValidationError(self.errors)
    
    def get_errors_dict(self) -> Dict[str, List[str]]:
        """Obtiene el diccionario de errores"""
        return self.errors.copy()