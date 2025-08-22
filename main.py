# main.py - PASO 1: API con soporte temporal
from fastapi import FastAPI
from agent import grafo
from pydantic import BaseModel
from typing import List, Optional
from agent import responder
from fastapi.staticfiles import StaticFiles
import os
from agent.semantica import indexar_documento, buscar_similares
from agent.query_analyzer import analizar_intencion_temporal

grafo.cargar_desde_disco()

# Reindexar lo que ya está guardado
for id, datos in grafo.obtener_todos().items():
    indexar_documento(id, datos["texto"])

app = FastAPI()

class EntradaContexto(BaseModel):
    titulo: str
    texto: str
    es_temporal: Optional[bool] = None  # None = auto-detectar, True/False = forzar
    referencia_temporal: Optional[str] = None

@app.post("/contexto/")
def agregar_contexto(entrada: EntradaContexto):
    nuevo_id = grafo.agregar_contexto(
        entrada.titulo, 
        entrada.texto, 
        entrada.es_temporal,  # Puede ser None para auto-detección
        entrada.referencia_temporal
    )
    
    # Información adicional en la respuesta
    contexto_creado = grafo.metadatos_contextos[nuevo_id]
    info_temporal = {}
    
    if contexto_creado.get("es_temporal", False):
        info_temporal = grafo.obtener_info_temporal(nuevo_id)
        info_temporal["fue_autodetectado"] = contexto_creado.get("deteccion_automatica", False)
    
    return {
        "status": "agregado", 
        "id": nuevo_id,
        "es_temporal": contexto_creado.get("es_temporal", False),
        "fue_autodetectado": contexto_creado.get("deteccion_automatica", False),
        "info_temporal": info_temporal
    }

#Previsualización de detección
@app.post("/contexto/previsualizar/")
def previsualizar_contexto(entrada: EntradaContexto):
    """Previsualiza qué detectará el sistema sin guardar"""
    if not entrada.titulo or not entrada.texto:
        return {"error": "Título y texto son requeridos"}
    
    preview = grafo.previsualizar_deteccion_temporal(entrada.titulo, entrada.texto)
    
    # Agregar información adicional
    preview["modo"] = "auto_deteccion" if entrada.es_temporal is None else "manual"
    preview["sera_temporal_final"] = preview["sera_temporal"] if entrada.es_temporal is None else entrada.es_temporal
    
    return preview

# NUEVO ENDPOINT: Información temporal de un contexto
@app.get("/contexto/{id_contexto}/temporal/")
def obtener_info_temporal_contexto(id_contexto: str):
    return grafo.obtener_info_temporal(id_contexto)

@app.get("/contexto/")
def obtener_contextos():
    return grafo.obtener_todos()

# NUEVO ENDPOINT: Testing del parser temporal
@app.get("/temporal/test/")
def test_parser_temporal(referencia: str):
    from agent.temporal_parser import parsear_referencia_temporal
    timestamp, tipo = parsear_referencia_temporal(referencia)
    
    resultado = {
        "referencia_original": referencia,
        "timestamp": timestamp,
        "tipo_referencia": tipo,
        "parseado_exitoso": timestamp is not None
    }
    
    if timestamp:
        from datetime import datetime
        fecha_obj = datetime.fromisoformat(timestamp)
        resultado["fecha_legible"] = fecha_obj.strftime("%d/%m/%Y %H:%M")
        resultado["es_futuro"] = fecha_obj > datetime.now()
        resultado["dias_diferencia"] = (fecha_obj - datetime.now()).days
    
    return resultado

@app.get("/preguntar/")
def preguntar(pregunta: str):
    pregunta = pregunta.strip()
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}},
            "analisis_intencion": {"error": "Sin contextos disponibles"}
        }

    # NUEVO: Análisis completo de la consulta con intención temporal
    try:
        analisis_completo = grafo.analizar_consulta_completa(pregunta)
        analisis_intencion = analisis_completo["analisis_intencion"]
        ids_similares = analisis_completo["contextos_recuperados"]
        arbol = analisis_completo["arbol_consulta"]
        estrategia = analisis_completo["estrategia_aplicada"]
        
    except Exception as e:
        print(f"Error en análisis completo: {e}")
        # Fallback al método anterior
        ids_similares = buscar_similares(pregunta, k=5)
        analisis_intencion = {"error": f"Error en análisis: {str(e)}"}
        estrategia = {"error": "Usando fallback"}
        arbol = {"nodes": [], "edges": [], "meta": {"error": "Error en construcción"}}

    contextos_relevantes = {}
    contextos_utilizados_info = []
    
    for id_ctx in ids_similares:
        if id_ctx in todos_contextos:
            contextos_relevantes[id_ctx] = todos_contextos[id_ctx]
            ctx = todos_contextos[id_ctx]
            contextos_utilizados_info.append({
                "titulo": ctx["titulo"],
                "id": id_ctx,
                "es_temporal": ctx.get("es_temporal", False),
                "timestamp": ctx.get("timestamp")
            })

    if not contextos_relevantes:
        return {
            "respuesta": "[ERROR] No se encontraron contextos relevantes para la pregunta",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No se encontraron contextos relevantes"}},
            "analisis_intencion": analisis_intencion
        }

    # Llamada a la IA (sin cambios)
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    # NUEVA: Información enriquecida sobre la estrategia aplicada
    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    
    # Construir mensaje con información de estrategia
    info_estrategia = ""
    if "analisis_intencion" in locals() and "intencion_temporal" in analisis_intencion:
        intencion = analisis_intencion["intencion_temporal"]
        factor = analisis_intencion.get("factor_refuerzo_temporal", 1.0)
        
        if intencion == "fuerte":
            info_estrategia = f" 🕒 Consulta temporal (factor: {factor:.1f}x)"
        elif intencion == "nula":
            info_estrategia = f" 📋 Consulta estructural (factor: {factor:.1f}x)"
        elif intencion == "media":
            info_estrategia = f" ⚡ Consulta mixta (factor: {factor:.1f}x)"
    
    info_temporal = f" ({len(temporales)} temporales)" if temporales else ""
    respuesta_completa = f"{respuesta}\n\n📚 Contextos: {', '.join(titulos_utilizados)}{info_temporal}{info_estrategia}"

    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "analisis_intencion": analisis_intencion,  # NUEVO
        "estrategia_aplicada": estrategia,  # NUEVO
        "debug": {
            "ids_similares": ids_similares,
            "contextos_encontrados": len(contextos_relevantes),
            "subgrafo_valido": len(arbol.get('nodes', [])) > 0,
            "intencion_temporal": analisis_intencion.get("intencion_temporal", "error"),
            "factor_refuerzo": analisis_intencion.get("factor_refuerzo_temporal", 1.0)
        }
    }

# NUEVO ENDPOINT: Solo análisis de intención (para testing)
@app.get("/query/analizar/")
def analizar_query(pregunta: str):
    """Analiza solo la intención temporal de una pregunta sin ejecutarla"""
    return analizar_intencion_temporal(pregunta)

# NUEVO ENDPOINT: Análisis completo sin respuesta de IA
@app.get("/query/analisis-completo/")
def analisis_completo_query(pregunta: str):
    """Análisis completo de consulta sin llamar a la IA"""
    try:
        return grafo.analizar_consulta_completa(pregunta)
    except Exception as e:
        return {"error": str(e)}

@app.get("/buscar/")
def buscar_por_texto(texto: str):
    from agent import grafo
    from agent.semantica import buscar_similares

    texto = texto.strip()
    ids_similares = buscar_similares(texto)
    todos = grafo.obtener_todos()
    resultados = {id: todos[id] for id in ids_similares if id in todos}
    return resultados

@app.get("/estadisticas/")
def obtener_estadisticas():
    return grafo.obtener_estadisticas()

@app.get("/grafo/centrales/")
def obtener_contextos_centrales(k: int = 5):
    """Obtiene los contextos más centrales del grafo"""
    return grafo.obtener_contextos_centrales(k)

@app.get("/grafo/visualizacion/")
def exportar_para_visualizacion():
    """Exporta el grafo optimizado para visualización"""
    return grafo.exportar_grafo_para_visualizacion()

# NUEVO: Endpoint para actualizar pesos temporales manualmente
@app.post("/grafo/actualizar-temporal/")
def actualizar_pesos_temporales():
    """Actualiza todos los pesos temporales en el grafo"""
    resultado = grafo.actualizar_pesos_temporales()
    return resultado

os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")