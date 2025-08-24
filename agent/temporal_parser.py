# agent/temporal_parser.py - Optimizado
from datetime import datetime, timedelta
import re
from typing import Optional, Tuple, List

def parsear_referencia_temporal(texto_referencia: str, fecha_base: Optional[datetime] = None) -> Tuple[Optional[str], str]:
    """Parsea referencias temporales y las convierte a timestamp ISO."""
    if not texto_referencia or not texto_referencia.strip():
        return None, "sin_referencia"
    
    texto = texto_referencia.lower().strip()
    if fecha_base is None:
        fecha_base = datetime.now()
    
    # Fechas exactas: DD/MM/YYYY, YYYY-MM-DD
    patrones_fecha = [
        (r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', False),  # DD/MM/YYYY
        (r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})', True),   # YYYY-MM-DD
    ]
    
    for patron, es_yyyy_mm_dd in patrones_fecha:
        match = re.search(patron, texto)
        if match:
            try:
                if es_yyyy_mm_dd:
                    año, mes, dia = match.groups()
                else:
                    dia, mes, año = match.groups()
                fecha_exacta = datetime(int(año), int(mes), int(dia))
                return fecha_exacta.isoformat(), "fecha_exacta"
            except ValueError:
                continue
    
    # Referencias relativas
    referencias_relativas = {
        "hoy": timedelta(days=0),
        "mañana": timedelta(days=1),
        "ayer": timedelta(days=-1),
        "próxima semana": timedelta(weeks=1),
        "semana próxima": timedelta(weeks=1),
        "semana pasada": timedelta(weeks=-1),
        "próximo mes": timedelta(days=30),
        "mes próximo": timedelta(days=30),
        "mes pasado": timedelta(days=-30),
    }
    
    for referencia, delta in referencias_relativas.items():
        if referencia in texto:
            fecha_resultado = fecha_base + delta
            return fecha_resultado.isoformat(), "relativa"
    
    # Expresiones numéricas: "en X días", "hace X días"
    patrones_numericos = [
        (r'en\s+(\d+)\s+(día|días|semana|semanas)', 1),
        (r'dentro\s+de\s+(\d+)\s+(día|días|semana|semanas)', 1),
        (r'hace\s+(\d+)\s+(día|días|semana|semanas)', -1)
    ]
    
    for patron, signo in patrones_numericos:
        match = re.search(patron, texto)
        if match:
            cantidad = int(match.group(1)) * signo
            unidad = match.group(2)
            
            if unidad in ['día', 'días']:
                delta = timedelta(days=cantidad)
            else:  # semana, semanas
                delta = timedelta(weeks=cantidad)
            
            fecha_resultado = fecha_base + delta
            return fecha_resultado.isoformat(), "expresion_temporal"
    
    return None, "no_reconocido"

def extraer_referencias_del_texto(texto: str) -> List[Tuple[str, str, str]]:
    """Extrae automáticamente referencias temporales del texto."""
    referencias_encontradas = []
    
    patrones = [
        r'\b(mañana|ayer|hoy)\b',
        r'\b(próxima? semanas?|semanas? próximas?)\b',
        r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
        r'\b(en \d+ (?:día|días|semana|semanas))\b'
    ]
    
    for patron in patrones:
        for match in re.finditer(patron, texto.lower()):
            referencia = match.group()
            timestamp, tipo = parsear_referencia_temporal(referencia)
            if timestamp:
                referencias_encontradas.append((referencia, timestamp, tipo))
    
    return referencias_encontradas