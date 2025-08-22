# agent/query_analyzer.py 
from datetime import datetime, timedelta
from typing import Tuple, Optional, Dict, List
from agent.temporal_parser import parsear_referencia_temporal, extraer_referencias_del_texto
import re

class IntentionTemporalDetector:
    """Detecta la intención temporal en consultas/preguntas del usuario"""
    
    # Patrones que indican intención temporal fuerte
    PATRONES_TEMPORALES_FUERTES = [
        # Preguntas directas sobre tiempo
        r'\b(qué|que) .*(tengo|hay|pasa|ocurre|sucede) (hoy|mañana|ayer|pasado mañana)\b',
        r'\b(cuándo|cuando) .*(es|será|fue|ocurre|pasa)\b',
        r'\b(qué|que) .*(agenda|calendario|programado|planificado)\b',
        r'\b(próximo|próxima|siguiente|este|esta) .*(semana|mes|día|lunes|martes|miércoles|jueves|viernes|sábado|domingo)\b',
        r'\b(el|la) .*(semana|mes) (pasado|pasada|anterior|que viene|próximo|próxima)\b',
        r'\bpara (mañana|hoy|el|la|este|esta)\b',
        r'\ben (enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\b',
        
        # Fechas explícitas
        r'\b\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4}\b',
        r'\b\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2}\b',
    ]
    
    # Palabras que sugieren intención temporal media
    PALABRAS_TEMPORALES_MEDIAS = [
        'reciente', 'recientemente', 'últimamente', 'actual', 'actualmente',
        'vigente', 'vigentes', 'pendiente', 'pendientes', 'próximo', 'próximos',
        'futuro', 'pasado', 'anterior', 'después', 'antes', 'durante', 'mientras',
        'ahora', 'ya', 'todavía', 'aún', 'temprano', 'tarde', 'pronto'
    ]
    
    # Patrones que indican búsqueda estructural/semántica (no temporal)
    PATRONES_NO_TEMPORALES = [
        r'\b(cómo|como) .*(funciona|hacer|crear|implementar)\b',
        r'\b(qué|que) .*(significa|define|concepto|definición)\b',
        r'\b(cuál|cual|cuáles|cuales) .*(diferencia|ventaja|característica)\b',
        r'\b(dónde|donde) .*(encuentra|ubicado|está)\b',
        r'\b(por qué|porque|razón|motivo)\b',
        r'\b(explicar|explicación|detalles|información|datos)\b',
        r'\b(comparar|comparación|versus|vs|contra)\b',
        r'\b(procedimiento|proceso|método|metodología|pasos)\b',
        r'\b(tipos|categorías|clasificación|ejemplos)\b'
    ]
    
    def analizar_intencion(self, pregunta: str) -> Dict:
        """
        Analiza la intención temporal de una pregunta
        
        Returns:
            {
                'intencion_temporal': 'fuerte' | 'media' | 'debil' | 'nula',
                'confianza': float (0.0-1.0),
                'referencia_temporal_detectada': str | None,
                'timestamp_referencia': str | None,
                'factor_refuerzo_temporal': float (multiplicador para pesos temporales),
                'explicacion': str
            }
        """
        pregunta_lower = pregunta.lower().strip()
        
        # 1. DETECTAR PATRONES TEMPORALES FUERTES
        for patron in self.PATRONES_TEMPORALES_FUERTES:
            if re.search(patron, pregunta_lower):
                return self._analizar_intencion_fuerte(pregunta, pregunta_lower, patron)
        
        # 2. DETECTAR REFERENCIAS TEMPORALES EXPLÍCITAS
        referencias_encontradas = extraer_referencias_del_texto(pregunta)
        if referencias_encontradas:
            return self._analizar_referencias_encontradas(pregunta, referencias_encontradas)
        
        # 3. DETECTAR PALABRAS TEMPORALES MEDIAS
        palabras_temporales_encontradas = [
            palabra for palabra in self.PALABRAS_TEMPORALES_MEDIAS 
            if palabra in pregunta_lower
        ]
        
        if palabras_temporales_encontradas:
            return self._analizar_intencion_media(pregunta, palabras_temporales_encontradas)
        
        # 4. DETECTAR PATRONES NO TEMPORALES (ESTRUCTURALES)
        for patron in self.PATRONES_NO_TEMPORALES:
            if re.search(patron, pregunta_lower):
                return self._analizar_intencion_nula(pregunta, patron)
        
        # 5. INTENCIÓN DÉBIL (por defecto)
        return {
            'intencion_temporal': 'debil',
            'confianza': 0.3,
            'referencia_temporal_detectada': None,
            'timestamp_referencia': datetime.now().isoformat(),
            'factor_refuerzo_temporal': 1.0,  # Peso normal
            'explicacion': 'Sin indicadores temporales claros, usando contexto presente'
        }
    
    def _analizar_intencion_fuerte(self, pregunta: str, pregunta_lower: str, patron_encontrado: str) -> Dict:
        """Analiza intención temporal fuerte"""
        # Intentar extraer referencia temporal específica
        referencias = extraer_referencias_del_texto(pregunta)
        
        if referencias:
            ref_texto, timestamp, tipo = referencias[0]
            referencia_temporal = ref_texto
            timestamp_referencia = timestamp
        else:
            # Usar timestamp actual pero con referencia detectada por patrón
            referencia_temporal = self._extraer_referencia_del_patron(pregunta_lower)
            timestamp_referencia = datetime.now().isoformat()
        
        return {
            'intencion_temporal': 'fuerte',
            'confianza': 0.9,
            'referencia_temporal_detectada': referencia_temporal,
            'timestamp_referencia': timestamp_referencia,
            'factor_refuerzo_temporal': 2.5,  # Refuerzo muy alto
            'explicacion': f'Patrón temporal fuerte detectado: {patron_encontrado}'
        }
    
    def _analizar_referencias_encontradas(self, pregunta: str, referencias: List) -> Dict:
        """Analiza cuando se encontraron referencias temporales explícitas"""
        ref_texto, timestamp, tipo = referencias[0]
        
        return {
            'intencion_temporal': 'fuerte',
            'confianza': 0.95,
            'referencia_temporal_detectada': ref_texto,
            'timestamp_referencia': timestamp,
            'factor_refuerzo_temporal': 2.0,  # Refuerzo alto
            'explicacion': f'Referencia temporal explícita: "{ref_texto}" ({tipo})'
        }
    
    def _analizar_intencion_media(self, pregunta: str, palabras_encontradas: List[str]) -> Dict:
        """Analiza intención temporal media"""
        return {
            'intencion_temporal': 'media',
            'confianza': 0.6,
            'referencia_temporal_detectada': ', '.join(palabras_encontradas),
            'timestamp_referencia': datetime.now().isoformat(),
            'factor_refuerzo_temporal': 1.5,  # Refuerzo moderado
            'explicacion': f'Palabras con contexto temporal: {", ".join(palabras_encontradas)}'
        }
    
    def _analizar_intencion_nula(self, pregunta: str, patron_encontrado: str) -> Dict:
        """Analiza cuando la intención es claramente no temporal"""
        return {
            'intencion_temporal': 'nula',
            'confianza': 0.8,
            'referencia_temporal_detectada': None,
            'timestamp_referencia': None,
            'factor_refuerzo_temporal': 0.2,  # Reduce drasticamente peso temporal
            'explicacion': f'Consulta estructural/semántica: {patron_encontrado}'
        }
    
    def _extraer_referencia_del_patron(self, pregunta_lower: str) -> str:
        """Extrae referencia temporal básica de patrones comunes"""
        if 'mañana' in pregunta_lower:
            return 'mañana'
        elif 'hoy' in pregunta_lower:
            return 'hoy'
        elif 'ayer' in pregunta_lower:
            return 'ayer'
        elif 'próxima semana' in pregunta_lower or 'semana próxima' in pregunta_lower:
            return 'próxima semana'
        elif 'próximo mes' in pregunta_lower or 'mes próximo' in pregunta_lower:
            return 'próximo mes'
        else:
            return 'contexto temporal detectado'


# Función helper para usar fácilmente
detector_intencion = IntentionTemporalDetector()

def analizar_intencion_temporal(pregunta: str) -> Dict:
    """Función helper para usar el detector"""
    return detector_intencion.analizar_intencion(pregunta)


# ===== FUNCIONES DE TESTING =====
def test_detector_intencion():
    """Función de prueba para el detector de intención"""
    casos_test = [
        # Intención temporal fuerte
        "¿Qué tengo mañana?",
        "¿Qué hay programado para el 25/01/2025?",
        "¿Cuándo es la próxima reunión?",
        "¿Qué pasa la próxima semana?",
        
        # Intención temporal media
        "¿Qué proyectos están pendientes?",
        "¿Hay algo reciente sobre el cliente X?",
        "¿Cuáles son los temas actuales?",
        
        # Intención temporal débil
        "¿Cómo está el proyecto?",
        "¿Qué información tienes sobre marketing?",
        
        # Intención no temporal (estructural)
        "¿Cómo funciona el sistema de pagos?",
        "¿Cuál es la diferencia entre A y B?",
        "¿Dónde está ubicada la oficina?",
        "¿Por qué usamos esta metodología?",
    ]
    
    print("🧪 Testing Detector de Intención Temporal:")
    print("=" * 60)
    
    for pregunta in casos_test:
        resultado = analizar_intencion_temporal(pregunta)
        intencion = resultado['intencion_temporal']
        confianza = resultado['confianza']
        factor = resultado['factor_refuerzo_temporal']
        
        # Emoji según intención
        emoji_intencion = {
            'fuerte': '🔴',
            'media': '🟡', 
            'debil': '🟢',
            'nula': '⚫'
        }.get(intencion, '❓')
        
        print(f"{emoji_intencion} '{pregunta}'")
        print(f"   → {intencion.upper()} (confianza: {confianza:.1f}, factor: {factor:.1f}x)")
        print(f"   → {resultado['explicacion']}")
        if resultado['referencia_temporal_detectada']:
            print(f"   → Referencia: {resultado['referencia_temporal_detectada']}")
        print()


if __name__ == "__main__":
    test_detector_intencion()