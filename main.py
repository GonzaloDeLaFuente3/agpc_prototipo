# main.py - PASO 1: API con soporte temporal
from fastapi import FastAPI
from agent import grafo
from pydantic import BaseModel
from typing import List, Optional
from agent import responder
from fastapi.staticfiles import StaticFiles
import os
from agent.semantica import indexar_documento, buscar_similares

grafo.cargar_desde_disco()

# Reindexar lo que ya está guardado
for id, datos in grafo.obtener_todos().items():
    indexar_documento(id, datos["texto"])

app = FastAPI()

class EntradaContexto(BaseModel):
    titulo: str
    texto: str
    es_temporal: Optional[bool] = False  # NUEVO: campo para indicar si es temporal

@app.post("/contexto/")
def agregar_contexto(entrada: EntradaContexto):
    nuevo_id = grafo.agregar_contexto(entrada.titulo, entrada.texto, entrada.es_temporal)
    return {
        "status": "agregado", 
        "id": nuevo_id,
        "es_temporal": entrada.es_temporal
    }

@app.get("/contexto/")
def obtener_contextos():
    return grafo.obtener_todos()

@app.get("/preguntar/")
def preguntar(pregunta: str):
    pregunta = pregunta.strip()
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}}
        }

    # Recuperar contextos relevantes (por embeddings)
    ids_similares = buscar_similares(pregunta, k=5)

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
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No se encontraron contextos relevantes"}}
        }

    # Llamada a la IA
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    info_temporal = f" (🕒 {len(temporales)} temporales)" if temporales else ""
    respuesta_completa = f"{respuesta}\n\n📚 Contextos utilizados: {', '.join(titulos_utilizados)}{info_temporal}"

    # Construcción del subgrafo efímero (NO se guarda en grafo principal)
    try:
        arbol = grafo.construir_arbol_consulta(pregunta, list(contextos_relevantes.keys()))
        print(f"Subgrafo construido: {len(arbol.get('nodes', []))} nodos, {len(arbol.get('edges', []))} aristas")
    except Exception as e:
        print(f"Error construyendo subgrafo: {e}")
        arbol = {"nodes": [], "edges": [], "meta": {"error": str(e)}}

    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "debug": {
            "ids_similares": ids_similares,
            "contextos_encontrados": len(contextos_relevantes),
            "subgrafo_valido": len(arbol.get('nodes', [])) > 0
        }
    }

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