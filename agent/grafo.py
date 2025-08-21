# agent/grafo.py - PASO 1: Agregando soporte temporal
import networkx as nx
import pickle
import json
import os
import uuid
from typing import Dict, List, Optional, Set
from agent.extractor import extraer_palabras_clave
from agent.semantica import indexar_documento
import threading
from datetime import datetime, timedelta
import math

# Archivos de persistencia
ARCHIVO_GRAFO = "data/grafo_contextos.pickle"
ARCHIVO_METADATOS = "data/contexto.json"

# Grafo principal
grafo_contextos = nx.DiGraph()
metadatos_contextos = {}

# Lock para operaciones thread-safe
_lock = threading.Lock()

def _guardar_grafo():
    """Guarda el grafo y metadatos en disco"""
    with _lock:
        os.makedirs("data", exist_ok=True)
        
        with open(ARCHIVO_GRAFO, 'wb') as f:
            pickle.dump(grafo_contextos, f)
        
        with open(ARCHIVO_METADATOS, 'w', encoding='utf-8') as f:
            json.dump(metadatos_contextos, f, ensure_ascii=False, indent=2)

def _cargar_grafo():
    """Carga el grafo y metadatos desde disco"""
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

def _calcular_similitud_semantica(claves_a: Set[str], claves_b: Set[str]) -> float:
    """Calcula similitud semántica entre dos conjuntos de palabras clave"""
    if not claves_a or not claves_b:
        return 0.0
    
    interseccion = len(claves_a & claves_b)
    union = len(claves_a | claves_b)
    
    return interseccion / union if union > 0 else 0.0

def _calcular_relevancia_temporal(fecha_a: str, fecha_b: str) -> float:
    """
    Calcula la relevancia temporal entre dos contextos
    Retorna un valor entre 0.0 y 1.0 donde:
    - 1.0 = máxima relevancia (mismo día)
    - 0.5 = relevancia media (1 semana)
    - 0.1 = baja relevancia (1 mes)
    - 0.0 = muy baja relevancia (>3 meses)
    """
    if not fecha_a or not fecha_b:
        return 0.0
    
    try:
        dt_a = datetime.fromisoformat(fecha_a)
        dt_b = datetime.fromisoformat(fecha_b)
        
        # Diferencia en días
        diferencia_dias = abs((dt_a - dt_b).days)
        
        # Función de decaimiento exponencial
        # R_temporal = e^(-diferencia_dias / factor_decaimiento)
        factor_decaimiento = 30  # 30 días para decaer significativamente
        relevancia = math.exp(-diferencia_dias / factor_decaimiento)
        
        return min(1.0, max(0.0, relevancia))
        
    except (ValueError, TypeError):
        return 0.0

def _calcular_peso_efectivo(peso_estructural: float, relevancia_temporal: float) -> float:
    """
    Calcula el peso efectivo combinando estructura y temporalidad
    W_efectivo = W_estructural × (1 + R_temporal)
    """
    return peso_estructural * (1 + relevancia_temporal)

def _recalcular_relaciones():
    """Recalcula todas las relaciones basadas en similitud semántica Y temporal"""
    # Limpiar edges existentes
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
            
            # Calcular similitud estructural
            similitud_estructural = _calcular_similitud_semantica(claves_a, claves_b)
            
            # Calcular relevancia temporal
            relevancia_temporal = _calcular_relevancia_temporal(fecha_a, fecha_b)
            
            # Calcular peso efectivo
            peso_efectivo = _calcular_peso_efectivo(similitud_estructural, relevancia_temporal)
            
            # Crear relación si similitud estructural > umbral mínimo
            if similitud_estructural > 0.1:
                # Datos completos en la arista
                datos_arista = {
                    "peso_estructural": round(similitud_estructural, 3),
                    "relevancia_temporal": round(relevancia_temporal, 3),
                    "peso_efectivo": round(peso_efectivo, 3),
                    "tipo": "semantica_temporal" if (fecha_a and fecha_b) else "semantica",
                    "actualizado": datetime.now().isoformat()
                }
                
                # Relación bidireccional
                grafo_contextos.add_edge(nodo_a, nodo_b, **datos_arista)
                grafo_contextos.add_edge(nodo_b, nodo_a, **datos_arista)

# Funciones principales de la API
def cargar_desde_disco():
    """Carga el grafo desde disco"""
    _cargar_grafo()

def guardar_en_disco():
    """Guarda el grafo en disco"""
    _guardar_grafo()

def agregar_contexto(titulo: str, texto: str, es_temporal: bool = False) -> str:
    """
    Agrega un nuevo contexto al grafo
    es_temporal: si True, asigna timestamp actual; si False, contexto atemporal
    """
    id_contexto = str(uuid.uuid4())
    palabras_clave = extraer_palabras_clave(texto)
    
    # Agregar nodo al grafo
    grafo_contextos.add_node(id_contexto, titulo=titulo)
    
    # Metadatos base
    metadatos = {
        "titulo": titulo,
        "texto": texto,
        "palabras_clave": palabras_clave,
        "created_at": datetime.now().isoformat(),
        "es_temporal": es_temporal,
        "relaciones": []
    }
    
    # Agregar timestamp solo si es temporal
    if es_temporal:
        metadatos["timestamp"] = datetime.now().isoformat()
    
    metadatos_contextos[id_contexto] = metadatos
    
    # Recalcular relaciones
    _recalcular_relaciones()
    _actualizar_listas_relaciones()
    _guardar_grafo()
    
    # Indexar para búsqueda semántica
    indexar_documento(id_contexto, texto)
    
    return id_contexto

def actualizar_pesos_temporales() -> Dict:
    """
    Actualiza todos los pesos temporales en el grafo
    Útil para ejecutar manualmente o en intervalos
    """
    inicio = datetime.now()
    
    # Recalcular todas las relaciones
    _recalcular_relaciones()
    _actualizar_listas_relaciones()
    _guardar_grafo()
    
    fin = datetime.now()
    duracion = (fin - inicio).total_seconds()
    
    return {
        "status": "actualizado",
        "timestamp": fin.isoformat(),
        "duracion_segundos": round(duracion, 3),
        "total_aristas": grafo_contextos.number_of_edges(),
        "aristas_temporales": len([
            math.e for _, _, datos in grafo_contextos.edges(data=True) 
            if datos.get("tipo") == "semantica_temporal"
        ])
    }

def _actualizar_listas_relaciones():
    """Actualiza las listas de relaciones en metadatos"""
    for nodo in grafo_contextos.nodes():
        if nodo in metadatos_contextos:
            vecinos = list(grafo_contextos.neighbors(nodo))
            metadatos_contextos[nodo]["relaciones"] = vecinos

def obtener_todos() -> Dict:
    """Obtiene todos los contextos"""
    resultado = {}
    
    for nodo in grafo_contextos.nodes():
        if nodo in metadatos_contextos:
            metadatos = metadatos_contextos[nodo].copy()
            if "relaciones" not in metadatos:
                metadatos["relaciones"] = list(grafo_contextos.neighbors(nodo))
            resultado[nodo] = metadatos
    
    return resultado

def obtener_relacionados(id_contexto: str) -> Dict:
    """Obtiene contextos relacionados a un ID específico"""
    if id_contexto not in grafo_contextos:
        return {}
    
    relacionados = {}
    vecinos = grafo_contextos.neighbors(id_contexto)
    
    for vecino in vecinos:
        if vecino in metadatos_contextos:
            relacionados[vecino] = metadatos_contextos[vecino]
    
    return relacionados

def obtener_estadisticas() -> Dict:
    """Obtiene estadísticas del grafo incluyendo información temporal"""
    stats = {
        "storage_type": "NetworkX Graph Database (Temporal)",
        "total_contextos": grafo_contextos.number_of_nodes(),
        "total_relaciones": grafo_contextos.number_of_edges(),
        "archivo_grafo": ARCHIVO_GRAFO,
        "archivo_metadatos": ARCHIVO_METADATOS
    }
    
    # Contar contextos temporales vs atemporales
    contextos_temporales = sum(1 for ctx in metadatos_contextos.values() 
                              if ctx.get("es_temporal", False))
    stats["contextos_temporales"] = contextos_temporales
    stats["contextos_atemporales"] = stats["total_contextos"] - contextos_temporales
    
    # Contar aristas temporales vs semánticas
    aristas_temporales = 0
    aristas_semanticas = 0
    
    for _, _, datos in grafo_contextos.edges(data=True):
        if datos.get("tipo") == "semantica_temporal":
            aristas_temporales += 1
        else:
            aristas_semanticas += 1
    
    stats["aristas_temporales"] = aristas_temporales
    stats["aristas_semanticas"] = aristas_semanticas
    
    # Tamaños de archivos
    for archivo, key in [(ARCHIVO_GRAFO, "tamaño_grafo_mb"), (ARCHIVO_METADATOS, "tamaño_metadatos_mb")]:
        if os.path.exists(archivo):
            stats[key] = round(os.path.getsize(archivo) / (1024*1024), 3)
    
    # Estadísticas del grafo
    if grafo_contextos.number_of_nodes() > 0:
        stats["densidad"] = round(nx.density(grafo_contextos), 3)
        stats["componentes_conectados"] = nx.number_weakly_connected_components(grafo_contextos)
        
        grados = dict(grafo_contextos.degree())
        if grados:
            nodo_max_grado = max(grados.items(), key=lambda x: x[1])
            titulo_max = metadatos_contextos.get(nodo_max_grado[0], {}).get("titulo", "Desconocido")
            stats["nodo_mas_conectado"] = {
                "id": nodo_max_grado[0],
                "titulo": titulo_max,
                "conexiones": nodo_max_grado[1]
            }
    
    return stats

def obtener_contextos_centrales(k: int = 5) -> List[Dict]:
    """Obtiene los k contextos más centrales considerando pesos efectivos"""
    if grafo_contextos.number_of_nodes() == 0:
        return []
    
    # Crear grafo con pesos efectivos para calcular centralidad
    grafo_ponderado = nx.Graph()
    
    for nodo in grafo_contextos.nodes():
        grafo_ponderado.add_node(nodo)
    
    for origen, destino, datos in grafo_contextos.edges(data=True):
        peso = datos.get("peso_efectivo", datos.get("peso_estructural", 1.0))
        if not grafo_ponderado.has_edge(origen, destino):
            grafo_ponderado.add_edge(origen, destino, weight=peso)
    
    # Calcular centralidad de cercanía ponderada
    centralidad = nx.closeness_centrality(grafo_ponderado, distance='weight')
    
    nodos_centrales = sorted(centralidad.items(), key=lambda x: x[1], reverse=True)[:k]
    
    resultado = []
    for nodo_id, centralidad_valor in nodos_centrales:
        if nodo_id in metadatos_contextos:
            info = metadatos_contextos[nodo_id].copy()
            info["centralidad"] = round(centralidad_valor, 3)
            info["id"] = nodo_id
            resultado.append(info)
    
    return resultado

def exportar_grafo_para_visualizacion() -> Dict:
    """Exporta el grafo en formato para visualización con información temporal"""
    nodos = []
    edges = []
    
    # Nodos con diferenciación temporal
    for nodo_id in grafo_contextos.nodes():
        if nodo_id in metadatos_contextos:
            metadatos = metadatos_contextos[nodo_id]
            es_temporal = metadatos.get("es_temporal", False)
            
            nodos.append({
                "id": nodo_id,
                "label": metadatos.get("titulo", "Sin título"),
                "title": f"{metadatos.get('titulo', '')}\n{metadatos.get('texto', '')[:100]}...\n{'🕒 Temporal' if es_temporal else '📋 Atemporal'}",
                "group": "temporal" if es_temporal else "atemporal",
                "es_temporal": es_temporal,
                "timestamp": metadatos.get("timestamp")
            })
    
    # Edges con información temporal completa
    for origen, destino, datos in grafo_contextos.edges(data=True):
        peso_estructural = datos.get("peso_estructural", 1.0)
        relevancia_temporal = datos.get("relevancia_temporal", 0.0)
        peso_efectivo = datos.get("peso_efectivo", peso_estructural)
        tipo = datos.get("tipo", "semantica")
        
        edges.append({
            "from": origen,
            "to": destino,
            "weight": peso_efectivo,
            "peso_estructural": peso_estructural,
            "relevancia_temporal": relevancia_temporal,
            "peso_efectivo": peso_efectivo,
            "tipo": tipo,
            "title": f"Estructural: {peso_estructural:.3f}\nTemporal: {relevancia_temporal:.3f}\nEfectivo: {peso_efectivo:.3f}\nTipo: {tipo}"
        })
    
    return {"nodes": nodos, "edges": edges}

def construir_arbol_consulta(pregunta: str, contextos_ids: List[str], referencia_temporal: Optional[str] = None) -> Dict:
    """
    Construye un subgrafo en forma de ÁRBOL para una consulta.
    - Raíz: la pregunta (NO se persiste).
    - Ramas: nodos contextuales recuperados.
    - Cada arista incluye: Ws (peso_estructural), Rt (relevancia_temporal), We (peso_efectivo = Ws * (1 + Rt)).

    Nota: Ws se calcula como similitud (Jaccard) entre palabras clave de la pregunta
    y del contexto. Rt se calcula contra 'referencia_temporal' (por defecto, ahora).
    """
    if not contextos_ids:
        return {"nodes": [], "edges": [], "meta": {"error": "No hay contextos para procesar"}}
    
    raiz_id = "consulta"
    ref_dt = datetime.fromisoformat(referencia_temporal) if referencia_temporal else datetime.now()

    # Palabras clave de la pregunta
    try:
        claves_pregunta = set(extraer_palabras_clave(pregunta))
    except Exception as e:
        print(f"Error extrayendo palabras clave: {e}")
        claves_pregunta = set()

    # Truncar pregunta para el label si es muy larga
    pregunta_corta = pregunta[:50] + "..." if len(pregunta) > 50 else pregunta
    
    nodos = [{
        "id": raiz_id,
        "label": f"❓ {pregunta_corta}",
        "title": f"Pregunta: {pregunta}",
        "group": "pregunta",
        "es_temporal": False
    }]
    edges = []

    contextos_procesados = 0
    
    for cid in contextos_ids:
        meta = metadatos_contextos.get(cid, {})
        if not meta:
            print(f"Warning: Contexto {cid} no encontrado en metadatos")
            continue

        # Nodo del contexto
        titulo = meta.get("titulo", f"Contexto {cid}")
        nodos.append({
            "id": cid,
            "label": titulo[:30] + "..." if len(titulo) > 30 else titulo,
            "title": f"{titulo}\n{meta.get('texto', '')[:100]}...",
            "group": "temporal" if meta.get("es_temporal") else "atemporal",
            "es_temporal": bool(meta.get("es_temporal")),
            "timestamp": meta.get("timestamp"),
        })

        # Ws: similitud por palabras clave (Jaccard)
        claves_ctx = set(meta.get("palabras_clave", []))
        ws = _calcular_similitud_semantica(claves_pregunta, claves_ctx)

        # Rt: relevancia temporal del nodo respecto a la referencia
        ts = meta.get("timestamp")
        rt = _calcular_relevancia_temporal(ts, ref_dt.isoformat()) if ts else 0.0

        # We: combinado
        we = _calcular_peso_efectivo(ws, rt)

        edges.append({
            "from": raiz_id,
            "to": cid,
            "tipo": "consulta",
            "peso_estructural": round(ws, 3),        # Ws
            "relevancia_temporal": round(rt, 3),     # Rt
            "peso_efectivo": round(we, 3),           # We = Ws * (1 + Rt)
            # label listo para UI si querés usarlo directo
            "label": f"E:{round(ws,2)}|T:{round(rt,2)}|Ef:{round(we,2)}"
        })
        
        contextos_procesados += 1

    return {
        "nodes": nodos,
        "edges": edges,
        "meta": {
            "referencia_temporal": ref_dt.isoformat(),
            "contextos_procesados": contextos_procesados,
            "total_solicitados": len(contextos_ids),
            "pregunta_original": pregunta
        }
    }