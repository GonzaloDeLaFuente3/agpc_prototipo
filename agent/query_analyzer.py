# agent/query_analyzer.py - Optimizado
from datetime import datetime
from typing import Dict
from agent.temporal_parser import extraer_referencias_del_texto
import re

class IntentionTemporalDetector:
    """Detecta la intención temporal en consultas del usuario."""
    
    PATRONES_TEMPORALES = [
        r'\b(qué|que) .*(tengo|hay|pasa) (hoy|mañana|ayer)\b',
        r'\b(cuándo|cuando) .*(es|será|fue)\b',
        r'\b(próximo|próxima) .*(semana|mes|día)\b',
        r'\bpara (mañana|hoy)\b',
        r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}\b',
    ]
    
    PALABRAS_TEMPORALES = [
        'reciente', 'actual', 'pendiente', 'próximo', 'futuro', 
        'pasado', 'ahora', 'hoy', 'mañana', 'ayer'
    ]
    
    PATRONES_ESTRUCTURALES = [
        r'\b(cómo|como) .*(funciona|hacer)\b',
        r'\b(qué|que) .*(significa|concepto)\b',
        r'\b(cuál|cual) .*(diferencia|ventaja)\b',
        r'\b(dónde|donde) .*(encuentra|está)\b',
    ]
    
    def analizar_intencion(self, pregunta: str) -> Dict:
        """Analiza la intención temporal de una pregunta."""
        pregunta_lower = pregunta.lower().strip()
        
        # Temporal fuerte: patrones explícitos o referencias encontradas
        for patron in self.PATRONES_TEMPORALES:
            if re.search(patron, pregunta_lower):
                return self._crear_respuesta('fuerte', 0.9, 2.5, 
                    f'Patrón temporal detectado')
        
        referencias = extraer_referencias_del_texto(pregunta)
        if referencias:
            ref_texto, timestamp, tipo = referencias[0]
            return self._crear_respuesta('fuerte', 0.95, 2.0, 
                f'Referencia temporal: "{ref_texto}"', timestamp)
        
        # Temporal medio: palabras relacionadas
        palabras_encontradas = [p for p in self.PALABRAS_TEMPORALES if p in pregunta_lower]
        if palabras_encontradas:
            return self._crear_respuesta('media', 0.6, 1.5, 
                f'Palabras temporales: {", ".join(palabras_encontradas)}')
        
        # Estructural: patrones no temporales
        for patron in self.PATRONES_ESTRUCTURALES:
            if re.search(patron, pregunta_lower):
                return self._crear_respuesta('nula', 0.8, 0.2, 
                    'Consulta estructural detectada')
        
        # Default: débil
        return self._crear_respuesta('debil', 0.3, 1.0, 
            'Sin indicadores temporales claros')
    
    def _crear_respuesta(self, intencion, confianza, factor, explicacion, timestamp=None):
        """Helper para crear respuesta consistente."""
        return {
            'intencion_temporal': intencion,
            'confianza': confianza,
            'factor_refuerzo_temporal': factor,
            'timestamp_referencia': timestamp or datetime.now().isoformat(),
            'explicacion': explicacion
        }

# Instancia global
detector = IntentionTemporalDetector()

def analizar_intencion_temporal(pregunta: str) -> Dict:
    """Función principal para analizar intención temporal."""
    return detector.analizar_intencion(pregunta)