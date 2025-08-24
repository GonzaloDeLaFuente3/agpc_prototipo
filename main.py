# main.py - Optimizado
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os

from agent import grafo, responder
from agent.semantica import indexar_documento, buscar_similares
from agent.query_analyzer import analizar_intencion_temporal

# Inicialización
grafo.cargar_desde_disco()

# Reindexar contextos existentes
for id, datos in grafo.obtener_todos().items():
    indexar_documento(id, datos["texto"])

app = FastAPI()

class EntradaContexto(BaseModel):
    titulo: str
    texto: str
    es_temporal: Optional[bool] = None
    referencia_temporal: Optional[str] = None

@app.post("/contexto/")
def agregar_contexto(entrada: EntradaContexto):
    """Agrega un nuevo contexto al grafo."""
    nuevo_id = grafo.agregar_contexto(
        entrada.titulo, 
        entrada.texto, 
        entrada.es_temporal,
        entrada.referencia_temporal
    )
    
    contexto_creado = grafo.metadatos_contextos[nuevo_id]
    
    return {
        "status": "agregado", 
        "id": nuevo_id,
        "es_temporal": contexto_creado.get("es_temporal", False)
    }

@app.get("/contexto/")
def obtener_contextos():
    """Obtiene todos los contextos."""
    return grafo.obtener_todos()

@app.get("/preguntar/")
def preguntar(pregunta: str):
    """Responde a una pregunta usando el contexto del grafo."""
    pregunta = pregunta.strip()
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}}
        }

    try:
        # Análisis completo con intención temporal
        analisis_completo = grafo.analizar_consulta_completa(pregunta)
        analisis_intencion = analisis_completo["analisis_intencion"]
        ids_similares = analisis_completo["contextos_recuperados"]
        arbol = analisis_completo["arbol_consulta"]
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        # Fallback a búsqueda básica
        ids_similares = buscar_similares(pregunta, k=5)
        analisis_intencion = {"error": f"Error en análisis: {str(e)}"}
        arbol = {"nodes": [], "edges": [], "meta": {"error": "Error en construcción"}}

    # Recopilar contextos relevantes
    contextos_relevantes = {}
    contextos_utilizados_info = []
    
    for id_ctx in ids_similares:
        if id_ctx in todos_contextos:
            contextos_relevantes[id_ctx] = todos_contextos[id_ctx]
            ctx = todos_contextos[id_ctx]
            contextos_utilizados_info.append({
                "titulo": ctx["titulo"],
                "id": id_ctx,
                "es_temporal": ctx.get("es_temporal", False)
            })

    if not contextos_relevantes:
        return {
            "respuesta": "[ERROR] No se encontraron contextos relevantes",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "Sin contextos relevantes"}},
            "analisis_intencion": analisis_intencion
        }

    # Generar respuesta con IA
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    # Información adicional
    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    
    # Agregar contexto usado a la respuesta
    info_temporal = f" ({len(temporales)} temporales)" if temporales else ""
    respuesta_completa = f"{respuesta}\n\n📚 Contextos: {', '.join(titulos_utilizados)}{info_temporal}"

    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "analisis_intencion": analisis_intencion
    }

@app.get("/buscar/")
def buscar_por_texto(texto: str):
    """Busca contextos por similitud semántica."""
    texto = texto.strip()
    ids_similares = buscar_similares(texto)
    todos = grafo.obtener_todos()
    return {id: todos[id] for id in ids_similares if id in todos}

@app.get("/estadisticas/")
def obtener_estadisticas():
    """Obtiene estadísticas del grafo."""
    return grafo.obtener_estadisticas()

@app.get("/grafo/visualizacion/")
def exportar_para_visualizacion():
    """Exporta el grafo para visualización."""
    return grafo.exportar_grafo_para_visualizacion()

@app.get("/query/analizar/")
def analizar_query(pregunta: str):
    """Analiza la intención temporal de una pregunta."""
    return analizar_intencion_temporal(pregunta)

# Servir archivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")