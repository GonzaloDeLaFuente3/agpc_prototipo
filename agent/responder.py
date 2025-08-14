# agent/responder.py
import requests
import os

# Google AI Studio API 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDfgYQq3a0bAZ0pgDCkuy8xmmytv8FfvO8")  # Obtén en https://aistudio.google.com/

def construir_prompt(pregunta, contextos):
    #Toma la pregunta del usuario
    # Toma los contextos relacionados (que vienen del grafo)
    # Construye un prompt estructurado
    prompt = """Usando los siguientes fragmentos de contexto, respondé a la siguiente pregunta.
Cuando necesites referenciar un fragmento, usa su título entre paréntesis.

Fragmentos:
"""
    for id, c in contextos.items():
        prompt += f"- {c['titulo']}: {c['texto']}\n"
    
    prompt += f"\nPregunta: {pregunta}\nRespuesta:"
    return prompt

def responder_con_google_gemini(pregunta, contextos):
    if not GOOGLE_API_KEY:
        return "[ERROR] No se configuró GOOGLE_API_KEY. Obtén una gratis en https://aistudio.google.com/"
    
    prompt = construir_prompt(pregunta, contextos)
    print(f"Prompt enviado: {prompt}")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GOOGLE_API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": {
            "temperature": 0.7,# Creatividad moderada
            "maxOutputTokens": 150,# Respuestas concisas
            "topP": 0.8,# Control de coherencia
            "topK": 10# Diversidad limitada
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if "candidates" in data and len(data["candidates"]) > 0:
                texto = data["candidates"][0]["content"]["parts"][0]["text"]
                return texto.strip()
            else:
                return "[ERROR] No se generó respuesta"
        else:
            return f"[ERROR Google {response.status_code}] {response.text}"
            
    except Exception as e:
        return f"[ERROR Google] {str(e)}"

# Función principal
def responder_con_ia(pregunta, contextos):
    """Wrapper para mantener compatibilidad con main.py"""
    return responder_con_google_gemini(pregunta, contextos)