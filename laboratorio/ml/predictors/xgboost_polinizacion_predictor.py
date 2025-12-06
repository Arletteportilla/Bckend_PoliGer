# -*- coding: utf-8 -*-
"""
Predictor XGBoost para Polinización
====================================
Usa el modelo XGBoost entrenado con 95.63% R² (RMSE: 19.43 días)

Este predictor implementa el mismo preprocessing que se usó en entrenamiento:
- 17 features (5 temporales + 4 cíclicas + 5 categóricas + 2 numéricas)
- LabelEncoder para variables categóricas (NO Target/Frequency Encoding)
- NO se usa escalado (XGBoost no lo requiere)
"""

import joblib
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os
import logging

logger = logging.getLogger(__name__)


class XGBoostPolinizacionPredictor:
    """Predictor usando modelo XGBoost para Polinización"""

    def __init__(self):
        self.model = None
        self.label_encoders = None
        self.feature_list = None
        self.metadata = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        """Carga el modelo XGBoost y los label encoders"""
        try:
            # Ruta al modelo
            base_path = os.path.join(
                os.path.dirname(__file__),
                '..',
                '..',
                'modelos',
                'Polinizacion'
            )

            model_path = os.path.join(base_path, 'polinizacion.joblib')
            encoders_path = os.path.join(base_path, 'label_encoders.pkl')
            metadata_path = os.path.join(base_path, 'features_metadata.json')

            # Cargar modelo
            if not os.path.exists(model_path):
                logger.error(f"Modelo no encontrado: {model_path}")
                return

            logger.info(f"Cargando modelo XGBoost desde: {model_path}")
            self.model = joblib.load(model_path)
            logger.info(f"✓ Modelo XGBoost cargado correctamente")

            # Cargar encoders
            if os.path.exists(encoders_path):
                self.label_encoders = joblib.load(encoders_path)
                logger.info(f"✓ Label encoders cargados: {list(self.label_encoders.keys())}")
            else:
                logger.warning(f"Label encoders no encontrados: {encoders_path}")
                return

            # Cargar metadata (opcional)
            if os.path.exists(metadata_path):
                import json
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    self.metadata = json.load(f)
                    self.feature_list = self.metadata.get('feature_list', [])
                logger.info(f"✓ Metadata cargada: {len(self.feature_list)} features")
            else:
                # Hardcodear la lista de features si no hay metadata
                self.feature_list = [
                    'mes_pol', 'dia_año_pol', 'trimestre_pol', 'año_pol', 'semana_año',
                    'mes_sin', 'mes_cos', 'dia_año_sin', 'dia_año_cos',
                    'genero_encoded', 'especie_encoded', 'ubicacion_encoded',
                    'responsable_encoded', 'Tipo_encoded', 'cantidad', 'disponible'
                ]
                logger.warning(f"Metadata no encontrada, usando lista de features por defecto")

            self.model_loaded = True
            logger.info("="*60)
            logger.info("MODELO XGBOOST POLINIZACIÓN CARGADO EXITOSAMENTE")
            logger.info(f"  - Precisión: 95.63% (R²)")
            logger.info(f"  - RMSE: ±19.43 días")
            logger.info(f"  - MAE: ±10.22 días")
            logger.info(f"  - Features: {len(self.feature_list)}")
            logger.info("="*60)

        except Exception as e:
            logger.error(f"Error cargando modelo XGBoost: {e}", exc_info=True)
            self.model_loaded = False

    def _normalizar_especie(self, especie, genero):
        """
        Normaliza la especie removiendo el género si viene incluido

        Ejemplos:
            'Acineta antioquiae' → 'antioquiae'
            'Cattleya maxima' → 'maxima'
            'antioquiae' → 'antioquiae' (sin cambios)
        """
        especie_limpia = str(especie).strip()
        genero_limpio = str(genero).strip()

        # Si la especie empieza con el género, removerlo
        if especie_limpia.lower().startswith(genero_limpio.lower()):
            especie_limpia = especie_limpia[len(genero_limpio):].strip()
            logger.info(f"  ✓ Especie normalizada: '{especie}' → '{especie_limpia}'")

        return especie_limpia

    def _normalizar_ubicacion(self, ubicacion):
        """
        Normaliza la ubicación al formato esperado por el modelo

        Ejemplos:
            'V-0 - M-1A - P-0' → 'V-0 M-1A P-A'
            'V-1 - M-10B - P-B' → 'V-1 M-10B P-B'
            'V-2 M-5A' → 'V-2 M-5A' (sin cambios)
        """
        ubicacion_limpia = str(ubicacion).strip()

        # Remover guiones extra (espacios + guion + espacios)
        ubicacion_limpia = ubicacion_limpia.replace(' - ', ' ')

        # Normalizar P-0 a P-A, P-1 a P-B, etc.
        # Solo si termina en P-[número]
        if 'P-' in ubicacion_limpia:
            partes = ubicacion_limpia.split()
            for i, parte in enumerate(partes):
                if parte.startswith('P-') and len(parte) == 3:
                    numero = parte[2]
                    if numero.isdigit():
                        # P-0 → P-A, P-1 → P-B, etc.
                        letra = chr(ord('A') + int(numero))
                        partes[i] = f'P-{letra}'
            ubicacion_limpia = ' '.join(partes)

        if ubicacion_limpia != ubicacion:
            logger.info(f"  ✓ Ubicación normalizada: '{ubicacion}' → '{ubicacion_limpia}'")

        return ubicacion_limpia

    def _normalizar_responsable(self, responsable):
        """
        Normaliza el responsable convirtiéndolo a mayúsculas

        Ejemplos:
            'Administrador Sistema' → 'ADMINISTRADOR SISTEMA'
            'alex portilla' → 'ALEX PORTILLA'
        """
        responsable_limpio = str(responsable).strip().upper()

        if responsable_limpio != responsable:
            logger.info(f"  ✓ Responsable normalizado: '{responsable}' → '{responsable_limpio}'")

        return responsable_limpio

    def _normalizar_tipo(self, tipo):
        """
        Normaliza el tipo convirtiéndolo a mayúsculas

        Ejemplos:
            'self' → 'SELF'
            'Hybrid' → 'HYBRID'
        """
        tipo_limpio = str(tipo).strip().upper()

        # Mapeo de variaciones comunes
        mapeo_tipos = {
            'HYBRID': 'HYBRID',
            'HIBRIDO': 'HYBRID',
            'HÍBRIDO': 'HYBRID',
            'SELF': 'SELF',
            'SIBBLING': 'SIBBLING',
            'SIBLING': 'SIBBLING',
        }

        tipo_normalizado = mapeo_tipos.get(tipo_limpio, tipo_limpio)

        if tipo_normalizado != tipo:
            logger.info(f"  ✓ Tipo normalizado: '{tipo}' → '{tipo_normalizado}'")

        return tipo_normalizado

    def predecir(self, fechapol, genero, especie, ubicacion, responsable, tipo, cantidad, disponible):
        """
        Realiza predicción usando el modelo XGBoost

        Args:
            fechapol (str): Fecha de polinización 'YYYY-MM-DD'
            genero (str): Género de la planta
            especie (str): Especie
            ubicacion (str): Ubicación física
            responsable (str): Responsable del registro
            tipo (str): Tipo de polinización (SELF, SIBLING, HYBRID)
            cantidad (int): Cantidad de cápsulas
            disponible (int): 0 o 1

        Returns:
            dict: Resultado con dias_estimados, fecha_estimada_maduracion, confianza, etc.
        """
        if not self.model_loaded:
            raise ValueError("Modelo XGBoost no está cargado")

        try:
            logger.info("="*60)
            logger.info("INICIANDO PREDICCIÓN XGBOOST POLINIZACIÓN")
            logger.info("="*60)

            # 1. Convertir fecha
            if isinstance(fechapol, str):
                fecha = datetime.strptime(fechapol, '%Y-%m-%d')
            else:
                fecha = fechapol

            logger.info(f"Datos entrada (originales):")
            logger.info(f"  - Fecha: {fechapol}")
            logger.info(f"  - Género: {genero}")
            logger.info(f"  - Especie: {especie}")
            logger.info(f"  - Ubicación: {ubicacion}")
            logger.info(f"  - Responsable: {responsable}")
            logger.info(f"  - Tipo: {tipo}")
            logger.info(f"  - Cantidad: {cantidad}")
            logger.info(f"  - Disponible: {disponible}")

            # 1.5. NORMALIZAR DATOS DE ENTRADA
            logger.info(f"\nNormalizando datos...")
            especie_normalizada = self._normalizar_especie(especie, genero)
            ubicacion_normalizada = self._normalizar_ubicacion(ubicacion)
            responsable_normalizado = self._normalizar_responsable(responsable)
            tipo_normalizado = self._normalizar_tipo(tipo)

            logger.info(f"\nDatos normalizados:")
            logger.info(f"  - Especie: {especie_normalizada}")
            logger.info(f"  - Ubicación: {ubicacion_normalizada}")
            logger.info(f"  - Responsable: {responsable_normalizado}")
            logger.info(f"  - Tipo: {tipo_normalizado}")

            # 2. Crear DataFrame de entrada (USANDO VALORES NORMALIZADOS)
            df = pd.DataFrame([{
                'fechapol': fecha,
                'genero': str(genero).strip(),
                'especie': especie_normalizada,
                'ubicacion': ubicacion_normalizada,
                'responsable': responsable_normalizado,
                'Tipo': tipo_normalizado,
                'cantidad': int(cantidad) if cantidad is not None else 1,
                'disponible': int(disponible) if disponible is not None else 1
            }])

            # 3. Crear features temporales
            df['mes_pol'] = df['fechapol'].dt.month
            df['dia_año_pol'] = df['fechapol'].dt.dayofyear
            df['trimestre_pol'] = df['fechapol'].dt.quarter
            df['año_pol'] = df['fechapol'].dt.year
            df['semana_año'] = df['fechapol'].dt.isocalendar().week

            # 4. Features cíclicas
            df['mes_sin'] = np.sin(2 * np.pi * df['mes_pol'] / 12)
            df['mes_cos'] = np.cos(2 * np.pi * df['mes_pol'] / 12)
            df['dia_año_sin'] = np.sin(2 * np.pi * df['dia_año_pol'] / 365)
            df['dia_año_cos'] = np.cos(2 * np.pi * df['dia_año_pol'] / 365)

            logger.info(f"Features temporales creadas:")
            logger.info(f"  - mes_pol: {df['mes_pol'].iloc[0]}")
            logger.info(f"  - trimestre_pol: {df['trimestre_pol'].iloc[0]}")
            logger.info(f"  - año_pol: {df['año_pol'].iloc[0]}")

            # 5. Aplicar LabelEncoder a variables categóricas
            categorical_cols = ['genero', 'especie', 'ubicacion', 'responsable', 'Tipo']
            categorias_nuevas = 0

            for col in categorical_cols:
                if col in df.columns and col in self.label_encoders:
                    le = self.label_encoders[col]
                    valor = df[col].iloc[0]

                    # Verificar si es categoría nueva
                    if valor not in le.classes_:
                        logger.warning(f"⚠️  Categoría nueva en '{col}': '{valor}'")
                        logger.warning(f"   → Se usará la primera categoría conocida: '{le.classes_[0]}'")
                        categorias_nuevas += 1
                        # Asignar a la primera categoría conocida
                        valor = le.classes_[0]

                    # Aplicar encoding
                    df[col + '_encoded'] = le.transform([valor])[0]
                    logger.info(f"  - {col}: '{df[col].iloc[0]}' → {df[col + '_encoded'].iloc[0]}")

            # 6. Seleccionar features en orden correcto
            X = df[self.feature_list]

            logger.info(f"\nFeatures preparados: {X.shape[1]} variables")
            logger.info(f"Valores: {X.iloc[0].to_dict()}")

            # 7. Hacer predicción
            dias_predichos = self.model.predict(X)[0]
            dias_predichos = max(1, int(round(dias_predichos)))  # Mínimo 1 día

            logger.info(f"\n✓ Días predichos: {dias_predichos}")

            # 8. Calcular fecha estimada de maduración
            fecha_estimada = fecha + timedelta(days=dias_predichos)

            # 9. Calcular confianza
            # Base: 85% (confianza del modelo R²=95.63%)
            # Penalización: -5% por cada categoría nueva (máximo 5)
            base_confianza = 85
            penalizacion = min(categorias_nuevas * 5, 25)  # Máximo 25% de penalización
            confianza = max(60, base_confianza - penalizacion)

            # Determinar nivel de confianza
            if confianza >= 85:
                nivel_confianza = 'alta'
            elif confianza >= 70:
                nivel_confianza = 'media'
            else:
                nivel_confianza = 'baja'

            logger.info(f"✓ Fecha estimada: {fecha_estimada.strftime('%Y-%m-%d')}")
            logger.info(f"✓ Confianza: {confianza}% ({nivel_confianza})")
            logger.info(f"  - Categorías nuevas: {categorias_nuevas}")
            logger.info("="*60)

            # 10. Verificar si hubo normalizaciones
            datos_normalizados = {}
            if especie != especie_normalizada:
                datos_normalizados['especie'] = {'original': especie, 'normalizada': especie_normalizada}
            if ubicacion != ubicacion_normalizada:
                datos_normalizados['ubicacion'] = {'original': ubicacion, 'normalizada': ubicacion_normalizada}
            if responsable != responsable_normalizado:
                datos_normalizados['responsable'] = {'original': responsable, 'normalizada': responsable_normalizado}
            if tipo != tipo_normalizado:
                datos_normalizados['tipo'] = {'original': tipo, 'normalizada': tipo_normalizado}

            # 11. Retornar resultado
            resultado = {
                'dias_estimados': dias_predichos,
                'fecha_polinizacion': fechapol if isinstance(fechapol, str) else fechapol.strftime('%Y-%m-%d'),
                'fecha_estimada_maduracion': fecha_estimada.strftime('%Y-%m-%d'),
                'confianza': confianza,
                'nivel_confianza': nivel_confianza,
                'metodo': 'XGBoost',
                'modelo': 'polinizacion.joblib',
                'input_data': {
                    'genero': genero,
                    'especie': especie_normalizada,  # Usar normalizada
                    'ubicacion': ubicacion_normalizada,  # Usar normalizada
                    'responsable': responsable_normalizado,  # Usar normalizada
                    'tipo': tipo_normalizado,  # Usar normalizada
                    'cantidad': cantidad,
                    'disponible': disponible
                },
                'features_count': len(self.feature_list),
                'categorias_nuevas': categorias_nuevas,
                'timestamp': datetime.now().isoformat(),
                'metricas_modelo': {
                    'r2': 0.9563,
                    'rmse': 19.43,
                    'mae': 10.22
                }
            }

            # Agregar info de normalizaciones si hubo
            if datos_normalizados:
                resultado['datos_normalizados'] = datos_normalizados
                logger.info(f"\n✓ Datos normalizados automáticamente: {list(datos_normalizados.keys())}")

            return resultado

        except Exception as e:
            logger.error(f"Error en predicción XGBoost: {e}", exc_info=True)
            raise


# Instancia global del predictor
_predictor_instance = None


def get_predictor():
    """Obtiene instancia única del predictor (singleton)"""
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = XGBoostPolinizacionPredictor()
    return _predictor_instance
