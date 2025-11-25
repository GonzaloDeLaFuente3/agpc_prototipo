# agent/temporal_llm_parser.py
import json
import re
import os
from datetime import datetime
from typing import Dict, Optional
import google.generativeai as genai

# Configurar Gemini con API key 
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDcCbQs_swG7s41Q0cjmk_ESfyMjg4hfmU")
genai.configure(api_key=GEMINI_API_KEY)


def analizar_temporalidad_con_llm(
    pregunta: str,
    momento_consulta: Optional[datetime] = None,
    factor_base: float = 1.5
) -> Dict:
    """
    Analiza temporalidad usando Google Gemini
        pregunta: Pregunta del usuario
        momento_consulta: Momento de la consulta (default: ahora)
        factor_base: Factor de refuerzo base configurado
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
        print(f" Error en análisis temporal LLM: {e}")
        # Fallback seguro
        return _crear_resultado_fallback(factor_base, momento_consulta, str(e))


def _construir_prompt(pregunta: str, momento: datetime) -> str:
    """Construye prompt  para Gemini"""
    
    # Información contextual
    dia_semana_es = {
        'Monday': 'lunes', 'Tuesday': 'martes', 'Wednesday': 'miércoles',
        'Thursday': 'jueves', 'Friday': 'viernes', 'Saturday': 'sábado', 'Sunday': 'domingo'
    }
    dia_semana = dia_semana_es.get(momento.strftime('%A'), momento.strftime('%A'))
    fecha_actual = momento.strftime('%Y-%m-%d %H:%M')
    
    return f"""Eres un clasificador de intención temporal extremadamente CONSERVADOR.

**PREGUNTA:** "{pregunta}"
**MOMENTO ACTUAL:** {fecha_actual} ({dia_semana})

---

**REGLA CRÍTICA #1:** Solo clasifica como TEMPORAL si la pregunta contiene AL MENOS UNA de estas palabras/frases:

**Palabras temporales absolutas:**
- Hoy, ayer, mañana, anteayer, pasado mañana
- Esta semana, este mes, este año, este trimestre
- Semana pasada, mes pasado, año pasado
- Próxima semana, próximo mes, próximo año

**Fechas específicas:**
- "enero 2023", "el 15 de marzo", "año 2024"
- "el lunes", "el martes" (días específicos)

**Períodos con números:**
- "últimos 3 días", "hace 2 semanas", "en los próximos 5 meses"

**Preguntas sobre programación:**
- "¿cuándo es mi reunión?", "¿qué tengo programado para...?"

---

**REGLA CRÍTICA #2:** SIEMPRE clasifica como ESTRUCTURAL si:

1. **Busca un concepto o definición:** "Amparo por mora administrativa", "¿Qué es un despido?"
2. **Busca casos SIN mencionar tiempo:** "Casos de acoso laboral", "Precedentes de contratos"
3. **Busca procedimientos:** "¿Cómo se calcula?", "¿Cuál es el proceso?"
4. **NO tiene ninguna palabra temporal de la lista anterior**

---

**EJEMPLOS DE CLASIFICACIÓN:**

❌ INCORRECTO:
Pregunta: "Amparo por mora administrativa"
Clasificación: TEMPORAL ← ERROR!
Razón: No tiene palabras temporales, es un concepto

✅ CORRECTO:
Pregunta: "Amparo por mora administrativa"
Clasificación: ESTRUCTURAL
Razón: Busca concepto legal, sin referencia temporal

✅ CORRECTO:
Pregunta: "¿Qué casos de amparo tuvimos ayer?"
Clasificación: TEMPORAL
Razón: Contiene "ayer" (palabra temporal absoluta)

✅ CORRECTO:
Pregunta: "Casos de despido sin causa"
Clasificación: ESTRUCTURAL
Razón: Busca casos en general, sin restricción temporal

✅ CORRECTO:
Pregunta: "¿Qué reuniones tengo mañana?"
Clasificación: TEMPORAL
Razón: Contiene "mañana" (palabra temporal absoluta)

---

**EN CASO DE DUDA → SIEMPRE ESTRUCTURAL**

---

**REGLAS DE INTERPRETACIÓN TEMPORAL (solo para consultas TEMPORALES):**
- "mañana" = día siguiente completo (00:00:00 a 23:59:59)
- "ayer" = día anterior completo
- "hoy" = día actual completo
- "esta semana" = desde lunes hasta domingo de esta semana
- "mes pasado" = primer día a último día del mes anterior

---

Responde ÚNICAMENTE con un JSON válido en este formato:
{{
    "es_temporal": true o false,
    "confianza": 0.0-1.0,
    "ventana_inicio": "YYYY-MM-DDTHH:MM:SS" o null,
    "ventana_fin": "YYYY-MM-DDTHH:MM:SS" o null,
    "explicacion": "Breve justificación de la clasificación"
}}

RESPONDE AHORA:"""


def _llamar_gemini(prompt: str) -> str:
    """Llama a Google Gemini con configuración """
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
        
        #  CLASIFICAR INTENCIÓN SEGÚN ESTÁNDARES DEL SISTEMA
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
        print(f"\n LLM ANÁLISIS COMPLETO:")
        print(f"   ├─ es_temporal: {es_temporal}")
        print(f"   ├─ intencion: '{intencion}'")
        print(f"   ├─ confianza: {confianza:.2f}")
        print(f"   ├─ factor_refuerzo: {factor_refuerzo}")
        if es_temporal:
            print(f"   ├─ ventana_temporal: {datos.get('ventana_inicio')} → {datos.get('ventana_fin')}")
        else:
            print(f"   ├─ ventana_temporal: NO (consulta estructural)")
        print(f"   └─ explicacion: {datos.get('explicacion', 'N/A')[:80]}...")  
              
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
        print(f" Error parseando JSON del LLM: {e}")
        print(f"Respuesta recibida: {respuesta[:200]}...")
        raise Exception(f"Respuesta del LLM no es JSON válido")
    except Exception as e:
        raise Exception(f"Error procesando respuesta: {str(e)}")


def _crear_resultado_fallback(factor_base: float, momento: datetime, error_msg: str) -> Dict:
    """Crea resultado seguro en caso de error"""
    return {
        'es_temporal': False,
        'intencion_temporal': 'ESTRUCTURAL', 
        'confianza': 0.0,
        'factor_refuerzo_temporal': factor_base,
        'momento_consulta': momento.isoformat(),
        'explicacion': f'Error en análisis: {error_msg}',
        'ventana_temporal': None,
        'timestamp_referencia': None
    }