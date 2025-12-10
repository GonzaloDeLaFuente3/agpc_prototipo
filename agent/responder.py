# agent/responder.py 
import requests
import os
from datetime import datetime
from typing import Dict
import google.generativeai as genai


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 

if not GEMINI_API_KEY:
    raise ValueError("❌ ERROR: No se encontró GEMINI_API_KEY en el archivo .env")

genai.configure(api_key=GEMINI_API_KEY)

def construir_prompt(pregunta: str, contextos: dict) -> str:
    """
    Construye prompt optimizado para respuestas temporales y documentos.
    - Distingue entre fragmentos de conversaciones y documentos
    - Instrucciones claras sobre uso de contextos
    - Información temporal explícita
    - Manejo de fragmentos relacionados
    - Detección de preguntas de enumeración 
    - Indicación de cantidad de contextos disponibles
    """
    
    #  Contar contextos disponibles
    num_contextos = len(contextos)
    
    # Detectar si la pregunta es temporal 
    es_pregunta_temporal = any(palabra in pregunta.lower() for palabra in [
        'mañana', 'ayer', 'hoy', 'semana', 'mes', 'lunes', 'martes', 
        'miércoles', 'jueves', 'viernes', 'sábado', 'domingo',
        'cuando', 'cuándo', 'qué día', 'fecha'
    ])
    
    #  Detectar si la pregunta pide enumeración
    es_pregunta_enumeracion = any(palabra in pregunta.lower() for palabra in [
        'qué casos', 'cuáles', 'cuántos', 'qué reuniones', 'qué proyectos',
        'qué documentos', 'lista', 'todos los', 'cuáles son', 'enumera',
        'menciona todos', 'qué temas', 'qué conversaciones'
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
        # CASO 1: Pregunta TEMPORAL
        prompt = f"""Eres un asistente experto que ayuda a responder preguntas sobre eventos, conversaciones, actividades programadas y documentos.

**PREGUNTA DEL USUARIO:**
"{pregunta}"

**CONTEXTOS DISPONIBLES ({num_contextos} contextos en total):**
{chr(10).join(secciones)}

**INSTRUCCIONES IMPORTANTES:**
1. Se te proporcionan {num_contextos} contextos con información relevante
2. La pregunta tiene componente TEMPORAL - prioriza fechas y horarios
3. Si hay MÚLTIPLES eventos/casos/documentos, menciónalos TODOS de forma agrupada
4. Sintetiza información común entre los contextos
5. Incluye fechas y horarios cuando estén disponibles
6. Si los contextos son fragmentos relacionados, combínalos en una respuesta coherente

**FORMATO DE RESPUESTA:**
- Si hay múltiples casos/eventos: Indica cuántos encontraste y enuméralos de forma concisa
- Agrupa por patrones comunes cuando sea posible
- Sé completo pero evita redundancias

**RESPUESTA:**"""

    elif es_pregunta_enumeracion:
        # CASO 2: Pregunta de ENUMERACIÓN 
        prompt = f"""Eres un asistente experto en análisis y síntesis de información legal y documental.

**PREGUNTA DEL USUARIO:**
"{pregunta}"

**CONTEXTOS DISPONIBLES ({num_contextos} contextos en total):**
{chr(10).join(secciones)}

**INSTRUCCIONES CRÍTICAS:**
1. Se te proporcionan {num_contextos} contextos relevantes
2. La pregunta pide una ENUMERACIÓN o LISTA de elementos
3. Debes mencionar TODOS los casos/documentos/elementos encontrados
4. NO te limites solo al primer contexto - sintetiza TODOS
5. Agrupa por patrones comunes si existen (ej: "8 casos de Amparo por mora administrativa")
6. Sé completo pero conciso - evita repetir la misma información

**FORMATO DE RESPUESTA ESPERADO:**
- Primero: Indica el total encontrado y el patrón común si existe
- Luego: Enumera los elementos de forma concisa (ej: "Casos 1, 2, 3, 4, 5, 6, 7 y 8")
- Finalmente: Menciona características comunes relevantes

**EJEMPLO DE BUENA RESPUESTA:**
"Durante [periodo] se discutieron 8 casos de [tipo] (Casos 1, 2, 3, 4, 5, 6, 7 y 8). Todos estos casos comparten [características comunes]."

**RESPUESTA:**"""

    else:
        # CASO 3: Pregunta GENERAL (explicación, concepto, etc.) 
        prompt = f"""Eres un asistente experto que ayuda a explicar y responder sobre contenido de documentos y conversaciones.

**PREGUNTA:**
"{pregunta}"

**CONTEXTOS DISPONIBLES ({num_contextos} contextos en total):**
{chr(10).join(secciones)}

**INSTRUCCIONES CRÍTICAS - LEE CON ATENCIÓN:**
1. Se te proporcionan {num_contextos} contextos relevantes para responder
2. **DEBES ANALIZAR Y USAR TODOS LOS {num_contextos} CONTEXTOS** en tu respuesta
3. Si varios contextos contienen casos o ejemplos similares, MENCIÓNALOS TODOS de forma concisa
4. Si encuentras múltiples casos/documentos relacionados, AGRÚPALOS y haz una síntesis clara
5. NO te limites solo al primer contexto - tu respuesta debe reflejar el análisis completo de todos los contextos
6. Si los contextos son fragmentos del mismo tema, combínalos en una respuesta coherente

**FORMATO DE RESPUESTA ESPERADO:**
- Si hay múltiples casos/documentos similares: "Se encontraron {num_contextos} casos relacionados: [lista breve o agrupación]"
- Si hay información común en varios contextos: "Los contextos mencionan como patrón común: [síntesis]"
- Si son fragmentos relacionados: Integra la información en párrafos coherentes sin repetir

**EJEMPLO DE BUENA RESPUESTA:**
Si la pregunta es "¿Qué casos se discutieron?" y tienes 8 contextos de "Amparo por mora":
"Se encontraron 8 casos de Amparo por mora administrativa (Casos 1, 2, 3, 4, 5, 6, 7 y 8). Todos comparten el patrón de que el proceso es rápido (30-60 días) y el Estado debe cumplir las órdenes judiciales bajo amenaza de multas."

**RESPUESTA:**"""
    
    return prompt


def responder_con_ia(pregunta: str, contextos: dict) -> str:
    """
    Genera respuesta usando Google Gemini con prompt optimizado.
    """
    if not GEMINI_API_KEY:
        return "[ERROR] No se configuró GEMINI_API_KEY"
    
    if not contextos:
        return "No se encontraron contextos relevantes para responder tu pregunta."
    
    prompt = construir_prompt(pregunta, contextos)
    
    # Usar SDK de Google en lugar de requests
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        # Configuración  (igual que RAG estándar)
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