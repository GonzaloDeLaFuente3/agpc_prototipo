# main.py - Optimizado
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os

from agent import grafo, responder
from agent.semantica import indexar_documento, buscar_similares
from agent.query_analyzer import analizar_intencion_temporal
from datetime import datetime

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
    """Responde a una pregunta considerando momento de consulta."""
    pregunta = pregunta.strip()
    momento_consulta = datetime.now()  # Capturar momento exacto
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}},
            "momento_consulta": momento_consulta.isoformat()
        }

    try:
        # Análisis completo con momento de consulta
        analisis_completo = grafo.analizar_consulta_completa(pregunta, momento_consulta)
        analisis_intencion = analisis_completo["analisis_intencion"]
        ids_similares = analisis_completo["contextos_recuperados"]
        arbol = analisis_completo["arbol_consulta"]
        estrategia = analisis_completo["estrategia_aplicada"]
        
    except Exception as e:
        print(f"Error en análisis: {e}")
        # Fallback a búsqueda básica
        ids_similares = buscar_similares(pregunta, k=5)
        analisis_intencion = {"error": f"Error en análisis: {str(e)}"}
        estrategia = {"error": "Estrategia fallback aplicada"}
        arbol = {"nodes": [], "edges": [], "meta": {"error": "Error en construcción"}}

    # Recopilar contextos relevantes
    contextos_relevantes = {}
    contextos_utilizados_info = []
    
    for id_ctx in ids_similares:
        if id_ctx in todos_contextos:
            contextos_relevantes[id_ctx] = todos_contextos[id_ctx]
            ctx = todos_contextos[id_ctx]
            
            # Información extendida del contexto
            info_ctx = {
                "titulo": ctx["titulo"],
                "id": id_ctx,
                "es_temporal": ctx.get("es_temporal", False),
                "tipo_contexto": ctx.get("tipo_contexto", "general")
            }
            
            # Agregar información temporal si existe
            if ctx.get("timestamp"):
                fecha_ctx = datetime.fromisoformat(ctx["timestamp"])
                info_ctx["fecha_contexto"] = fecha_ctx.isoformat()
                
                # Diferencia temporal con momento consulta
                diff_seconds = (momento_consulta - fecha_ctx).total_seconds()
                diff_hours = diff_seconds / 3600
                
                if abs(diff_hours) < 24:
                    info_ctx["diferencia_temporal"] = f"{diff_hours:+.1f} horas"
                else:
                    diff_days = diff_hours / 24
                    info_ctx["diferencia_temporal"] = f"{diff_days:+.1f} días"
            
            contextos_utilizados_info.append(info_ctx)

    if not contextos_relevantes:
        return {
            "respuesta": "[ERROR] No se encontraron contextos relevantes",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "Sin contextos relevantes"}},
            "analisis_intencion": analisis_intencion,
            "momento_consulta": momento_consulta.isoformat()
        }

    # Generar respuesta con IA
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    # Información adicional mejorada
    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    
    # Información de estrategia aplicada
    info_estrategia = ""
    if estrategia.get("ventana_temporal_aplicada"):
        info_estrategia += " [Filtro temporal aplicado]"
    if estrategia.get("contextos_filtrados_temporalmente", 0) > 0:
        info_estrategia += f" ({estrategia['contextos_filtrados_temporalmente']} contextos filtrados por tiempo)"
    
    # Agregar contexto usado a la respuesta
    info_temporal = f" ({len(temporales)} temporales)" if temporales else ""
    momento_str = momento_consulta.strftime("%d/%m %H:%M")
    respuesta_completa = f"{respuesta}\n\n📚 Contextos: {', '.join(titulos_utilizados)}{info_temporal}\n🕐 Consultado: {momento_str}{info_estrategia}"

    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "analisis_intencion": analisis_intencion,
        "estrategia_aplicada": estrategia,
        "momento_consulta": momento_consulta.isoformat()
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