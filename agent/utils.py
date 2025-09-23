# agent/utils.py - VERSIÓN COMPLETA CORREGIDA
from datetime import datetime, timezone
from typing import Optional
import re

def parse_iso_datetime_safe(iso_string) -> Optional[datetime]:
    """
    Parsea fechas ISO de forma segura, manejando diferentes formatos.
    CORREGIDO: Maneja correctamente timestamps con 'Z' UTC y microsegundos
    IMPORTANTE: Siempre devuelve datetime SIN timezone para evitar problemas de comparación
    """
    if not iso_string:
        return None
    
    try:
        iso_string = str(iso_string).strip()
        
        # PASO 1: Si termina en 'Z', convertir a formato UTC estándar
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1]
            print(f"🔧 Removiendo Z de timestamp: {iso_string}")
        
        # PASO 2: Remover microsegundos (.000 o .123456)
        iso_string = re.sub(r'\.\d+', '', iso_string)
        
        # PASO 3: Remover timezone si existe para normalizar
        iso_string = re.sub(r'[+-]\d{2}:\d{2}$', '', iso_string)
        
        # PASO 4: Parsear con fromisoformat
        resultado = datetime.fromisoformat(iso_string)
        print(f"✅ Timestamp parseado correctamente (naive): {resultado}")
        return resultado
        
    except (ValueError, TypeError) as e:
        print(f"⚠️ Error parseando fecha '{iso_string}': {e}")
        
        # FALLBACK: Intentar formatos alternativos comunes
        formatos_alternativos = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%d/%m/%Y %H:%M:%S',
            '%d/%m/%Y'
        ]
        
        for formato in formatos_alternativos:
            try:
                resultado = datetime.strptime(str(iso_string), formato)
                print(f"✅ Timestamp parseado con formato alternativo {formato}: {resultado}")
                return resultado
            except:
                continue
        
        print(f"❌ No se pudo parsear timestamp: {iso_string}")
        return None