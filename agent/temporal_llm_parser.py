# agent/temporal_llm_parser.py
import json
import re
import os
from datetime import datetime
from typing import Dict, Optional
import google.generativeai as genai

# Configurar Gemini con API key desde variable de entorno
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDfgYQq3a0bAZ0pgDCkuy8xmmytv8FfvO8")
genai.configure(api_key=GEMINI_API_KEY)


def analizar_temporalidad_con_llm(
    pregunta: str,
    momento_consulta: Optional[datetime] = None,
    factor_base: float = 1.5
) -> Dict:
    """
    Analiza temporalidad usando Google Gemini
    
    Args:
        pregunta: Pregunta del usuario
        momento_consulta: Momento de la consulta (default: ahora)
        factor_base: Factor de refuerzo base configurado
    
    Returns:
        Dict con estructura compatible con sistema existente
    """
    if momento_consulta is None:
        momento_consulta = datetime.now()
    
    try:
        # 1. Construir prompt
        prompt = _construir_prompt(pregunta, momento_consulta)
        
        # 2. Llamar a Gemini
        respuesta_texto = _llamar_gemini(prompt)
        
        # 3. Parsear y validar respuesta
        resultado = _parsear_respuesta(respuesta_texto, factor_base, momento_consulta)
        
        return resultado
        
    except Exception as e:
        print(f"⚠️ Error en análisis temporal LLM: {e}")
        # Fallback seguro
        return _crear_resultado_fallback(factor_base, momento_consulta, str(e))


def _construir_prompt(pregunta: str, momento: datetime) -> str:
    """Construye prompt optimizado para Gemini"""
    
    # Información contextual
    dia_semana_es = {
        'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
        'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo'
    }
    dia_semana = dia_semana_es.get(momento.strftime('%A'), momento.strftime('%A'))
    fecha_actual = momento.strftime('%Y-%m-%d %H:%M')
    
    return f"""Eres un asistente experto en análisis temporal. Tu tarea es detectar si una pregunta tiene intención temporal y generar ventanas de tiempo precisas.

**CONTEXTO ACTUAL:**
- Fecha y hora: {fecha_actual}
- Día de la semana: {dia_semana}

**PREGUNTA DEL USUARIO:**
"{pregunta}"

**INSTRUCCIONES:**
1. Analiza si la pregunta tiene intención temporal clara
2. Si es temporal, calcula la ventana de tiempo (inicio y fin) en formato ISO
3. Responde SOLO con JSON válido (sin markdown, sin explicaciones extra)

**REGLAS DE INTERPRETACIÓN:**
- "mañana" = día siguiente completo (00:00:00 a 23:59:59)
- "por la mañana" = 06:00:00 a 12:00:00
- "por la tarde" = 14:00:00 a 20:00:00
- "por la noche" = 20:00:00 a 23:59:59
- "ayer" = día anterior completo
- "hoy" = día actual completo
- "esta semana" = desde el lunes de esta semana hasta el domingo
- "semana pasada" = lunes a domingo de la semana anterior
- "este mes" = primer día a último día del mes actual
- "mes pasado" = primer día a último día del mes anterior
- "el lunes" (sin calificador) = próximo lunes
- "lunes pasado" = lunes de la semana anterior
- Fechas específicas: "15 de marzo", "el 20 de octubre"

**FORMATO DE RESPUESTA (JSON válido):**
{{
    "es_temporal": true/false,
    "ventana_inicio": "YYYY-MM-DDTHH:MM:SS" o null,
    "ventana_fin": "YYYY-MM-DDTHH:MM:SS" o null,
    "confianza": 0.95,
    "explicacion": "Descripción breve de la interpretación"
}}

**EJEMPLOS:**

Pregunta: "¿Qué reuniones tengo mañana por la tarde?"
Respuesta:
{{
    "es_temporal": true,
    "ventana_inicio": "2025-10-11T14:00:00",
    "ventana_fin": "2025-10-11T20:00:00",
    "confianza": 0.95,
    "explicacion": "Mañana (11/10) por la tarde (14:00-20:00)"
}}

Pregunta: "¿Cómo funciona el sistema de propagación?"
Respuesta:
{{
    "es_temporal": false,
    "ventana_inicio": null,
    "ventana_fin": null,
    "confianza": 0.90,
    "explicacion": "Consulta estructural sin referencia temporal"
}}

RESPONDE AHORA:"""


def _llamar_gemini(prompt: str) -> str:
    """Llama a Google Gemini con configuración optimizada"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        generation_config = {
            'temperature': 0.1,  # Baja temperatura para respuestas consistentes
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 500,
        }
        
        response = model.generate_content(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
        
    except Exception as e:
        raise Exception(f"Error llamando a Gemini: {str(e)}")


def _parsear_respuesta(respuesta: str, factor_base: float, momento: datetime) -> Dict:
    """Parsea y valida respuesta del LLM"""
    try:
        # Limpiar respuesta (a veces viene con markdown)
        respuesta_limpia = respuesta.strip()
        
        # Extraer JSON (puede venir con ```json o sin)
        if '```json' in respuesta_limpia:
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', respuesta_limpia, re.DOTALL)
            if json_match:
                respuesta_limpia = json_match.group(1)
        elif '```' in respuesta_limpia:
            json_match = re.search(r'```\s*(\{.*?\})\s*```', respuesta_limpia, re.DOTALL)
            if json_match:
                respuesta_limpia = json_match.group(1)
        else:
            # Buscar JSON directo
            json_match = re.search(r'\{.*\}', respuesta_limpia, re.DOTALL)
            if json_match:
                respuesta_limpia = json_match.group()
        
        # Parsear JSON
        datos = json.loads(respuesta_limpia)
        
        # Validar estructura
        es_temporal = datos.get('es_temporal', False)
        confianza = float(datos.get('confianza', 0.5))
        
        # ✅ CLASIFICAR INTENCIÓN SEGÚN ESTÁNDARES DEL SISTEMA
        if es_temporal:
            # Detectar si es MIXTA (temporal + semántica)
            # Si confianza baja, probablemente tiene componentes mixtos
            if confianza < 0.8:
                intencion = 'MIXTA'
            else:
                intencion = 'TEMPORAL'
            
            # Factor de refuerzo: mantener base (se amplifica en fórmula)
            factor_refuerzo = factor_base
        else:
            # Consulta estructural/semántica pura
            intencion = 'ESTRUCTURAL'
            factor_refuerzo = factor_base
        
        # Logging para debugging
        print(f"🧠 LLM Análisis: es_temporal={es_temporal}, intencion='{intencion}', confianza={confianza:.2f}, factor={factor_refuerzo}")
        
        # Construir resultado
        resultado = {
            'es_temporal': es_temporal,
            'intencion_temporal': intencion,  # ← AHORA ES "TEMPORAL", "ESTRUCTURAL" o "MIXTA"
            'confianza': confianza,
            'factor_refuerzo_temporal': factor_refuerzo,
            'momento_consulta': momento.isoformat(),
            'explicacion': datos.get('explicacion', 'Sin explicación'),
        }
        
        # Agregar ventana temporal si existe
        if es_temporal:
            ventana_inicio = datos.get('ventana_inicio')
            ventana_fin = datos.get('ventana_fin')
            
            resultado['ventana_temporal'] = {
                'inicio': ventana_inicio,
                'fin': ventana_fin
            }
            resultado['timestamp_referencia'] = ventana_inicio
        else:
            resultado['ventana_temporal'] = None
            resultado['timestamp_referencia'] = None
        
        return resultado
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Error parseando JSON del LLM: {e}")
        print(f"Respuesta recibida: {respuesta[:200]}...")
        raise Exception(f"Respuesta del LLM no es JSON válido")
    except Exception as e:
        raise Exception(f"Error procesando respuesta: {str(e)}")


def _crear_resultado_fallback(factor_base: float, momento: datetime, error_msg: str) -> Dict:
    """Crea resultado seguro en caso de error"""
    return {
        'es_temporal': False,
        'intencion_temporal': 'ESTRUCTURAL',  # ✅ Cambiar de 'nula' a 'ESTRUCTURAL'
        'confianza': 0.0,
        'factor_refuerzo_temporal': factor_base,
        'momento_consulta': momento.isoformat(),
        'explicacion': f'Error en análisis: {error_msg}',
        'ventana_temporal': None,
        'timestamp_referencia': None
    }