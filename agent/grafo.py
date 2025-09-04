# agent/grafo.py - Versión limpia y optimizada
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
from agent.semantica import indexar_documento, coleccion
from agent.temporal_parser import extraer_referencias_del_texto, parsear_referencia_temporal
from agent.query_analyzer import analizar_intencion_temporal

# === NUEVAS FUNCIONES PARA CONVERSACIONES Y FRAGMENTOS ===

# Nuevas estructuras de datos
conversaciones_metadata = {}
fragmentos_metadata = {}

def agregar_conversacion(titulo: str, contenido: str, fecha: str = None, 
                        participantes: List[str] = None, metadata: Dict = None) -> Dict:
    """
    Agrega una conversación completa y la fragmenta automáticamente.
    
    Returns:
        {
            'conversacion_id': str,
            'fragmentos_creados': List[str],
            'total_fragmentos': int
        }
    """
    from agent.fragmentador import fragmentar_conversacion
    
    # Preparar datos de conversación
    conversacion_data = {
        'titulo': titulo,
        'contenido': contenido,
        'fecha': fecha or datetime.now().isoformat(),
        'participantes': participantes or [],
        'metadata': metadata or {}
    }
    
    # Fragmentar conversación
    fragmentos = fragmentar_conversacion(conversacion_data)
    
    if not fragmentos:
        raise ValueError("No se pudieron generar fragmentos de esta conversación")
    
    conversacion_id = fragmentos[0]['metadata']['conversacion_id']
    fragmentos_ids = []
    
    # Agregar conversación a metadatos
    conversaciones_metadata[conversacion_id] = {
        'titulo': titulo,
        'fecha': fecha or datetime.now().isoformat(),
        'participantes': participantes or [],
        'metadata': metadata or {},
        'total_fragmentos': len(fragmentos),
        'fragmentos_ids': [f['id'] for f in fragmentos],
        'created_at': datetime.now().isoformat()
    }
    
    # Procesar cada fragmento como si fuera un contexto individual
    for fragmento in fragmentos:
        frag_id = fragmento['id']
        frag_meta = fragmento['metadata']
        
        # Agregar fragmento al grafo como nodo
        titulo_fragmento = f"{titulo} - Fragmento {frag_meta['posicion_en_conversacion']}"
        grafo_contextos.add_node(frag_id, titulo=titulo_fragmento)
        
        # Guardar metadatos del fragmento
        fragmentos_metadata[frag_id] = frag_meta
        
        # También mantener compatibilidad con metadatos_contextos
        metadatos_contextos[frag_id] = {
            "titulo": titulo_fragmento,
            "texto": frag_meta['texto'],
            "palabras_clave": frag_meta['palabras_clave'],
            "created_at": frag_meta['created_at'],
            "es_temporal": frag_meta['es_temporal'],
            "timestamp": frag_meta.get('timestamp'),
            "tipo_contexto": frag_meta['tipo_contexto'],
            # Metadatos específicos de fragmento
            "es_fragmento": True,
            "conversacion_id": conversacion_id,
            "posicion_fragmento": frag_meta['posicion_en_conversacion']
        }
        
        # Indexar para búsqueda semántica
        indexar_documento(frag_id, frag_meta['texto'])
        fragmentos_ids.append(frag_id)
    
    # Recalcular relaciones con los nuevos fragmentos
    _recalcular_relaciones()
    _guardar_grafo()
    
    # También guardar nuevas estructuras
    _guardar_conversaciones()
    
    print(f"✅ Conversación '{titulo}' agregada: {len(fragmentos)} fragmentos creados")
    
    return {
        'conversacion_id': conversacion_id,
        'fragmentos_creados': fragmentos_ids,
        'total_fragmentos': len(fragmentos)
    }

def _guardar_conversaciones():
    """Guarda metadatos de conversaciones y fragmentos."""
    import os
    import json
    
    os.makedirs("data", exist_ok=True)
    
    with open("data/conversaciones.json", 'w', encoding='utf-8') as f:
        json.dump(conversaciones_metadata, f, ensure_ascii=False, indent=2)
    
    with open("data/fragmentos.json", 'w', encoding='utf-8') as f:
        json.dump(fragmentos_metadata, f, ensure_ascii=False, indent=2)

def cargar_conversaciones_desde_disco():
    """Carga metadatos de conversaciones desde disco."""
    global conversaciones_metadata, fragmentos_metadata
    import os
    import json
    
    if os.path.exists("data/conversaciones.json"):
        with open("data/conversaciones.json", 'r', encoding='utf-8') as f:
            conversaciones_metadata = json.load(f)
    
    if os.path.exists("data/fragmentos.json"):
        with open("data/fragmentos.json", 'r', encoding='utf-8') as f:
            fragmentos_metadata = json.load(f)

def obtener_conversaciones() -> Dict:
    """Obtiene todas las conversaciones."""
    return conversaciones_metadata

def obtener_fragmentos_de_conversacion(conversacion_id: str) -> List[Dict]:
    """Obtiene todos los fragmentos de una conversación específica."""
    if conversacion_id not in conversaciones_metadata:
        return []
    
    fragmentos_ids = conversaciones_metadata[conversacion_id]['fragmentos_ids']
    
    fragmentos = []
    for frag_id in fragmentos_ids:
        if frag_id in fragmentos_metadata:
            fragmentos.append({
                'id': frag_id,
                'metadata': fragmentos_metadata[frag_id]
            })
    
    return fragmentos

# Archivos de persistencia
ARCHIVO_GRAFO = "data/grafo_contextos.pickle"
ARCHIVO_METADATOS = "data/contexto.json"

# Grafo y metadatos globales
grafo_contextos = nx.DiGraph()
metadatos_contextos = {}
_lock = threading.Lock()

def _detectar_tipo_contexto(titulo: str, texto: str) -> str:
    """Detecta el tipo de contexto para ajustar decaimiento temporal."""
    texto_completo = f"{titulo} {texto}".lower()
    
    # Palabras clave por categoría
    patrones = {
        "reunion": ["reunión", "meeting", "cita", "entrevista", "llamada", "videoconferencia"],
        "tarea": ["tarea", "pendiente", "hacer", "completar", "entregar", "deadline"],
        "evento": ["evento", "conferencia", "seminario", "workshop", "celebración"],
        "proyecto": ["proyecto", "desarrollo", "implementar", "planificar", "estrategia"],
        "conocimiento": ["concepto", "definición", "procedimiento", "manual", "guía", "documentación"]
    }
    
    for tipo, palabras in patrones.items():
        if any(palabra in texto_completo for palabra in palabras):
            return tipo
    
    return "general"

def _obtener_factor_decaimiento(tipo_contexto: str) -> int:
    """Obtiene factor de decaimiento en días según tipo de contexto."""
    factores = {
        "reunion": 2,        # Reuniones caducan rápido
        "tarea": 7,          # Tareas tienen urgencia semanal  
        "evento": 3,         # Eventos puntuales
        "proyecto": 45,      # Proyectos largo plazo
        "conocimiento": 365, # Conocimiento perdura
        "general": 30        # Default actual
    }
    return factores.get(tipo_contexto, 30)

def _calcular_similitud_jaccard(claves_a: Set[str], claves_b: Set[str]) -> float:
    """Calcula similitud Jaccard entre dos conjuntos."""
    if not claves_a or not claves_b:
        return 0.0
    
    interseccion = len(claves_a & claves_b)
    union = len(claves_a | claves_b)
    jaccard = interseccion / union if union > 0 else 0.0
    return jaccard

def _calcular_similitud_semantica_simple(texto_a: str, texto_b: str) -> float:
    """Calcula similitud semántica usando ChromaDB query."""
    try:
        if not texto_a.strip() or not texto_b.strip():
            return 0.0
        
        # Crear un documento temporal para comparar
        temp_id = f"temp_{hash(texto_a)}"
        
        # Indexar temporalmente el primer texto
        indexar_documento(temp_id, texto_a)
        
        # Buscar similitud con el segundo texto
        resultado = coleccion.query(
            query_texts=[texto_b],
            n_results=10,  # Buscar más resultados para encontrar nuestro temp
            include=['distances']
        )
        
        # Buscar nuestro documento temporal en los resultados
        if temp_id in resultado['ids'][0]:
            index = resultado['ids'][0].index(temp_id)
            distance = resultado['distances'][0][index]
            # Convertir distancia a similitud (0=idéntico, 2=muy diferente)
            similitud = max(0.0, 1.0 - distance / 2.0)
        else:
            similitud = 0.0
        
        # Limpiar documento temporal
        try:
            coleccion.delete(ids=[temp_id])
        except:
            pass
            
        return similitud
        
    except Exception as e:
        print(f"Error en similitud semántica: {e}")
        return 0.0

def _calcular_similitud_estructural(claves_a: Set[str], claves_b: Set[str], texto_a: str, texto_b: str) -> float:
    """
    Calcula similitud estructural como el promedio de similitud Jaccard y semántica.
    Similitud_estructural = (Similitud_jaccard + Similitud_semantica) / 2
    """
    # Calcular componentes
    similitud_jaccard = _calcular_similitud_jaccard(claves_a, claves_b)
    similitud_semantica = _calcular_similitud_semantica_simple(texto_a, texto_b)
    
    # Promedio de ambas similitudes
    similitud_estructural = (similitud_jaccard + similitud_semantica) / 2
    
    return similitud_estructural

def _calcular_relevancia_temporal(fecha_a: str, fecha_b: str, tipo_a: str = "general", tipo_b: str = "general") -> float:
    """Calcula relevancia temporal con decaimiento dinámico por tipo."""
    if not fecha_a or not fecha_b:
        return 0.0
    
    try:
        dt_a = datetime.fromisoformat(fecha_a)
        dt_b = datetime.fromisoformat(fecha_b)
        
        diferencia_dias = abs((dt_a - dt_b).days)
        
        # Usar el factor más restrictivo (menor) entre ambos contextos
        factor_a = _obtener_factor_decaimiento(tipo_a)
        factor_b = _obtener_factor_decaimiento(tipo_b)
        factor_decaimiento = min(factor_a, factor_b)
        
        relevancia = math.exp(-diferencia_dias / factor_decaimiento)
        return min(1.0, max(0.0, relevancia))
        
    except (ValueError, TypeError):
        return 0.0

def _calcular_similitud_textual_exacta(texto_a: str, texto_b: str) -> float:
    """Calcula similitud textual exacta entre dos textos."""
    if not texto_a or not texto_b:
        return 0.0
    
    # Normalizar textos (remover espacios extra, convertir a minúsculas)
    texto_a_norm = " ".join(texto_a.lower().split())
    texto_b_norm = " ".join(texto_b.lower().split())
    
    if texto_a_norm == texto_b_norm:
        return 1.0
    
    # Similitud por caracteres comunes
    caracteres_a = set(texto_a_norm)
    caracteres_b = set(texto_b_norm)
    
    if not caracteres_a or not caracteres_b:
        return 0.0
    
    intersection = len(caracteres_a & caracteres_b)
    union = len(caracteres_a | caracteres_b)
    
    return intersection / union if union > 0 else 0.0

def _recalcular_relaciones():
    """Recalcula todas las relaciones del grafo con similitud estructural corregida."""
    grafo_contextos.clear_edges()
    nodos = list(grafo_contextos.nodes())
    
    print(f"Recalculando relaciones para {len(nodos)} nodos...")
    
    for i, nodo_a in enumerate(nodos):
        metadatos_a = metadatos_contextos.get(nodo_a, {})
        claves_a = set(metadatos_a.get("palabras_clave", []))
        fecha_a = metadatos_a.get("timestamp")
        tipo_a = metadatos_a.get("tipo_contexto", "general")
        texto_a = metadatos_a.get("texto", "")
        
        for nodo_b in nodos[i+1:]:
            metadatos_b = metadatos_contextos.get(nodo_b, {})
            claves_b = set(metadatos_b.get("palabras_clave", []))
            fecha_b = metadatos_b.get("timestamp")
            tipo_b = metadatos_b.get("tipo_contexto", "general")
            texto_b = metadatos_b.get("texto", "")
            
            # Calcular similitudes
            similitud_estructural = _calcular_similitud_estructural(claves_a, claves_b, texto_a, texto_b)
            relevancia_temporal = _calcular_relevancia_temporal(fecha_a, fecha_b, tipo_a, tipo_b)
            peso_efectivo = similitud_estructural * (1 + relevancia_temporal)
            
            if similitud_estructural > 0.1:  # Umbral más bajo para capturar más relaciones
                datos_arista = {
                    "peso_estructural": round(similitud_estructural, 3),
                    "relevancia_temporal": round(relevancia_temporal, 3),
                    "peso_efectivo": round(peso_efectivo, 3),
                    "tipo": "semantica_temporal" if (fecha_a and fecha_b) else "semantica",
                    "tipos_contexto": f"{tipo_a}-{tipo_b}"
                }
                
                grafo_contextos.add_edge(nodo_a, nodo_b, **datos_arista)
                grafo_contextos.add_edge(nodo_b, nodo_a, **datos_arista)
    
    print(f"Total aristas creadas: {grafo_contextos.number_of_edges()}")

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
    
    # NUEVO: Cargar también conversaciones y fragmentos
    cargar_conversaciones_desde_disco()

def agregar_contexto(titulo: str, texto: str, es_temporal: bool = None, referencia_temporal: str = None) -> str:
    """Agrega un nuevo contexto con prevención de duplicados."""
    
    # PREVENCIÓN DE DUPLICADOS - Verificación antes de agregar
    titulo_norm = titulo.strip().lower()
    texto_norm = " ".join(texto.strip().lower().split())
    
    for ctx_id, meta in metadatos_contextos.items():
        titulo_existente = meta.get("titulo", "").strip().lower()
        texto_existente = " ".join(meta.get("texto", "").strip().lower().split())
        
        # Verificar duplicado exacto o muy similar
        if (titulo_norm == titulo_existente and texto_norm == texto_existente) or \
           (len(texto_norm) > 50 and _calcular_similitud_textual_exacta(texto_norm, texto_existente) > 0.98):
            print(f"⚠️ Contexto duplicado detectado - no agregando. Retornando ID existente: {ctx_id}")
            return ctx_id  # Retornar ID del existente
    
    # Continuar con el proceso normal si no es duplicado
    id_contexto = str(uuid.uuid4())
    palabras_clave = extraer_palabras_clave(texto)
    
    # Detectar tipo de contexto
    tipo_contexto = _detectar_tipo_contexto(titulo, texto)
    
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
        "tipo_contexto": tipo_contexto
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
    
    # Indexar para búsqueda semántica
    indexar_documento(id_contexto, texto)
    
    # Recalcular y guardar
    _recalcular_relaciones()
    _guardar_grafo()
    
    print(f"✅ Nuevo contexto agregado: {titulo} (ID: {id_contexto})")
    return id_contexto

def obtener_todos() -> Dict:
    """Obtiene todos los contextos."""
    return metadatos_contextos

def obtener_estadisticas() -> Dict:
    """Obtiene estadísticas básicas del grafo incluyendo tipos de contexto."""
    stats = {
        "total_contextos": grafo_contextos.number_of_nodes(),
        "total_relaciones": grafo_contextos.number_of_edges(),
    }
    
    # Contar temporales vs atemporales
    temporales = sum(1 for ctx in metadatos_contextos.values() 
                    if ctx.get("es_temporal", False))
    stats["contextos_temporales"] = temporales
    stats["contextos_atemporales"] = stats["total_contextos"] - temporales
    
    # Contar por tipos de contexto
    tipos_count = {}
    for ctx in metadatos_contextos.values():
        tipo = ctx.get("tipo_contexto", "general")
        tipos_count[tipo] = tipos_count.get(tipo, 0) + 1
    
    stats["tipos_contexto"] = tipos_count
    
    return stats

def exportar_grafo_para_visualizacion() -> Dict:
    """Exporta el grafo para visualización con información de aristas."""
    nodos = []
    edges = []
    
    for nodo_id in grafo_contextos.nodes():
        if nodo_id in metadatos_contextos:
            metadatos = metadatos_contextos[nodo_id]
            es_temporal = metadatos.get("es_temporal", False)
            tipo_contexto = metadatos.get("tipo_contexto", "general")
            
            # Emoji por tipo de contexto
            iconos_tipo = {
                "reunion": "👥",
                "tarea": "📋", 
                "evento": "🎯",
                "proyecto": "🚀",
                "conocimiento": "📚",
                "general": "📄"
            }
            
            icono = iconos_tipo.get(tipo_contexto, "📄")
            titulo_con_icono = f"{icono} {metadatos.get('titulo', 'Sin título')}"
            
            nodos.append({
                "id": nodo_id,
                "label": titulo_con_icono,
                "title": f"{metadatos.get('titulo', '')}\n{metadatos.get('texto', '')[:100]}...\nTipo: {tipo_contexto}",
                "group": "temporal" if es_temporal else "atemporal",
                "es_temporal": es_temporal,
                "tipo_contexto": tipo_contexto
            })
    
    # Extraer datos de aristas
    for origen, destino, datos in grafo_contextos.edges(data=True):
        peso_estructural = None
        relevancia_temporal = None  
        peso_efectivo = None
        
        # Intentar múltiples claves posibles
        for key in ["peso_estructural", "similitud_estructural", "weight_estructural"]:
            if key in datos and datos[key] is not None:
                peso_estructural = float(datos[key])
                break
        
        for key in ["relevancia_temporal", "temporal_relevance", "weight_temporal"]:
            if key in datos and datos[key] is not None:
                relevancia_temporal = float(datos[key])
                break
                
        for key in ["peso_efectivo", "weight", "effective_weight"]:
            if key in datos and datos[key] is not None:
                peso_efectivo = float(datos[key])
                break
        
        # Valores por defecto
        peso_estructural = peso_estructural if peso_estructural is not None else 0.0
        relevancia_temporal = relevancia_temporal if relevancia_temporal is not None else 0.0
        peso_efectivo = peso_efectivo if peso_efectivo is not None else 0.0
        
        tipos_contexto = datos.get("tipos_contexto", "desconocido")
        
        # Etiqueta de arista
        label = f"E:{peso_estructural:.2f}|T:{relevancia_temporal:.2f}|W:{peso_efectivo:.2f}"
        title = f"Peso Estructural: {peso_estructural:.3f}\nRelevancia Temporal: {relevancia_temporal:.3f}\nPeso Efectivo: {peso_efectivo:.3f}\nTipos: {tipos_contexto}"
        
        edges.append({
            "from": origen,
            "to": destino,
            "weight": peso_efectivo,
            "label": label,
            "title": title,
            "font": {"size": 10, "align": "top"},
            "peso_estructural": peso_estructural,
            "relevancia_temporal": relevancia_temporal,
            "peso_efectivo": peso_efectivo
        })
    
    return {"nodes": nodos, "edges": edges}

def construir_arbol_consulta(pregunta: str, contextos_ids: List[str], referencia_temporal: Optional[str] = None, 
                           factor_refuerzo: float = 1.0, momento_consulta: Optional[datetime] = None) -> Dict:
    """Construye subgrafo considerando momento de consulta y similitud estructural."""
    if not contextos_ids:
        return {"nodes": [], "edges": [], "meta": {"error": "No hay contextos"}}
    
    if momento_consulta is None:
        momento_consulta = datetime.now()
    
    raiz_id = "consulta"
    ref_dt = datetime.fromisoformat(referencia_temporal) if referencia_temporal else momento_consulta
    claves_pregunta = set(extraer_palabras_clave(pregunta))
    
    # Nodo raíz con momento de consulta
    pregunta_corta = pregunta[:50] + "..." if len(pregunta) > 50 else pregunta
    momento_str = momento_consulta.strftime("%d/%m %H:%M")
    
    nodos = [{
        "id": raiz_id,
        "label": f"❓ {pregunta_corta}",
        "title": f"Pregunta: {pregunta}\nConsultado: {momento_str}",
        "group": "pregunta"
    }]
    
    edges = []
    
    for cid in contextos_ids:
        meta = metadatos_contextos.get(cid, {})
        if not meta:
            continue
        
        # Nodo contexto con información temporal
        titulo = meta.get("titulo", f"Contexto {cid}")
        tipo_contexto = meta.get("tipo_contexto", "general")
        
        iconos_tipo = {
            "reunion": "👥", "tarea": "📋", "evento": "🎯",
            "proyecto": "🚀", "conocimiento": "📚", "general": "📄"
        }
        
        icono = iconos_tipo.get(tipo_contexto, "📄")
        titulo_con_icono = f"{icono} {titulo[:25]}{'...' if len(titulo) > 25 else ''}"
        
        # Información temporal en tooltip
        tooltip_info = f"{titulo}\n{meta.get('texto', '')[:100]}...\nTipo: {tipo_contexto}"
        if meta.get("timestamp"):
            fecha_contexto = datetime.fromisoformat(meta["timestamp"])
            tooltip_info += f"\nFecha contexto: {fecha_contexto.strftime('%d/%m %H:%M')}"
            
            # Calcular diferencia con momento consulta
            diff_hours = (momento_consulta - fecha_contexto).total_seconds() / 3600
            if abs(diff_hours) < 24:
                tooltip_info += f" ({diff_hours:+.1f}h rel. consulta)"
            else:
                diff_days = diff_hours / 24
                tooltip_info += f" ({diff_days:+.1f}d rel. consulta)"
        
        nodos.append({
            "id": cid,
            "label": titulo_con_icono,
            "title": tooltip_info,
            "group": "temporal" if meta.get("es_temporal") else "atemporal",
            "es_temporal": bool(meta.get("es_temporal")),
            "tipo_contexto": tipo_contexto
        })
        
        # Calcular pesos usando similitud estructural
        claves_ctx = set(meta.get("palabras_clave", []))
        texto_ctx = meta.get("texto", "")
        
        ws = _calcular_similitud_estructural(claves_pregunta, claves_ctx, pregunta, texto_ctx)
        
        # Relevancia temporal desde momento de consulta al contexto
        ts = meta.get("timestamp")
        rt = _calcular_relevancia_temporal(
            momento_consulta.isoformat(), 
            ts, 
            "general",  # Tipo consulta genérico
            tipo_contexto
        ) if ts else 0.0
        
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
            "momento_consulta": momento_consulta.isoformat(),
            "contextos_procesados": len(contextos_ids),
            "pregunta_original": pregunta
        }
    }

def analizar_consulta_completa(pregunta: str, momento_consulta: Optional[datetime] = None) -> Dict:
    """Análisis completo con contexto de momento de consulta."""
    if momento_consulta is None:
        momento_consulta = datetime.now()
    
    # Analizar intención temporal con contexto
    analisis_intencion = analizar_intencion_temporal(pregunta, momento_consulta)
    
    referencia_temporal = analisis_intencion.get('timestamp_referencia')
    factor_refuerzo = analisis_intencion.get('factor_refuerzo_temporal', 1.0)
    ventana_temporal = analisis_intencion.get('ventana_temporal')
    
    # Obtener contextos relevantes
    from agent.semantica import buscar_similares
    try:
        ids_candidatos = buscar_similares(pregunta, k=10)
    except Exception as e:
        print(f"Error en búsqueda semántica: {e}")
        ids_candidatos = []
    
    # Filtrar por ventana temporal si existe
    ids_similares = ids_candidatos
    contextos_filtrados_temporalmente = 0
    
    if ventana_temporal and ventana_temporal.get('inicio') and ventana_temporal.get('fin'):
        ventana_inicio = ventana_temporal['inicio']
        ventana_fin = ventana_temporal['fin']
        
        # Filtrar contextos por ventana temporal
        ids_en_ventana = [
            ctx_id for ctx_id in ids_candidatos 
            if _contexto_en_ventana_temporal(ctx_id, ventana_inicio, ventana_fin)
        ]
        
        if ids_en_ventana:
            ids_similares = ids_en_ventana[:5]
            contextos_filtrados_temporalmente = len(ids_candidatos) - len(ids_en_ventana)
        else:
            ids_similares = ids_candidatos[:5]
    else:
        ids_similares = ids_candidatos[:5]
    
    # Construir árbol
    if ids_similares:
        arbol = construir_arbol_consulta(pregunta, ids_similares, referencia_temporal, factor_refuerzo, momento_consulta)
    else:
        arbol = {"nodes": [], "edges": [], "meta": {"error": "No se encontraron contextos relevantes"}}
    
    return {
        "analisis_intencion": analisis_intencion,
        "contextos_recuperados": ids_similares,
        "arbol_consulta": arbol,
        "estrategia_aplicada": {
            "intencion_temporal": analisis_intencion['intencion_temporal'],
            "factor_refuerzo": factor_refuerzo,
            "referencia_temporal": referencia_temporal,
            "momento_consulta": momento_consulta.isoformat(),
            "ventana_temporal_aplicada": ventana_temporal is not None,
            "contextos_filtrados_temporalmente": contextos_filtrados_temporalmente
        }
    }

def _contexto_en_ventana_temporal(contexto_id: str, ventana_inicio: str, ventana_fin: str) -> bool:
    """Verifica si un contexto está dentro de la ventana temporal especificada."""
    meta = metadatos_contextos.get(contexto_id, {})
    timestamp = meta.get("timestamp")
    
    if not timestamp:
        return False
    
    try:
        fecha_contexto = datetime.fromisoformat(timestamp)
        fecha_inicio = datetime.fromisoformat(ventana_inicio)
        fecha_fin = datetime.fromisoformat(ventana_fin)
        
        return fecha_inicio <= fecha_contexto <= fecha_fin
    except (ValueError, TypeError):
        return False