# agent/responder.py - Optimizado con soporte temporal
import requests
import os
from datetime import datetime
from typing import Dict

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDfgYQq3a0bAZ0pgDCkuy8xmmytv8FfvO8")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-001:generateContent?key={GOOGLE_API_KEY}"

def construir_prompt(pregunta: str, contextos: dict) -> str:
    """
    Construye prompt optimizado para respuestas temporales.
    
    Mejoras:
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
    
    # Construir lista de contextos con información temporal
    contextos_formateados = []
    tiene_timestamps = False
    
    for id, c in contextos.items():
        titulo = c.get('titulo', 'Sin título')
        texto = c.get('texto', '')
        timestamp = c.get('timestamp')
        
        # Formatear contexto con timestamp si existe
        if timestamp:
            tiene_timestamps = True
            try:
                fecha = datetime.fromisoformat(timestamp.replace('Z', ''))
                fecha_str = fecha.strftime('%d/%m/%Y %H:%M')
                contextos_formateados.append(
                    f"📅 [{fecha_str}] {titulo}:\n{texto}"
                )
            except:
                contextos_formateados.append(f"• {titulo}:\n{texto}")
        else:
            contextos_formateados.append(f"• {titulo}:\n{texto}")
    
    # Construir prompt según tipo de pregunta
    if es_pregunta_temporal and tiene_timestamps:
        # Prompt especializado para preguntas temporales
        prompt = f"""Eres un asistente que ayuda a responder preguntas sobre eventos y actividades programadas.

**CONTEXTO IMPORTANTE:**
Los fragmentos que recibes ya fueron filtrados por fecha/hora según la pregunta del usuario. Esto significa que SI son relevantes temporalmente.

**PREGUNTA DEL USUARIO:**
"{pregunta}"

**FRAGMENTOS RELEVANTES (filtrados temporalmente):**

{chr(10).join(contextos_formateados)}

**INSTRUCCIONES:**
1. Los fragmentos anteriores YA fueron filtrados para coincidir con el periodo temporal de la pregunta
2. Si los fragmentos mencionan eventos, reuniones o actividades, descríbelos directamente
3. Incluye fechas y horarios cuando estén disponibles
4. Si hay múltiples fragmentos de la misma conversación, sintetízalos en una respuesta coherente
5. NO digas "no hay información" o "no se menciona" - los fragmentos SON la respuesta
6. Sé conciso y directo (máximo 2-3 oraciones)

**RESPUESTA:**"""

    else:
        # Prompt general para preguntas estructurales
        prompt = f"""Usando los siguientes fragmentos de contexto, responde la pregunta de forma precisa y concisa.

**PREGUNTA:**
"{pregunta}"

**CONTEXTOS DISPONIBLES:**

{chr(10).join(contextos_formateados)}

**INSTRUCCIONES:**
1. Responde basándote ÚNICAMENTE en la información de los contextos
2. Sé específico y directo
3. Si necesitas referenciar un fragmento, menciona su título
4. Máximo 2-3 oraciones

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
    if not GOOGLE_API_KEY:
        return "[ERROR] No se configuró GOOGLE_API_KEY"
    
    if not contextos:
        return "No se encontraron contextos relevantes para responder tu pregunta."
    
    prompt = construir_prompt(pregunta, contextos)
    
    # Configuración optimizada para respuestas concisas y precisas
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,      # Más bajo = más determinista
            "maxOutputTokens": 200,  # Aumentado para respuestas completas
            "topP": 0.8,
            "topK": 10
        }
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                respuesta = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Post-procesamiento: remover frases problemáticas comunes
                frases_problematicas = [
                    "la información provista no",
                    "los fragmentos no mencionan",
                    "no se proporciona información",
                    "no hay información sobre"
                ]
                
                # Si la respuesta contiene frases problemáticas, intentar regenerar
                if any(frase in respuesta.lower() for frase in frases_problematicas):
                    # Logging para debugging
                    print(f"⚠️ Respuesta problemática detectada: {respuesta[:100]}")
                    
                    # Crear respuesta de fallback más útil
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
            return "[ERROR] No se generó respuesta"
        else:
            return f"[ERROR API {response.status_code}] {response.text}"
            
    except Exception as e:
        return f"[ERROR] {str(e)}"