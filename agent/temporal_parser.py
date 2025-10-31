# agent/temporal_parser.py - Optimizado
from datetime import datetime, timedelta
import re
from typing import Optional, Tuple, List
from agent.utils import parse_iso_datetime_safe

def parsear_referencia_temporal(texto_referencia: str, fecha_base: Optional[datetime] = None) -> Tuple[Optional[str], str]:
    """Parsea referencias temporales y las convierte a timestamp ISO."""
    if not texto_referencia or not texto_referencia.strip():
        return None, "sin_referencia"
    
    texto = texto_referencia.lower().strip()
    if fecha_base is None:
        fecha_base = datetime.now()
    
    # 1. Fechas exactas: DD/MM/YYYY, YYYY-MM-DD
    patrones_fecha = [
        (r'(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})', False),  # DD/MM/YYYY
        (r'(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})', True),   # YYYY-MM-DD
        (r'(\d{1,2})[\/\-](\d{1,2})', False),              # DD/MM (año actual)
    ]
    
    for patron, es_yyyy_mm_dd in patrones_fecha:
        match = re.search(patron, texto)
        if match:
            try:
                if es_yyyy_mm_dd:
                    año, mes, dia = match.groups()
                else:
                    dia, mes = match.groups()[:2]
                    año = match.groups()[2] if len(match.groups()) > 2 else str(fecha_base.year)
                
                fecha_exacta = datetime(int(año), int(mes), int(dia))
                return fecha_exacta.isoformat(), "fecha_exacta"
            except ValueError:
                continue

    # 2. NUEVO: Fechas con nombres de meses
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
    }
    
    # Patrón: "15 de diciembre", "el 20 de marzo"
    patron_fecha_mes = r'(?:el\s+)?(\d{1,2})\s+de\s+(' + '|'.join(meses.keys()) + r')(?:\s+(?:de\s+)?(\d{4}))?'
    match = re.search(patron_fecha_mes, texto)
    if match:
        dia = int(match.group(1))
        mes_nombre = match.group(2)
        año = int(match.group(3)) if match.group(3) else fecha_base.year
        mes = meses[mes_nombre]
        
        try:
            fecha_exacta = datetime(año, mes, dia)
            return fecha_exacta.isoformat(), "fecha_exacta"
        except ValueError:
            pass
    
    # 3. NUEVO: Días de la semana específicos
    dias_semana = {
        'lunes': 0, 'martes': 1, 'miércoles': 2, 'jueves': 3,
        'viernes': 4, 'sábado': 5, 'domingo': 6
    }
    
    for dia_nombre, dia_numero in dias_semana.items():
        if dia_nombre in texto:
            # Calcular el día más cercano (pasado o futuro)
            dias_diferencia = dia_numero - fecha_base.weekday()
            
            # Si es el mismo día de la semana (hoy)
            if dias_diferencia == 0:
                fecha_resultado = fecha_base
            # Si es un día futuro en esta semana
            elif dias_diferencia > 0:
                fecha_resultado = fecha_base + timedelta(days=dias_diferencia)
            # Si es un día pasado, puede referirse a la semana anterior
            else:
                # Si dice "el lunes pasado", buscar la semana anterior
                if 'pasado' in texto or 'anterior' in texto:
                    fecha_resultado = fecha_base + timedelta(days=dias_diferencia - 7)
                else:
                    # Por defecto, el próximo día con ese nombre
                    fecha_resultado = fecha_base + timedelta(days=dias_diferencia + 7)
            
            return fecha_resultado.isoformat(), "dia_semana"
    
    # Referencias relativas
    referencias_relativas = {
        "hoy": timedelta(days=0),
        "mañana": timedelta(days=1),
        "ayer": timedelta(days=-1),
        # Semanas
        "próxima semana": timedelta(weeks=1),
        "semana próxima": timedelta(weeks=1),
        "semana pasada": timedelta(weeks=-1),
        "la semana pasada": timedelta(weeks=-1),
        "semana anterior": timedelta(weeks=-1),
        "esta semana": timedelta(days=0),  # Manejado especialmente
        # Meses
        "próximo mes": timedelta(days=30),
        "mes próximo": timedelta(days=30),
        "mes pasado": timedelta(days=-30),
        "este mes": timedelta(days=0),  # Manejado especialmente
    }
    
    for referencia, delta in referencias_relativas.items():
        if referencia in texto:
            if referencia in ["esta semana", "este mes"]:
                # Para "esta semana/mes" devolver fecha base
                fecha_resultado = fecha_base
            else:
                fecha_resultado = fecha_base + delta
            return fecha_resultado.isoformat(), "relativa"
    
    # Expresiones numéricas: "en X días", "hace X días"
    patrones_numericos = [
        (r'en\s+(\d+)\s+(día|días|semana|semanas|mes|meses)', 1),
        (r'dentro\s+de\s+(\d+)\s+(día|días|semana|semanas|mes|meses)', 1),
        (r'hace\s+(\d+)\s+(día|días|semana|semanas|mes|meses)', -1),
        (r'(\d+)\s+(día|días|semana|semanas|mes|meses)\s+atrás', -1)
    ]
    
    for patron, signo in patrones_numericos:
        match = re.search(patron, texto)
        if match:
            cantidad = int(match.group(1)) * signo
            unidad = match.group(2)
            
            if unidad in ['día', 'días']:
                delta = timedelta(days=cantidad)
            elif unidad in ['semana', 'semanas']:
                delta = timedelta(weeks=cantidad)
            else:  # mes, meses
                delta = timedelta(days=cantidad * 30)  # Aproximación
            
            fecha_resultado = fecha_base + delta
            return fecha_resultado.isoformat(), "expresion_temporal"
    # 6. NUEVO: Expresiones de rango ("los últimos 7 días", "las próximas 2 semanas")
    patron_rango = r'(?:los?\s+)?(?:últimos?|próximas?)\s+(\d+)\s+(día|días|semana|semanas)'
    match = re.search(patron_rango, texto)
    if match:
        cantidad = int(match.group(1))
        unidad = match.group(2)
        
        if 'último' in texto:
            signo = -1
        else:
            signo = 1
        
        if unidad in ['día', 'días']:
            delta = timedelta(days=cantidad * signo)
        else:  # semana, semanas
            delta = timedelta(weeks=cantidad * signo)
        
        fecha_resultado = fecha_base + delta
        return fecha_resultado.isoformat(), "rango_temporal"
    
    return None, "no_reconocido"

def extraer_referencias_del_texto(texto: str) -> List[Tuple[str, str, str]]:
    """
    Extrae automáticamente referencias temporales del texto usando regex y detección simple.
    Versión unificada que combina ambos enfoques para mayor robustez.
    Returns:
        List[Tuple[str, str, str]]: Lista de tuplas (referencia_original, timestamp, tipo)
    """
    referencias_encontradas = []
    
    # Patrones regex para referencias temporales
    patrones = [
        r'\b(mañana|ayer|hoy)\b',
        r'\b(próxima? semanas?|semanas? próximas?)\b',
        r'\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{4})\b',
        r'\b(en \d+ (?:día|días|semana|semanas))\b',
        r'\b(semana|mes) (pasada|pasado|anterior)\b',
        r'\b(este|esta) (semana|mes)\b',
        r'\b(lunes|martes|miércoles|jueves|viernes|sábado|domingo)(?:\s+(?:pasado|próximo))?\b',
        r'\b(?:el\s+)?\d{1,2}\s+de\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+(?:de\s+)?\d{4})?\b',
        r'\bhace\s+\d+\s+(?:día|días|semana|semanas|mes|meses)\b',
        r'\b(?:los?\s+)?(?:últimos?|próximas?)\s+\d+\s+(?:día|días|semana|semanas)\b',
        r'\b\d{1,2}[\/\-]\d{1,2}\b',  # DD/MM sin año
    ]
    
    # 1. Extraer referencias usando patrones regex
    for patron in patrones:
        for match in re.finditer(patron, texto.lower()):
            referencia = match.group()
            timestamp, tipo = parsear_referencia_temporal(referencia)
            if timestamp:
                referencias_encontradas.append((referencia, timestamp, tipo))
    
    # 2. Detectar palabras temporales simples adicionales
    palabras_temporales = detectar_palabras_temporales_simples(texto)
    
    # 3. Convertir palabras simples a referencias (evitando duplicados)
    referencias_ya_encontradas = {ref[0].lower() for ref in referencias_encontradas}
    
    for palabra in palabras_temporales:
        if palabra.lower() not in referencias_ya_encontradas:
            timestamp, tipo = parsear_referencia_temporal(palabra)
            if timestamp:
                referencias_encontradas.append((palabra, timestamp, tipo))
                referencias_ya_encontradas.add(palabra.lower())  # Actualizar conjunto para evitar duplicados futuros
    
    return referencias_encontradas

# NUEVA FUNCIÓN: Detectar referencias temporales específicas en fragmentos
def detectar_timestamps_fragmento(texto_fragmento: str, timestamp_base_conversacion: str) -> Optional[str]:
    """
    Detecta si un fragmento específico tiene referencias temporales propias
    que deberían sobrescribir el timestamp de la conversación.
    """
    referencias = extraer_referencias_del_texto(texto_fragmento)
    
    if not referencias:
        return timestamp_base_conversacion
    
    # Usar la fecha base de la conversación para resolver referencias relativas
    if timestamp_base_conversacion:
        try:
            fecha_base = parse_iso_datetime_safe(timestamp_base_conversacion)
            if fecha_base:
                for ref_texto, timestamp, tipo in referencias:
                    # Si encontramos una referencia temporal específica, usarla
                    if tipo in ['fecha_exacta', 'dia_semana']:
                        return timestamp
                    elif tipo in ['relativa', 'expresion_temporal']:
                        # Para referencias relativas, resolver desde la fecha base
                        timestamp_resuelto, _ = parsear_referencia_temporal(ref_texto, fecha_base)
                        if timestamp_resuelto:
                            return timestamp_resuelto
        except Exception:
            pass
    
    # Si no se puede resolver, mantener el timestamp base
    return timestamp_base_conversacion

def detectar_palabras_temporales_simples(texto: str) -> List[str]:
    """
    Detecta palabras temporales simples independientemente del contexto gramatical.
    Esta función es más permisiva que los patrones regex complejos.
    """
    texto_normalizado = texto.lower()
    
    # Remover signos de puntuación para detección más robusta
    texto_limpio = re.sub(r'[¿?¡!.,;:]', ' ', texto_normalizado)
    texto_limpio = re.sub(r'\s+', ' ', texto_limpio).strip()
    
    palabras_temporales_encontradas = []
    
    # Palabras temporales básicas
    temporales_basicas = [
        'ayer', 'hoy', 'mañana', 'manana',
        'lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo',
        'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
        'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
        'semana', 'mes', 'año', 'dia'
    ]
    
    # Frases temporales
    frases_temporales = [
        'la semana pasada', 'el mes pasado', 'el año pasado',
        'esta semana', 'este mes', 'este año',
        'la proxima semana', 'el proximo mes'
    ]
    
    # Buscar frases primero (más específicas)
    for frase in frases_temporales:
        if frase in texto_limpio:
            palabras_temporales_encontradas.append(frase)
    
    # Buscar palabras individuales
    palabras = texto_limpio.split()
    for palabra in palabras:
        if palabra in temporales_basicas:
            if palabra not in ' '.join(palabras_temporales_encontradas):  # Evitar duplicados
                palabras_temporales_encontradas.append(palabra)
    
    return palabras_temporales_encontradas