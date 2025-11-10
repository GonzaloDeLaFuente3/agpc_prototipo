# agent/responder.py - Optimizado con soporte temporal
import requests
import os
from datetime import datetime
from typing import Dict
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDcCbQs_swG7s41Q0cjmk_ESfyMjg4hfmU")
genai.configure(api_key=GEMINI_API_KEY)

def construir_prompt(pregunta: str, contextos: dict) -> str:
    """
    Construye prompt optimizado para respuestas temporales y documentos.
    Mejoras:
    - Distingue entre fragmentos de conversaciones y documentos
    - Instrucciones claras sobre uso de contextos
    - Información temporal explícita
    - Manejo de fragmentos relacionados
    """
    
    # Detectar si la pregunta es temporal
    es_pregunta_temporal = any(palabra in pregunta.lower() for palabra in [
        'mañana', 'ayer', 'hoy', 'semana', 'mes', 'lunes', 'martes', 
        'miércoles', 'jueves', 'viernes', 'sábado', 'domingo',
        'cuando', 'cuándo', 'qué día', 'fecha'
    ])
    
    # Clasificar contextos por tipo
    fragmentos_documentos = []
    fragmentos_conversaciones = []
    tiene_timestamps = False
    
    for id, c in contextos.items():
        titulo = c.get('titulo', 'Sin título')
        texto = c.get('texto', '')
        timestamp = c.get('timestamp')
        es_pdf = c.get('es_pdf', False)
        tipo_contexto = c.get('tipo_contexto', 'general')
        
        # Clasificar por tipo
        if es_pdf or tipo_contexto == 'documento':
            # Es un fragmento de documento
            source_doc = c.get('source_document', 'documento')
            posicion = c.get('position_in_doc', 0)
            total_frags = c.get('total_fragmentos_pdf', 1)
            
            fragmentos_documentos.append({
                'titulo': f"📄 {source_doc} (parte {posicion+1}/{total_frags})",
                'texto': texto,
                'timestamp': timestamp
            })
        else:
            # Es un fragmento de conversación
            if timestamp:
                tiene_timestamps = True
                try:
                    fecha = datetime.fromisoformat(timestamp.replace('Z', ''))
                    fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
                    titulo_formateado = f"📅 [{fecha_str}] {titulo}"
                except:
                    titulo_formateado = f"💬 {titulo}"
            else:
                titulo_formateado = f"💬 {titulo}"
            
            fragmentos_conversaciones.append({
                'titulo': titulo_formateado,
                'texto': texto,
                'timestamp': timestamp
            })
    
    # Construir secciones del prompt
    secciones = []
    
    if fragmentos_documentos:
        docs_formateados = []
        for frag in fragmentos_documentos:
            docs_formateados.append(f"{frag['titulo']}:\n{frag['texto']}")
        
        secciones.append(f"""**DOCUMENTOS RELEVANTES:**
{chr(10).join(docs_formateados)}""")
    
    if fragmentos_conversaciones:
        convs_formateadas = []
        for frag in fragmentos_conversaciones:
            convs_formateadas.append(f"{frag['titulo']}:\n{frag['texto']}")
        
        secciones.append(f"""**CONVERSACIONES RELEVANTES:**
{chr(10).join(convs_formateadas)}""")
    
    # Construir prompt según tipo de pregunta
    if es_pregunta_temporal and tiene_timestamps:
        # Prompt especializado para preguntas temporales
        prompt = f"""Eres un asistente experto que ayuda a responder preguntas sobre eventos,conversaciones, actividades programadas y documentos.

**PREGUNTA DEL USUARIO:**
"{pregunta}"

{chr(10).join(secciones)}

**INSTRUCCIONES:**
1. Si la pregunta es sobre contenido de un documento o conversacion, explica detalladamente basándote en los fragmentos del documento o conversacion
2. Si la pregunta es temporal (fechas, horarios), prioriza esa información
3. Si hay múltiples fragmentos del mismo documento, sintetízalos en una respuesta coherente y completa
4. Incluye fechas y horarios cuando estén disponibles
5. Si los fragmentos son de documentos técnicos o conceptuales, explica en detalle

**RESPUESTA:**"""

    else:
        # Prompt general para preguntas estructurales y documentos
        prompt = f"""Eres un asistente experto que ayuda a explicar y responder sobre contenido de documentos y conversaciones.

**PREGUNTA:**
"{pregunta}"

{chr(10).join(secciones)}

**INSTRUCCIONES:**
1. Responde basándote ÚNICAMENTE en la información de los contextos proporcionados
2. Si la pregunta es sobre un concepto o procedimiento en un documento, explícalo de forma detallada y clara
3. Si hay varios fragmentos del mismo documento, combina la información para dar una respuesta completa
4. Estructura tu respuesta de forma clara, usando párrafos cuando sea necesario
5. Si necesitas referenciar un fragmento específico, menciona su fuente

**RESPUESTA:**"""
    
    return prompt


def responder_con_ia(pregunta: str, contextos: dict) -> str:
    """
    Genera respuesta usando Google Gemini con prompt optimizado.
    Args:
        pregunta: Pregunta del usuario
        contextos: Dict de contextos con estructura {id: {titulo, texto, timestamp?, ...}}
    
    Returns:
        Respuesta generada por el LLM
    """
    if not GEMINI_API_KEY:
        return "[ERROR] No se configuró GEMINI_API_KEY"
    
    if not contextos:
        return "No se encontraron contextos relevantes para responder tu pregunta."
    
    prompt = construir_prompt(pregunta, contextos)
    
    # ✅ Usar SDK de Google en lugar de requests
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Configuración optimizada (igual que RAG estándar)
        generation_config = {
            'temperature': 0.3,
            'top_p': 0.95,
            'top_k': 40,
            'max_output_tokens': 2048
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        respuesta = response.text.strip()
        
        # Post-procesamiento: remover frases problemáticas comunes
        frases_problematicas = [
            "la información provista no",
            "los fragmentos no mencionan",
            "no se proporciona información",
            "no hay información sobre"
        ]
        
        if any(frase in respuesta.lower() for frase in frases_problematicas):
            print(f"⚠️ Respuesta problemática detectada: {respuesta[:100]}")
            
            if contextos:
                primer_contexto = list(contextos.values())[0]
                titulo = primer_contexto.get('titulo', 'contexto')
                timestamp = primer_contexto.get('timestamp')
                
                if timestamp:
                    try:
                        fecha = datetime.fromisoformat(timestamp.replace('Z', ''))
                        fecha_str = fecha.strftime('%d/%m a las %H:%M')
                        return f"Encontré información relacionada en '{titulo}' programado para el {fecha_str}."
                    except:
                        return f"Encontré información relacionada en '{titulo}'."
                else:
                    return f"Encontré información relacionada en '{titulo}'."
        
        return respuesta
        
    except Exception as e:
        return f"[ERROR] {str(e)}"