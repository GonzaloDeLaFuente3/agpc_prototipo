# agent/fragmentador.py
import uuid
import re
from datetime import datetime
from typing import List, Dict, Tuple
from agent.extractor import extraer_palabras_clave

def criterio_fragmentacion_semantica(texto: str, max_palabras: int = 150) -> List[str]:
    """
    Fragmenta una conversación en bloques semánticamente coherentes.
    
    Criterios de fragmentación:
    1. Cambios de hablante (si se detectan patrones como "Juan:", "- María:")
    2. Párrafos largos (más de max_palabras)
    3. Cambios de tema (detección básica por puntos/cambios abruptos)
    4. Separadores explícitos (líneas con "---", "***", etc.)
    """
    if not texto or not texto.strip():
        return []
    
    # Normalizar texto
    texto = texto.strip()
    
    # 1. Dividir por separadores explícitos primero
    separadores_explicitos = re.split(r'\n[-*=]{3,}\n|\n\s*[-*=]{3,}\s*\n', texto)
    
    fragmentos_finales = []
    
    for bloque in separadores_explicitos:
        bloque = bloque.strip()
        if not bloque:
            continue
            
        # 2. Detectar cambios de hablante
        # Patrones: "Nombre:", "- Nombre:", "[Timestamp] Nombre:"
        patron_hablante = r'^(\s*-?\s*[A-ZÁÉÍÓÚ][a-záéíóúñ\s]+:|^\[\d+:\d+\]\s*[A-ZÁÉÍÓÚ][a-záéíóúñ\s]+:)'
        
        lineas = bloque.split('\n')
        fragmento_actual = []
        
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
                
            # Si detectamos cambio de hablante y ya tenemos contenido, crear fragmento
            if re.match(patron_hablante, linea) and fragmento_actual:
                texto_fragmento = '\n'.join(fragmento_actual).strip()
                if len(texto_fragmento.split()) > 10:  # Mínimo 10 palabras
                    fragmentos_finales.extend(_dividir_por_tamaño(texto_fragmento, max_palabras))
                fragmento_actual = [linea]
            else:
                fragmento_actual.append(linea)
        
        # Agregar último fragmento del bloque
        if fragmento_actual:
            texto_fragmento = '\n'.join(fragmento_actual).strip()
            if len(texto_fragmento.split()) > 10:
                fragmentos_finales.extend(_dividir_por_tamaño(texto_fragmento, max_palabras))
    
    # Si no se encontraron patrones especiales, fragmentar por párrafos y tamaño
    if not fragmentos_finales:
        fragmentos_finales = _dividir_por_parrafos_y_tamaño(texto, max_palabras)
    
    # Limpieza final
    return [f.strip() for f in fragmentos_finales if f.strip() and len(f.split()) >= 5]

def _dividir_por_tamaño(texto: str, max_palabras: int) -> List[str]:
    """Divide un texto por tamaño máximo de palabras, respetando frases completas."""
    palabras = texto.split()
    
    if len(palabras) <= max_palabras:
        return [texto]
    
    fragmentos = []
    inicio = 0
    
    while inicio < len(palabras):
        fin = min(inicio + max_palabras, len(palabras))
        
        # Buscar punto final cercano para corte natural
        if fin < len(palabras):
            for i in range(fin, max(inicio + int(max_palabras * 0.7), inicio + 10), -1):
                if i < len(palabras) and palabras[i-1].endswith('.'):
                    fin = i
                    break
        
        fragmento = ' '.join(palabras[inicio:fin])
        fragmentos.append(fragmento)
        inicio = fin
    
    return fragmentos

def _dividir_por_parrafos_y_tamaño(texto: str, max_palabras: int) -> List[str]:
    """División por párrafos con control de tamaño."""
    parrafos = [p.strip() for p in texto.split('\n\n') if p.strip()]
    
    if not parrafos:
        parrafos = [p.strip() for p in texto.split('\n') if p.strip()]
    
    fragmentos = []
    fragmento_actual = []
    palabras_actuales = 0
    
    for parrafo in parrafos:
        palabras_parrafo = len(parrafo.split())
        
        if palabras_actuales + palabras_parrafo <= max_palabras:
            fragmento_actual.append(parrafo)
            palabras_actuales += palabras_parrafo
        else:
            # Guardar fragmento actual
            if fragmento_actual:
                fragmentos.append('\n\n'.join(fragmento_actual))
            
            # Si el párrafo es muy largo, dividirlo
            if palabras_parrafo > max_palabras:
                fragmentos.extend(_dividir_por_tamaño(parrafo, max_palabras))
                fragmento_actual = []
                palabras_actuales = 0
            else:
                fragmento_actual = [parrafo]
                palabras_actuales = palabras_parrafo
    
    # Agregar último fragmento
    if fragmento_actual:
        fragmentos.append('\n\n'.join(fragmento_actual))
    
    return fragmentos

def fragmentar_conversacion(conversacion: Dict) -> List[Dict]:
    """
    Toma una conversación completa y la fragmenta automáticamente.
    
    Args:
        conversacion: {
            'titulo': str,
            'contenido': str, 
            'fecha': str (ISO),
            'participantes': list,
            'metadata': dict
        }
    
    Returns:
        Lista de fragmentos con metadatos
    """
    contenido = conversacion.get('contenido', '').strip()
    if not contenido:
        return []
    
    # Obtener fragmentos de texto
    textos_fragmentos = criterio_fragmentacion_semantica(contenido)
    
    fragmentos_con_metadata = []
    conversacion_id = str(uuid.uuid4())
    
    for i, texto_fragmento in enumerate(textos_fragmentos):
        fragmento_id = str(uuid.uuid4())
        
        # Detectar si el fragmento tiene información temporal individual
        referencias_temporales = []
        palabras_clave = extraer_palabras_clave(texto_fragmento)
        
        # Heredar timestamp de la conversación o detectar individual
        timestamp_fragmento = conversacion.get('fecha')
        
        # Crear metadatos del fragmento
        metadata_fragmento = {
            "fragmento_id": fragmento_id,
            "conversacion_id": conversacion_id,
            "conversacion_titulo": conversacion.get('titulo', 'Sin título'),
            "posicion_en_conversacion": i + 1,
            "total_fragmentos_conversacion": len(textos_fragmentos),
            "texto": texto_fragmento,
            "palabras_clave": palabras_clave,
            "timestamp": timestamp_fragmento,
            "participantes": conversacion.get('participantes', []),
            "metadata_conversacion": conversacion.get('metadata', {}),
            "created_at": datetime.now().isoformat(),
            "es_temporal": bool(timestamp_fragmento),
            "tipo_contexto": _detectar_tipo_fragmento(texto_fragmento, conversacion.get('metadata', {}))
        }
        
        fragmentos_con_metadata.append({
            'id': fragmento_id,
            'metadata': metadata_fragmento
        })
    
    return fragmentos_con_metadata

def _detectar_tipo_fragmento(texto: str, metadata_conversacion: Dict) -> str:
    """Detecta el tipo de fragmento basado en contenido y contexto de conversación."""
    texto_lower = texto.lower()
    
    # Si la conversación ya tiene tipo, heredarlo como base
    tipo_base = metadata_conversacion.get('tipo', 'general')
    
    # Patrones específicos de fragmentos
    patrones_especificos = {
        "decision": ["decidimos", "acordamos", "resolveremos", "la decisión", "se decidió"],
        "accion": ["hacer", "implementar", "ejecutar", "realizar", "completar"],
        "pregunta": ["¿", "como", "cómo", "qué", "cuándo", "dónde", "por qué"],
        "conclusion": ["en resumen", "para concluir", "finalmente", "en conclusión"],
        "problema": ["problema", "issue", "bug", "error", "falla", "no funciona"]
    }
    
    for tipo, palabras in patrones_especificos.items():
        if any(palabra in texto_lower for palabra in palabras):
            return tipo
    
    return tipo_base

# Función de utilidad para testing
def test_fragmentacion():
    """Función de testing para validar la fragmentación."""
    texto_test = """
    Juan: Hola equipo, vamos a revisar el estado del proyecto.
    
    María: Perfecto Juan. He completado la implementación del módulo de usuario. 
    Todo funciona correctamente y ya está listo para testing.
    
    Pedro: Excelente María. Por mi parte, he encontrado algunos problemas con la 
    base de datos. Específicamente, las consultas están tomando demasiado tiempo.
    
    Juan: ¿Qué propones Pedro para solucionarlo?
    
    Pedro: Creo que necesitamos optimizar los índices y revisar algunas queries.
    También podríamos implementar cache para las consultas más frecuentes.
    
    ---
    
    DECISIONES TOMADAS:
    1. María continuará con el testing del módulo de usuario
    2. Pedro se enfocará en la optimización de la base de datos
    3. Próxima reunión: viernes a las 15:00
    """
    
    conversacion_test = {
        'titulo': 'Reunión de Proyecto - Revisión Semanal',
        'contenido': texto_test,
        'fecha': '2025-01-25T10:00:00',
        'participantes': ['Juan', 'María', 'Pedro'],
        'metadata': {'tipo': 'reunion', 'proyecto': 'Sistema Web', 'duracion': '30min'}
    }
    
    fragmentos = fragmentar_conversacion(conversacion_test)
    
    print(f"🔍 Testing de Fragmentación:")
    print(f"Conversación: {conversacion_test['titulo']}")
    print(f"Total fragmentos generados: {len(fragmentos)}\n")
    
    for i, frag in enumerate(fragmentos, 1):
        print(f"--- Fragmento {i} ---")
        print(f"ID: {frag['id']}")
        print(f"Tipo: {frag['metadata']['tipo_contexto']}")
        print(f"Palabras clave: {frag['metadata']['palabras_clave'][:5]}")
        print(f"Texto: {frag['metadata']['texto'][:100]}...")
        print()
    
    return fragmentos

if __name__ == "__main__":
    test_fragmentacion()