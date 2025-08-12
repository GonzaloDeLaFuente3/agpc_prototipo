# agent/grafo.py
import networkx as nx
import pickle
import json
import os
import uuid
from typing import Dict, List, Optional, Set
from agent.extractor import extraer_palabras_clave
from agent.semantica import indexar_documento
import threading
from datetime import datetime


# Archivos de persistencia
ARCHIVO_GRAFO = "data/grafo_contextos.pickle"
ARCHIVO_METADATOS = "data/contexto.json"

# Grafo principal (NetworkX DiGraph para relaciones dirigidas)
grafo_contextos = nx.DiGraph()
metadatos_contextos = {}  # Información adicional de cada nodo

# Lock para operaciones thread-safe
_lock = threading.Lock()

def _guardar_grafo():
    """Guarda el grafo y metadatos en disco"""
    with _lock:
        os.makedirs("data", exist_ok=True)
        
        # Guardar grafo en pickle (eficiente para NetworkX)
        with open(ARCHIVO_GRAFO, 'wb') as f:
            pickle.dump(grafo_contextos, f)
        
        # Guardar metadatos en JSON (legible y debuggeable)
        with open(ARCHIVO_METADATOS, 'w', encoding='utf-8') as f:
            json.dump(metadatos_contextos, f, ensure_ascii=False, indent=2)

def _cargar_grafo():
    """Carga el grafo y metadatos desde disco"""
    global grafo_contextos, metadatos_contextos
    
    # Cargar grafo
    if os.path.exists(ARCHIVO_GRAFO):
        with open(ARCHIVO_GRAFO, 'rb') as f:
            grafo_contextos = pickle.load(f)
    else:
        grafo_contextos = nx.DiGraph()
    
    # Cargar metadatos
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
    
    # Similitud de Jaccard
    return interseccion / union if union > 0 else 0.0

def _recalcular_relaciones():
    """Recalcula todas las relaciones basadas en similitud semántica"""
    # Limpiar edges existentes
    grafo_contextos.clear_edges()
    
    nodos = list(grafo_contextos.nodes())
    
    for i, nodo_a in enumerate(nodos):
        metadatos_a = metadatos_contextos.get(nodo_a, {})
        claves_a = set(metadatos_a.get("palabras_clave", []))
        
        for nodo_b in nodos[i+1:]:  # Evitar duplicados
            metadatos_b = metadatos_contextos.get(nodo_b, {})
            claves_b = set(metadatos_b.get("palabras_clave", []))
            
            similitud = _calcular_similitud_semantica(claves_a, claves_b)
            
            # Crear relación si similitud > umbral
            if similitud > 0.1:  # Umbral configurable
                # Relación bidireccional con peso
                grafo_contextos.add_edge(nodo_a, nodo_b, peso=similitud, tipo="semantica")
                grafo_contextos.add_edge(nodo_b, nodo_a, peso=similitud, tipo="semantica")

# Funciones principales de la API
def cargar_desde_disco():
    """Carga el grafo desde disco"""
    _cargar_grafo()

def guardar_en_disco():
    """Guarda el grafo en disco"""
    _guardar_grafo()

def agregar_contexto(titulo: str, texto: str) -> str:
    """Agrega un nuevo contexto al grafo"""
    id_contexto = str(uuid.uuid4())
    palabras_clave = extraer_palabras_clave(texto)
    
    # Agregar nodo al grafo
    grafo_contextos.add_node(id_contexto, titulo=titulo)
    
    # Agregar metadatos
    metadatos_contextos[id_contexto] = {
        "titulo": titulo,
        "texto": texto,
        "palabras_clave": palabras_clave,
        "created_at": datetime.now().isoformat(),
        "relaciones": []  # Se calculará después
    }
    
    # Recalcular relaciones con todos los nodos
    _recalcular_relaciones()
    
    # Actualizar lista de relaciones en metadatos
    _actualizar_listas_relaciones()
    
    # Persistir
    _guardar_grafo()
    
    # Indexar para búsqueda semántica
    indexar_documento(id_contexto, texto)
    
    return id_contexto

def _actualizar_listas_relaciones():
    """Actualiza las listas de relaciones en metadatos"""
    for nodo in grafo_contextos.nodes():
        if nodo in metadatos_contextos:
            # Obtener vecinos (nodos conectados)
            vecinos = list(grafo_contextos.neighbors(nodo))
            metadatos_contextos[nodo]["relaciones"] = vecinos

def obtener_todos() -> Dict:
    """Obtiene todos los contextos en formato compatible con la API anterior"""
    resultado = {}
    
    for nodo in grafo_contextos.nodes():
        if nodo in metadatos_contextos:
            metadatos = metadatos_contextos[nodo].copy()
            # Asegurar que tiene la estructura esperada
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
    """Obtiene estadísticas del grafo"""
    stats = {
        "storage_type": "NetworkX Graph Database",
        "total_contextos": grafo_contextos.number_of_nodes(),
        "total_relaciones": grafo_contextos.number_of_edges(),
        "archivo_grafo": ARCHIVO_GRAFO,
        "archivo_metadatos": ARCHIVO_METADATOS
    }
    
    # Tamaños de archivos
    for archivo, key in [(ARCHIVO_GRAFO, "tamaño_grafo_mb"), (ARCHIVO_METADATOS, "tamaño_metadatos_mb")]:
        if os.path.exists(archivo):
            stats[key] = round(os.path.getsize(archivo) / (1024*1024), 3)
    
    # Estadísticas del grafo
    if grafo_contextos.number_of_nodes() > 0:
        # Densidad del grafo
        stats["densidad"] = round(nx.density(grafo_contextos), 3)
        
        # Componentes conectados
        stats["componentes_conectados"] = nx.number_weakly_connected_components(grafo_contextos)
        
        # Nodo con más conexiones (centralidad de grado)
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

def obtener_camino_mas_corto(id_origen: str, id_destino: str) -> List[str]:
    """Encuentra el camino más corto entre dos contextos"""
    try:
        if id_origen in grafo_contextos and id_destino in grafo_contextos:
            return nx.shortest_path(grafo_contextos.to_undirected(), id_origen, id_destino)
        return []
    except nx.NetworkXNoPath:
        return []

def obtener_contextos_centrales(k: int = 5) -> List[Dict]:
    """Obtiene los k contextos más centrales en el grafo"""
    if grafo_contextos.number_of_nodes() == 0:
        return []
    
    # Calcular centralidad de cercanía
    centralidad = nx.closeness_centrality(grafo_contextos.to_undirected())
    
    # Obtener los k más centrales
    nodos_centrales = sorted(centralidad.items(), key=lambda x: x[1], reverse=True)[:k]
    
    resultado = []
    for nodo_id, centralidad_valor in nodos_centrales:
        if nodo_id in metadatos_contextos:
            info = metadatos_contextos[nodo_id].copy()
            info["centralidad"] = round(centralidad_valor, 3)
            info["id"] = nodo_id
            resultado.append(info)
    
    return resultado

def buscar_contextos_por_patron(patron: str) -> List[str]:
    """Busca contextos que coincidan con un patrón en título o texto"""
    patron_lower = patron.lower()
    resultados = []
    
    for nodo_id, metadatos in metadatos_contextos.items():
        titulo = metadatos.get("titulo", "").lower()
        texto = metadatos.get("texto", "").lower()
        
        if patron_lower in titulo or patron_lower in texto:
            resultados.append(nodo_id)
    
    return resultados

def exportar_grafo_para_visualizacion() -> Dict:
    """Exporta el grafo en formato para vis.js o similar"""
    nodos = []
    edges = []
    
    # Nodos
    for nodo_id in grafo_contextos.nodes():
        if nodo_id in metadatos_contextos:
            metadatos = metadatos_contextos[nodo_id]
            nodos.append({
                "id": nodo_id,
                "label": metadatos.get("titulo", "Sin título"),
                "title": f"{metadatos.get('titulo', '')}\n{metadatos.get('texto', '')[:100]}...",
                "group": len(metadatos.get("palabras_clave", [])),  # Agrupar por cantidad de palabras clave
            })
    
    # Edges
    for origen, destino, datos in grafo_contextos.edges(data=True):
        edges.append({
            "from": origen,
            "to": destino,
            "weight": datos.get("peso", 1),
            "title": f"Similitud: {datos.get('peso', 0):.2f}"
        })
    
    return {"nodes": nodos, "edges": edges}

# Funciones de utilidad avanzadas
def recalcular_relaciones():
    """Función pública para recalcular relaciones"""
    _recalcular_relaciones()
    _actualizar_listas_relaciones()
    _guardar_grafo()
