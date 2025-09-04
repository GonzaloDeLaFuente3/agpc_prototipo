# agent/query_analyzer.py 
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from agent.temporal_parser import extraer_referencias_del_texto, parsear_referencia_temporal
import re

class IntentionTemporalDetector:
    """Detecta la intención temporal en consultas del usuario con contexto de momento."""
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
    
    def _resolver_referencias_contextuales(self, pregunta: str, momento_consulta: datetime) -> Optional[str]:
        """Resuelve referencias temporales relativas al momento de la consulta."""
        referencias = extraer_referencias_del_texto(pregunta)
        
        if not referencias:
            return None
        
        # Tomar la primera referencia encontrada
        ref_texto, timestamp_base, tipo = referencias[0]
        
        # Si ya es una fecha absoluta, la devolvemos
        if tipo == "fecha_exacta":
            return timestamp_base
        
        # Para referencias relativas, recalcular desde momento_consulta
        timestamp_contextual, _ = parsear_referencia_temporal(ref_texto, momento_consulta)
        
        return timestamp_contextual
    
    def _calcular_ventana_temporal(self, intencion: str, referencia_temporal: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
        """Calcula ventana temporal de búsqueda según intención y referencia."""
        if not referencia_temporal:
            return None, None
        
        try:
            fecha_ref = datetime.fromisoformat(referencia_temporal)
        except (ValueError, TypeError):
            return None, None
        
        # Ventanas según intensidad de intención temporal
        if intencion == 'fuerte':
            # Búsqueda precisa: ±1 día
            inicio = (fecha_ref - timedelta(days=1)).isoformat()
            fin = (fecha_ref + timedelta(days=1)).isoformat()
        elif intencion == 'media':
            # Búsqueda amplia: ±3 días
            inicio = (fecha_ref - timedelta(days=3)).isoformat()
            fin = (fecha_ref + timedelta(days=3)).isoformat()
        else:
            # Sin ventana específica
            return None, None
        
        return inicio, fin
    
    def analizar_intencion(self, pregunta: str, momento_consulta: Optional[datetime] = None) -> Dict:
        """Analiza la intención temporal considerando el momento de consulta."""
        if momento_consulta is None:
            momento_consulta = datetime.now()
        
        pregunta_lower = pregunta.lower().strip()
        
        # 1. Resolver referencia temporal contextual
        referencia_contextual = self._resolver_referencias_contextuales(pregunta, momento_consulta)
        
        # 2. Temporal fuerte: patrones explícitos
        for patron in self.PATRONES_TEMPORALES:
            if re.search(patron, pregunta_lower):
                ventana_inicio, ventana_fin = self._calcular_ventana_temporal('fuerte', referencia_contextual)
                return self._crear_respuesta(
                    'fuerte', 0.9, 2.5, 
                    f'Patrón temporal detectado | Momento consulta: {momento_consulta.strftime("%d/%m %H:%M")}',
                    referencia_contextual,
                    momento_consulta.isoformat(),
                    ventana_inicio,
                    ventana_fin
                )
        
        # 3. Referencias encontradas
        if referencia_contextual:
            ventana_inicio, ventana_fin = self._calcular_ventana_temporal('fuerte', referencia_contextual)
            return self._crear_respuesta(
                'fuerte', 0.95, 2.0, 
                f'Referencia temporal contextual | Consultado: {momento_consulta.strftime("%d/%m %H:%M")}',
                referencia_contextual,
                momento_consulta.isoformat(),
                ventana_inicio,
                ventana_fin
            )
        
        # 4. Temporal medio: palabras relacionadas
        palabras_encontradas = [p for p in self.PALABRAS_TEMPORALES if p in pregunta_lower]
        if palabras_encontradas:
            return self._crear_respuesta(
                'media', 0.6, 1.5, 
                f'Palabras temporales: {", ".join(palabras_encontradas)} | Contexto: {momento_consulta.strftime("%d/%m %H:%M")}',
                momento_consulta.isoformat(),
                momento_consulta.isoformat()
            )
        
        # 5. Estructural: patrones no temporales
        for patron in self.PATRONES_ESTRUCTURALES:
            if re.search(patron, pregunta_lower):
                return self._crear_respuesta(
                    'nula', 0.8, 0.2, 
                    'Consulta estructural detectada',
                    None,
                    momento_consulta.isoformat()
                )
        
        # 6. Default: débil
        return self._crear_respuesta(
            'debil', 0.3, 1.0, 
            'Sin indicadores temporales claros',
            None,
            momento_consulta.isoformat()
        )
    
    def _crear_respuesta(self, intencion, confianza, factor, explicacion, 
                        timestamp=None, momento_consulta=None, 
                        ventana_inicio=None, ventana_fin=None):
        """Helper para crear respuesta consistente con contexto temporal."""
        respuesta = {
            'intencion_temporal': intencion,
            'confianza': confianza,
            'factor_refuerzo_temporal': factor,
            'timestamp_referencia': timestamp,
            'momento_consulta': momento_consulta or datetime.now().isoformat(),
            'explicacion': explicacion
        }
        
        # Agregar ventana temporal si existe
        if ventana_inicio and ventana_fin:
            respuesta['ventana_temporal'] = {
                'inicio': ventana_inicio,
                'fin': ventana_fin
            }
        
        return respuesta

# Instancia global
detector = IntentionTemporalDetector()

def analizar_intencion_temporal(pregunta: str, momento_consulta: Optional[datetime] = None) -> Dict:
    """Función principal para analizar intención temporal con contexto."""
    return detector.analizar_intencion(pregunta, momento_consulta)