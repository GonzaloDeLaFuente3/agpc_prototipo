# agent/fragmentador.py
import uuid
import re
from datetime import datetime
from typing import List, Dict, Tuple
from agent.extractor import extraer_palabras_clave
from agent.temporal_parser import detectar_timestamps_fragmento
from agent.utils import normalizar_timestamp_para_guardar

def criterio_fragmentacion_semantica(texto: str, max_palabras: int = 300, min_palabras: int = 50) -> List[str]:
    """
    Fragmenta una conversación en bloques semánticamente coherentes.
    ESTRATEGIA MEJORADA:
    1. Agrupa múltiples líneas de diálogo hasta alcanzar min_palabras
    2. Corta en cambios de tema o cuando alcanza max_palabras
    3. Mantiene contexto completo de intercambios
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
        patron_hablante = r'^(\s*-?\s*[A-ZÁÉÍÓÚ][a-záéíóúñ\s]+:|^\[\d+:\d+\]\s*[A-ZÁÉÍÓÚ][a-záéíóúñ\s]+:)'
        
        lineas = bloque.split('\n')
        fragmento_actual = []
        palabras_actuales = 0
        
        for linea in lineas:
            linea = linea.strip()
            if not linea:
                continue
            
            palabras_linea = len(linea.split())
            
            #  Solo crear fragmento si:
            # 1. Ya tenemos suficiente contexto (>= min_palabras)
            # 2. Y detectamos cambio de hablante
            # 3. O alcanzamos max_palabras
            
            if re.match(patron_hablante, linea) and fragmento_actual:
                # Si ya tenemos suficiente contexto, crear fragmento
                if palabras_actuales >= min_palabras or palabras_actuales + palabras_linea > max_palabras:
                    texto_fragmento = '\n'.join(fragmento_actual).strip()
                    if palabras_actuales >= 10:  # Mínimo 
                        fragmentos_finales.append(texto_fragmento)
                    
                    # Iniciar nuevo fragmento con esta línea
                    fragmento_actual = [linea]
                    palabras_actuales = palabras_linea
                else:
                    # Aún no tenemos suficiente contexto, seguir agregando
                    fragmento_actual.append(linea)
                    palabras_actuales += palabras_linea
            else:
                # Agregar línea al fragmento actual
                fragmento_actual.append(linea)
                palabras_actuales += palabras_linea
                
                # Si alcanzamos max_palabras, forzar corte
                if palabras_actuales >= max_palabras:
                    texto_fragmento = '\n'.join(fragmento_actual).strip()
                    if palabras_actuales >= 10:
                        fragmentos_finales.append(texto_fragmento)
                    fragmento_actual = []
                    palabras_actuales = 0
        
        # Agregar último fragmento del bloque
        if fragmento_actual:
            texto_fragmento = '\n'.join(fragmento_actual).strip()
            palabras = len(texto_fragmento.split())
            
            # Si es muy corto, intentar unir con el fragmento anterior
            if palabras < min_palabras and fragmentos_finales:
                fragmentos_finales[-1] = fragmentos_finales[-1] + '\n' + texto_fragmento
            elif palabras >= 10:  # Mínimo 
                fragmentos_finales.append(texto_fragmento)
    
    # Si no se encontraron patrones especiales, fragmentar por párrafos y tamaño
    if not fragmentos_finales:
        fragmentos_finales = _dividir_por_parrafos_y_tamaño(texto, max_palabras)
    
    # Limpieza final: eliminar fragmentos muy cortos
    fragmentos_limpios = []
    for f in fragmentos_finales:
        f = f.strip()
        palabras = len(f.split())
        
        # Si el fragmento es muy corto, intentar unir con el anterior
        if palabras < 20 and fragmentos_limpios:
            fragmentos_limpios[-1] = fragmentos_limpios[-1] + '\n' + f
        elif palabras >= 10:
            fragmentos_limpios.append(f)
    
    return fragmentos_limpios

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
    """
    contenido = conversacion.get('contenido', '').strip()
    if not contenido:
        return []
    
    # Obtener fragmentos de texto
    textos_fragmentos = criterio_fragmentacion_semantica(contenido)
    
    fragmentos_con_metadata = []
    conversacion_id = str(uuid.uuid4())
    
    # TIMESTAMP BASE YA NORMALIZADO (viene de agregar_conversacion)
    timestamp_base_conversacion = conversacion.get('fecha')
    print(f"Timestamp base conversación: {timestamp_base_conversacion}")
    
    for i, texto_fragmento in enumerate(textos_fragmentos):
        fragmento_id = str(uuid.uuid4())
        
        # Detectar timestamp específico del fragmento
        timestamp_fragmento = detectar_timestamps_fragmento(
            texto_fragmento, 
            timestamp_base_conversacion
        )
        
        # NORMALIZAR TIMESTAMP DEL FRAGMENTO
        if timestamp_fragmento:
            timestamp_normalizado = normalizar_timestamp_para_guardar(timestamp_fragmento)
            timestamp_fragmento = timestamp_normalizado if timestamp_normalizado else timestamp_base_conversacion
            print(f"Fragmento {i+1} - timestamp específico normalizado: {timestamp_fragmento}")
        elif timestamp_base_conversacion:
            # Heredar timestamp base (ya normalizado)
            timestamp_fragmento = timestamp_base_conversacion
            print(f"Fragmento {i+1} - heredó timestamp base: {timestamp_fragmento}")
        
        # Determinar si es temporal basado en timestamp específico
        es_temporal = bool(timestamp_fragmento)
        
        palabras_clave = extraer_palabras_clave(texto_fragmento)
        
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
            "timestamp_original_conversacion": timestamp_base_conversacion,  
            "participantes": conversacion.get('participantes', []),
            "metadata_conversacion": conversacion.get('metadata', {}),
            "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
            "es_temporal": es_temporal,
            "tipo_contexto": _detectar_tipo_fragmento(texto_fragmento, conversacion.get('metadata', {})),
            "tiene_timestamp_especifico": timestamp_fragmento != timestamp_base_conversacion  
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
    
    # PATRONES ESPECÍFICOS AMPLIADOS
    patrones_especificos = {
        "decision": ["decidimos", "acordamos", "resolveremos", "la decisión", "se decidió", 
                    "optamos", "elegimos", "determinamos"],
        "accion": ["hacer", "implementar", "ejecutar", "realizar", "completar", 
                "desarrollar", "crear", "construir", "establecer"],
        "pregunta": ["¿", "como", "cómo", "qué", "cuándo", "dónde", "por qué", 
                    "cuál", "quién", "cuánto"],
        "conclusion": ["en resumen", "para concluir", "finalmente", "en conclusión",
                    "resumiendo", "concluyendo"],
        "problema": ["problema", "issue", "bug", "error", "falla", "no funciona",
                    "dificultad", "obstáculo", "inconveniente"],
        "tarea": ["tarea", "pendiente", "debe", "tengo que", "hay que",
                "asignar", "responsable", "deadline"],
        "evento": ["reunión", "meeting", "cita", "evento", "conferencia",
                "presentación", "demo"],
        "temporalidad_fuerte": ["mañana", "ayer", "hoy", "próximo", "pasado",
                            "lunes", "martes", "miércoles", "jueves", "viernes"]
    }
    
    # Contar coincidencias por categoría
    coincidencias = {}
    for tipo, palabras in patrones_especificos.items():
        count = sum(1 for palabra in palabras if palabra in texto_lower)
        if count > 0:
            coincidencias[tipo] = count
    
    # Si hay coincidencias, usar la más fuerte
    if coincidencias:
        tipo_detectado = max(coincidencias.items(), key=lambda x: x[1])[0]
        
        # Casos especiales
        if tipo_detectado == "temporalidad_fuerte":
            return "temporal_especifico"
        else:
            return tipo_detectado
    
    return tipo_base