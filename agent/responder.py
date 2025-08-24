# agent/responder.py - Optimizado
import requests
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDfgYQq3a0bAZ0pgDCkuy8xmmytv8FfvO8")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GOOGLE_API_KEY}"

def construir_prompt(pregunta: str, contextos: dict) -> str:
    """Construye el prompt para la IA."""
    prompt = """Usando los siguientes fragmentos de contexto, respondé a la pregunta.
Cuando necesites referenciar un fragmento, usa su título entre paréntesis.

Fragmentos:
"""
    for id, c in contextos.items():
        prompt += f"- {c['titulo']}: {c['texto']}\n"
    
    prompt += f"\nPregunta: {pregunta}\nRespuesta:"
    return prompt

def responder_con_ia(pregunta: str, contextos: dict) -> str:
    """Genera respuesta usando Google Gemini."""
    if not GOOGLE_API_KEY:
        return "[ERROR] No se configuró GOOGLE_API_KEY"
    
    prompt = construir_prompt(pregunta, contextos)
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 150,
            "topP": 0.8,
            "topK": 10
        }
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and data["candidates"]:
                return data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return "[ERROR] No se generó respuesta"
        else:
            return f"[ERROR API {response.status_code}] {response.text}"
            
    except Exception as e:
        return f"[ERROR] {str(e)}"