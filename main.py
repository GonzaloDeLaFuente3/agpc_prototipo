# main.py
import json
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
from agent import grafo, responder
from agent.semantica import indexar_documento, buscar_similares
from agent.query_analyzer import analizar_intencion_temporal
from datetime import datetime
from agent.dataset_loader import DatasetLoader
from fastapi import UploadFile, File

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
    """Agrega un nuevo contexto al grafo con prevención de duplicados."""
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

@app.get("/preguntar-con-propagacion/")
def preguntar_con_propagacion(pregunta: str, usar_propagacion: bool = True, max_pasos: int = 2,
                             factor_decaimiento: float = None, umbral_activacion: float = None):
    """Responde a una pregunta usando propagación de activación."""
    pregunta = pregunta.strip()
    momento_consulta = datetime.now()
    todos_contextos = grafo.obtener_todos()

    if not todos_contextos:
        return {
            "respuesta": "[ERROR] No hay contextos almacenados en el sistema",
            "contextos_utilizados": [],
            "subgrafo": {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}},
            "momento_consulta": momento_consulta.isoformat(),
            "propagacion": {"error": "Sin contextos base"}
        }

    try:
        # Análisis con propagación
        analisis_completo = grafo.analizar_consulta_con_propagacion(
            pregunta, momento_consulta, usar_propagacion, max_pasos,
            factor_decaimiento, umbral_activacion  
        )
        
        analisis_intencion = analisis_completo["analisis_intencion"]
        ids_similares = analisis_completo["contextos_recuperados"]
        arbol = analisis_completo["arbol_consulta"]
        estrategia = analisis_completo["estrategia_aplicada"]
        info_propagacion = analisis_completo.get("propagacion", {})
        
    except Exception as e:
        print(f"Error en análisis con propagación: {e}")
        # Fallback a método básico
        ids_similares = buscar_similares(pregunta, k=5)
        analisis_intencion = {"error": f"Error en análisis: {str(e)}"}
        estrategia = {"error": "Estrategia fallback aplicada"}
        arbol = {"nodes": [], "edges": [], "meta": {"error": "Error en construcción"}}
        info_propagacion = {"error": str(e)}

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
            
            # Marcar si fue encontrado por propagación
            encontrado_por = None
            if info_propagacion.get('solo_por_propagacion') and id_ctx in info_propagacion['solo_por_propagacion']:
                encontrado_por = 'propagacion'
                info_ctx['activacion'] = 'encontrado por propagación'
            elif info_propagacion.get('contextos_directos') and id_ctx in info_propagacion['contextos_directos']:
                encontrado_por = 'busqueda_directa'
            
            if encontrado_por:
                info_ctx['encontrado_por'] = encontrado_por
            
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
            "momento_consulta": momento_consulta.isoformat(),
            "propagacion": info_propagacion
        }

    # Generar respuesta con IA
    respuesta = responder.responder_con_ia(pregunta, contextos_relevantes)

    # Información adicional mejorada
    titulos_utilizados = [c["titulo"] for c in contextos_utilizados_info]
    temporales = [c for c in contextos_utilizados_info if c.get("es_temporal")]
    por_propagacion = [c for c in contextos_utilizados_info if c.get("encontrado_por") == "propagacion"]
    
    # Información de estrategia aplicada
    info_estrategia = ""
    if estrategia.get("ventana_temporal_aplicada"):
        info_estrategia += " [Filtro temporal aplicado]"
    if estrategia.get("contextos_filtrados_temporalmente", 0) > 0:
        info_estrategia += f" ({estrategia['contextos_filtrados_temporalmente']} contextos filtrados por tiempo)"
    
    if usar_propagacion and info_propagacion.get('total_nodos_alcanzados', 0) > 0:
        info_estrategia += f" [Propagación: +{len(por_propagacion)} contextos indirectos]"
    
    # Agregar contexto usado a la respuesta
    info_temporal = f" ({len(temporales)} temporales)" if temporales else ""
    info_propagacion_resp = f" (+{len(por_propagacion)} por propagación)" if por_propagacion else ""
    momento_str = momento_consulta.strftime("%d/%m %H:%M")
    
    respuesta_completa = f"{respuesta}\n\n📚 Contextos: {', '.join(titulos_utilizados)}{info_temporal}{info_propagacion_resp}\n🕐 Consultado: {momento_str}{info_estrategia}"

    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info,
        "subgrafo": arbol,
        "analisis_intencion": analisis_intencion,
        "estrategia_aplicada": estrategia,
        "momento_consulta": momento_consulta.isoformat(),
        "propagacion": info_propagacion
    }

@app.post("/configurar-propagacion/")
def configurar_parametros_propagacion_endpoint(factor_decaimiento: float = None, umbral_activacion: float = None):
    """Configura parámetros del algoritmo de propagación."""
    resultado = grafo.configurar_parametros_propagacion(factor_decaimiento, umbral_activacion)
    return resultado

# TAMBIÉN MANTENER el endpoint de estado:
@app.get("/estado-propagacion/")
def obtener_estado_propagacion_endpoint():
    """Obtiene el estado actual del sistema de propagación."""
    return grafo.obtener_estado_propagacion()
    
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

# ENDPOINTS PARA CONVERSACIONES

class EntradaConversacion(BaseModel):
    titulo: str
    contenido: str
    fecha: Optional[str] = None
    participantes: Optional[List[str]] = None
    metadata: Optional[dict] = None

@app.post("/conversacion/")
def agregar_conversacion_endpoint(entrada: EntradaConversacion):
    """Agrega una conversación completa y la fragmenta automáticamente."""
    try:
        resultado = grafo.agregar_conversacion(
            titulo=entrada.titulo,
            contenido=entrada.contenido,
            fecha=entrada.fecha,
            participantes=entrada.participantes,
            metadata=entrada.metadata
        )
        return {
            "status": "conversacion_agregada",
            **resultado
        }
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}

@app.get("/conversaciones/")
def obtener_conversaciones():
    """Obtiene todas las conversaciones."""
    return grafo.obtener_conversaciones()

@app.get("/conversacion/{conversacion_id}/fragmentos")
def obtener_fragmentos_conversacion(conversacion_id: str):
    """Obtiene fragmentos de una conversación específica."""
    return grafo.obtener_fragmentos_de_conversacion(conversacion_id)

# ENDPOINTS PARA CARGA MASIVA DE DATASETS
class DatasetUpload(BaseModel):
    dataset: dict
    sobrescribir: bool = False

@app.post("/dataset/validar/")
def validar_dataset(dataset: dict):
    """Valida el formato de un dataset sin procesarlo."""
    loader = DatasetLoader()
    es_valido, errores = loader.validar_formato(dataset)
    
    return {
        "valido": es_valido,
        "errores": errores,
        "total_conversaciones": len(dataset.get('conversaciones', [])),
        "dominio": dataset.get('dominio', 'No especificado')
    }

@app.post("/dataset/upload/")
async def upload_dataset_file(file: UploadFile = File(...), sobrescribir: bool = False):
    """Sube y procesa un archivo JSON de dataset."""
    if not file.filename.endswith('.json'):
        return {"status": "error", "mensaje": "Solo se permiten archivos .json"}
    
    try:
        contenido = await file.read()
        dataset = json.loads(contenido.decode('utf-8'))
        
        loader = DatasetLoader()
        estadisticas = loader.procesar_dataset(dataset, sobrescribir)
        
        return {
            "status": "archivo_procesado",
            "archivo": file.filename,
            "estadisticas": estadisticas
        }
        
    except json.JSONDecodeError:
        return {"status": "error", "mensaje": "Archivo JSON inválido"}
    except Exception as e:
        return {"status": "error", "mensaje": str(e)}
    
#ENDPOINTS PARA VISUALIZACIÓN DOBLE NIVEL
@app.get("/grafo/macro/conversaciones/")
def exportar_grafo_macro():
    """Vista macro: conversaciones como nodos, relaciones agregadas."""
    return grafo.exportar_grafo_macro_conversaciones()

@app.get("/grafo/micro/fragmentos/")
def exportar_grafo_micro_completo():
    """Vista micro: todos los fragmentos individuales."""
    return grafo.exportar_grafo_micro_fragmentos()

@app.get("/grafo/micro/conversacion/{conversacion_id}")
def exportar_grafo_micro_conversacion(conversacion_id: str):
    """Vista micro filtrada: solo fragmentos de una conversación específica."""
    return grafo.exportar_grafo_micro_fragmentos(conversacion_id)

@app.get("/estadisticas/doble-nivel/")
def obtener_estadisticas_doble_nivel():
    """Estadísticas comparativas entre vista macro y micro."""
    return grafo.obtener_estadisticas_doble_nivel()

@app.get("/estadisticas-actualizacion/")
def obtener_estadisticas_actualizacion():
    """Obtiene estadísticas básicas del sistema de actualización incremental."""
    try:
        stats = grafo.obtener_estadisticas()
        
        return {
            "status": "success",
            "estadisticas": {
                "total_nodos": stats["total_contextos"],
                "total_relaciones": stats["total_relaciones"],
                "contextos_temporales": stats.get("contextos_temporales", 0),
                "contextos_atemporales": stats.get("contextos_atemporales", 0),
                "tipos_contexto": stats.get("tipos_contexto", {}),
                "actualizacion_incremental": "habilitada",
                "umbral_similitud": 0.1,
                "mensaje": f"Sistema funcionando con {stats['total_contextos']} nodos y {stats['total_relaciones']} relaciones"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error", 
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Servir archivos estáticos
os.makedirs("static", exist_ok=True)
app.mount("/", StaticFiles(directory="static", html=True), name="static")