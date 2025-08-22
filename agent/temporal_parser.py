# agent/temporal_parser.py 
from datetime import datetime, timedelta
import re
from typing import Optional, Tuple

def parsear_referencia_temporal(texto_referencia: str, fecha_base: Optional[datetime] = None) -> Tuple[Optional[str], str]:
    """
    Parsea referencias temporales explícitas y las convierte a ISO timestamp.
    
    Args:
        texto_referencia: "mañana", "25/01/2025", "próxima semana", etc.
        fecha_base: fecha de referencia (por defecto datetime.now())
    
    Returns:
        (timestamp_iso, tipo_referencia)
        - timestamp_iso: fecha en formato ISO o None si no se puede parsear
        - tipo_referencia: "fecha_exacta", "relativa", "expresion_temporal"
    """
    if not texto_referencia or not texto_referencia.strip():
        return None, "sin_referencia"
    
    texto = texto_referencia.lower().strip()
    if fecha_base is None:
        fecha_base = datetime.now()
    
    # ===== 1. FECHAS EXACTAS =====
    # Formatos: DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD
    patrones_fecha = [
        r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})',  # DD/MM/YYYY o DD-MM-YYYY
        r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})',  # YYYY/MM/DD o YYYY-MM-DD
    ]
    
    for patron in patrones_fecha:
        match = re.search(patron, texto)
        if match:
            try:
                if len(match.group(1)) == 4:  # YYYY-MM-DD
                    año, mes, dia = match.groups()
                else:  # DD/MM/YYYY
                    dia, mes, año = match.groups()
                
                fecha_exacta = datetime(int(año), int(mes), int(dia))
                return fecha_exacta.isoformat(), "fecha_exacta"
            except ValueError:
                continue
    
    # ===== 2. REFERENCIAS RELATIVAS =====
    referencias_relativas = {
        # Días específicos
        "hoy": timedelta(days=0),
        "mañana": timedelta(days=1),
        "pasado mañana": timedelta(days=2),
        "ayer": timedelta(days=-1),
        "anteayer": timedelta(days=-2),
        
        # Semanas
        "próxima semana": timedelta(weeks=1),
        "la próxima semana": timedelta(weeks=1),
        "semana próxima": timedelta(weeks=1),
        "semana que viene": timedelta(weeks=1),
        "semana pasada": timedelta(weeks=-1),
        "la semana pasada": timedelta(weeks=-1),
        
        # Meses (aproximado)
        "próximo mes": timedelta(days=30),
        "mes próximo": timedelta(days=30),
        "mes que viene": timedelta(days=30),
        "mes pasado": timedelta(days=-30),
        "el mes pasado": timedelta(days=-30),
    }
    
    for referencia, delta in referencias_relativas.items():
        if referencia in texto:
            fecha_resultado = fecha_base + delta
            return fecha_resultado.isoformat(), "relativa"
    
    # ===== 3. EXPRESIONES TEMPORALES COMPLEJAS =====
    # "en 3 días", "dentro de 2 semanas", "hace 1 mes"
    
    # Patrón: "en X días/semanas/meses"
    patron_en = r'en\s+(\d+)\s+(día|días|semana|semanas|mes|meses)'
    match = re.search(patron_en, texto)
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        
        if unidad in ['día', 'días']:
            delta = timedelta(days=cantidad)
        elif unidad in ['semana', 'semanas']:
            delta = timedelta(weeks=cantidad)
        elif unidad in ['mes', 'meses']:
            delta = timedelta(days=cantidad * 30)  # Aproximación
        
        fecha_resultado = fecha_base + delta
        return fecha_resultado.isoformat(), "expresion_temporal"
    
    # Patrón: "dentro de X días/semanas/meses"
    patron_dentro = r'dentro\s+de\s+(\d+)\s+(día|días|semana|semanas|mes|meses)'
    match = re.search(patron_dentro, texto)
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        
        if unidad in ['día', 'días']:
            delta = timedelta(days=cantidad)
        elif unidad in ['semana', 'semanas']:
            delta = timedelta(weeks=cantidad)
        elif unidad in ['mes', 'meses']:
            delta = timedelta(days=cantidad * 30)
        
        fecha_resultado = fecha_base + delta
        return fecha_resultado.isoformat(), "expresion_temporal"
    
    # Patrón: "hace X días/semanas/meses"
    patron_hace = r'hace\s+(\d+)\s+(día|días|semana|semanas|mes|meses)'
    match = re.search(patron_hace, texto)
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        
        if unidad in ['día', 'días']:
            delta = timedelta(days=-cantidad)
        elif unidad in ['semana', 'semanas']:
            delta = timedelta(weeks=-cantidad)
        elif unidad in ['mes', 'meses']:
            delta = timedelta(days=-cantidad * 30)
        
        fecha_resultado = fecha_base + delta
        return fecha_resultado.isoformat(), "expresion_temporal"
    
    # ===== 4. NO SE PUDO PARSEAR =====
    return None, "no_reconocido"


def extraer_referencias_del_texto(texto: str) -> list:
    """
    Extrae automáticamente referencias temporales del texto completo.
    Útil para detectar referencias sin que el usuario las especifique explícitamente.
    
    Returns:
        Lista de tuplas (referencia_encontrada, timestamp_iso, tipo)
    """
    referencias_encontradas = []
    
    # Palabras y patrones temporales comunes
    patrones_busqueda = [
        r'\b(mañana|ayer|hoy|pasado mañana|anteayer)\b',
        r'\b(próxima? semanas?|semanas? (?:que viene|próximas?))\b',
        r'\b(próximo? mes|mes (?:que viene|próximo))\b',
        r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
        r'\b(en \d+ (?:día|días|semana|semanas))\b',
        r'\b(dentro de \d+ (?:día|días|semana|semanas))\b',
        r'\b(hace \d+ (?:día|días|semana|semanas))\b'
    ]
    
    for patron in patrones_busqueda:
        matches = re.finditer(patron, texto.lower())
        for match in matches:
            referencia = match.group()
            timestamp, tipo = parsear_referencia_temporal(referencia)
            if timestamp:
                referencias_encontradas.append((referencia, timestamp, tipo))
    
    return referencias_encontradas


# ===== FUNCIONES DE TESTING =====
def test_parser_temporal():
    """Función de prueba para verificar el parser"""
    casos_test = [
        "mañana",
        "25/01/2025", 
        "próxima semana",
        "en 3 días",
        "dentro de 2 semanas",
        "hace 1 mes",
        "hoy",
        "ayer",
        "2025-12-25",
        "texto sin fecha",
        "tengo reunión mañana por la tarde"
    ]
    
    print("🧪 Testing Parser Temporal:")
    print("=" * 50)
    
    for caso in casos_test:
        timestamp, tipo = parsear_referencia_temporal(caso)
        if timestamp:
            fecha_legible = datetime.fromisoformat(timestamp).strftime("%d/%m/%Y %H:%M")
            print(f"✅ '{caso}' → {fecha_legible} (tipo: {tipo})")
        else:
            print(f"❌ '{caso}' → No reconocido (tipo: {tipo})")
    
    print("\n🔍 Testing extracción automática:")
    texto_ejemplo = "Tengo reunión mañana y el 15/02/2025 hay presentación. En 3 días reviso el proyecto."
    referencias = extraer_referencias_del_texto(texto_ejemplo)
    for ref, timestamp, tipo in referencias:
        fecha_legible = datetime.fromisoformat(timestamp).strftime("%d/%m/%Y")
        print(f"📅 Encontrado: '{ref}' → {fecha_legible} ({tipo})")


if __name__ == "__main__":
    test_parser_temporal()