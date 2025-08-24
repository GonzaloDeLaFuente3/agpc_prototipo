# agent/grafo.py - Optimizado
import networkx as nx
import pickle
import json
import os
import uuid
import threading
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from agent.extractor import extraer_palabras_clave
from agent.semantica import indexar_documento
from agent.temporal_parser import extraer_referencias_del_texto, parsear_referencia_temporal
from agent.query_analyzer import analizar_intencion_temporal

# Archivos de persistencia
ARCHIVO_GRAFO = "data/grafo_contextos.pickle"
ARCHIVO_METADATOS = "data/contexto.json"

# Grafo y metadatos globales
grafo_contextos = nx.DiGraph()
metadatos_contextos = {}
_lock = threading.Lock()

def _calcular_similitud_semantica(claves_a: Set[str], claves_b: Set[str]) -> float:
    """Calcula similitud Jaccard entre dos conjuntos."""
    if not claves_a or not claves_b:
        return 0.0
    
    interseccion = len(claves_a & claves_b)
    union = len(claves_a | claves_b)
    return interseccion / union if union > 0 else 0.0

def _calcular_relevancia_temporal(fecha_a: str, fecha_b: str) -> float:
    """Calcula relevancia temporal con decaimiento exponencial."""
    if not fecha_a or not fecha_b:
        return 0.0
    
    try:
        dt_a = datetime.fromisoformat(fecha_a)
        dt_b = datetime.fromisoformat(fecha_b)
        
        diferencia_dias = abs((dt_a - dt_b).days)
        factor_decaimiento = 30  # 30 días
        relevancia = math.exp(-diferencia_dias / factor_decaimiento)
        
        return min(1.0, max(0.0, relevancia))
    except (ValueError, TypeError):
        return 0.0

def _recalcular_relaciones():
    """Recalcula todas las relaciones del grafo."""
    grafo_contextos.clear_edges()
    nodos = list(grafo_contextos.nodes())
    
    for i, nodo_a in enumerate(nodos):
        metadatos_a = metadatos_contextos.get(nodo_a, {})
        claves_a = set(metadatos_a.get("palabras_clave", []))
        fecha_a = metadatos_a.get("timestamp")
        
        for nodo_b in nodos[i+1:]:
            metadatos_b = metadatos_contextos.get(nodo_b, {})
            claves_b = set(metadatos_b.get("palabras_clave", []))
            fecha_b = metadatos_b.get("timestamp")
            
            similitud = _calcular_similitud_semantica(claves_a, claves_b)
            relevancia_temporal = _calcular_relevancia_temporal(fecha_a, fecha_b)
            peso_efectivo = similitud * (1 + relevancia_temporal)
            
            if similitud > 0.1:  # Umbral mínimo
                datos_arista = {
                    "peso_estructural": round(similitud, 3),
                    "relevancia_temporal": round(relevancia_temporal, 3),
                    "peso_efectivo": round(peso_efectivo, 3),
                    "tipo": "semantica_temporal" if (fecha_a and fecha_b) else "semantica"
                }
                
                grafo_contextos.add_edge(nodo_a, nodo_b, **datos_arista)
                grafo_contextos.add_edge(nodo_b, nodo_a, **datos_arista)

def _guardar_grafo():
    """Guarda el grafo en disco de forma thread-safe."""
    with _lock:
        os.makedirs("data", exist_ok=True)
        
        with open(ARCHIVO_GRAFO, 'wb') as f:
            pickle.dump(grafo_contextos, f)
        
        with open(ARCHIVO_METADATOS, 'w', encoding='utf-8') as f:
            json.dump(metadatos_contextos, f, ensure_ascii=False, indent=2)

def cargar_desde_disco():
    """Carga el grafo desde disco."""
    global grafo_contextos, metadatos_contextos
    
    if os.path.exists(ARCHIVO_GRAFO):
        with open(ARCHIVO_GRAFO, 'rb') as f:
            grafo_contextos = pickle.load(f)
    else:
        grafo_contextos = nx.DiGraph()
    
    if os.path.exists(ARCHIVO_METADATOS):
        with open(ARCHIVO_METADATOS, 'r', encoding='utf-8') as f:
            metadatos_contextos = json.load(f)
    else:
        metadatos_contextos = {}

def agregar_contexto(titulo: str, texto: str, es_temporal: bool = None, referencia_temporal: str = None) -> str:
    """Agrega un nuevo contexto con detección temporal automática."""
    id_contexto = str(uuid.uuid4())
    palabras_clave = extraer_palabras_clave(texto)
    
    grafo_contextos.add_node(id_contexto, titulo=titulo)
    
    # Detección temporal
    texto_completo = f"{titulo} {texto}"
    referencias_encontradas = extraer_referencias_del_texto(texto_completo)
    
    es_temporal_final = len(referencias_encontradas) > 0 if es_temporal is None else es_temporal
    
    # Metadatos base
    metadatos = {
        "titulo": titulo,
        "texto": texto,
        "palabras_clave": palabras_clave,
        "created_at": datetime.now().isoformat(),
        "es_temporal": es_temporal_final,
    }
    
    # Procesamiento temporal
    if es_temporal_final:
        timestamp_usado = None
        
        if referencia_temporal:
            timestamp_usado, _ = parsear_referencia_temporal(referencia_temporal)
        elif referencias_encontradas:
            _, timestamp_usado, _ = referencias_encontradas[0]
        
        if timestamp_usado:
            metadatos["timestamp"] = timestamp_usado
        else:
            metadatos["timestamp"] = datetime.now().isoformat()
    
    metadatos_contextos[id_contexto] = metadatos
    
    # Recalcular y guardar
    _recalcular_relaciones()
    _guardar_grafo()
    
    # Indexar para búsqueda semántica
    indexar_documento(id_contexto, texto)
    
    return id_contexto

def obtener_todos() -> Dict:
    """Obtiene todos los contextos."""
    return metadatos_contextos

def obtener_estadisticas() -> Dict:
    """Obtiene estadísticas básicas del grafo."""
    stats = {
        "total_contextos": grafo_contextos.number_of_nodes(),
        "total_relaciones": grafo_contextos.number_of_edges(),
    }
    
    # Contar temporales vs atemporales
    temporales = sum(1 for ctx in metadatos_contextos.values() 
                    if ctx.get("es_temporal", False))
    stats["contextos_temporales"] = temporales
    stats["contextos_atemporales"] = stats["total_contextos"] - temporales
    
    return stats

def exportar_grafo_para_visualizacion() -> Dict:
    """Exporta el grafo para visualización."""
    nodos = []
    edges = []
    
    for nodo_id in grafo_contextos.nodes():
        if nodo_id in metadatos_contextos:
            metadatos = metadatos_contextos[nodo_id]
            es_temporal = metadatos.get("es_temporal", False)
            
            nodos.append({
                "id": nodo_id,
                "label": metadatos.get("titulo", "Sin título"),
                "title": f"{metadatos.get('titulo', '')}\n{metadatos.get('texto', '')[:100]}...",
                "group": "temporal" if es_temporal else "atemporal",
                "es_temporal": es_temporal
            })
    
    for origen, destino, datos in grafo_contextos.edges(data=True):
        peso_efectivo = datos.get("peso_efectivo", 1.0)
        
        edges.append({
            "from": origen,
            "to": destino,
            "weight": peso_efectivo,
            "title": f"Peso: {peso_efectivo:.3f}"
        })
    
    return {"nodes": nodos, "edges": edges}

def construir_arbol_consulta(pregunta: str, contextos_ids: List[str], referencia_temporal: Optional[str] = None, factor_refuerzo: float = 1.0) -> Dict:
    """Construye subgrafo en árbol para una consulta."""
    if not contextos_ids:
        return {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}}
    
    raiz_id = "consulta"
    ref_dt = datetime.fromisoformat(referencia_temporal) if referencia_temporal else datetime.now()
    claves_pregunta = set(extraer_palabras_clave(pregunta))
    
    # Nodo raíz
    pregunta_corta = pregunta[:50] + "..." if len(pregunta) > 50 else pregunta
    nodos = [{
        "id": raiz_id,
        "label": f"❓ {pregunta_corta}",
        "title": f"Pregunta: {pregunta}",
        "group": "pregunta"
    }]
    
    edges = []
    
    for cid in contextos_ids:
        meta = metadatos_contextos.get(cid, {})
        if not meta:
            continue
        
        # Nodo contexto
        titulo = meta.get("titulo", f"Contexto {cid}")
        nodos.append({
            "id": cid,
            "label": titulo[:30] + "..." if len(titulo) > 30 else titulo,
            "title": f"{titulo}\n{meta.get('texto', '')[:100]}...",
            "group": "temporal" if meta.get("es_temporal") else "atemporal",
            "es_temporal": bool(meta.get("es_temporal"))
        })
        
        # Calcular pesos
        claves_ctx = set(meta.get("palabras_clave", []))
        ws = _calcular_similitud_semantica(claves_pregunta, claves_ctx)
        
        ts = meta.get("timestamp")
        rt = _calcular_relevancia_temporal(ts, ref_dt.isoformat()) if ts else 0.0
        
        we = ws * (1 + rt * factor_refuerzo)
        
        edges.append({
            "from": raiz_id,
            "to": cid,
            "peso_estructural": round(ws, 3),
            "relevancia_temporal": round(rt, 3),
            "peso_efectivo": round(we, 3),
            "label": f"E:{round(ws,2)}|T:{round(rt,2)}|Ef:{round(we,2)}"
        })
    
    return {
        "nodes": nodos,
        "edges": edges,
        "meta": {
            "referencia_temporal": ref_dt.isoformat(),
            "contextos_procesados": len(contextos_ids),
            "pregunta_original": pregunta
        }
    }

def analizar_consulta_completa(pregunta: str) -> Dict:
    """Análisis completo de consulta: intención + contextos relevantes."""
    # Analizar intención temporal
    analisis_intencion = analizar_intencion_temporal(pregunta)
    
    referencia_temporal = analisis_intencion.get('timestamp_referencia')
    factor_refuerzo = analisis_intencion.get('factor_refuerzo_temporal', 1.0)
    
    # Obtener contextos relevantes
    from agent.semantica import buscar_similares
    try:
        ids_similares = buscar_similares(pregunta, k=5)
    except Exception as e:
        print(f"Error en búsqueda semántica: {e}")
        ids_similares = []
    
    # Construir árbol
    if ids_similares:
        arbol = construir_arbol_consulta(pregunta, ids_similares, referencia_temporal, factor_refuerzo)
    else:
        arbol = {"nodes": [], "edges": [], "meta": {"error": "No se encontraron contextos relevantes"}}
    
    return {
        "analisis_intencion": analisis_intencion,
        "contextos_recuperados": ids_similares,
        "arbol_consulta": arbol,
        "estrategia_aplicada": {
            "intencion_temporal": analisis_intencion['intencion_temporal'],
            "factor_refuerzo": factor_refuerzo,
            "referencia_temporal": referencia_temporal
        }
    }