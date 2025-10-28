# agent/grafo.py - Versión limpia y optimizada
import networkx as nx
import pickle
import json
import os
import uuid
import threading
import math
from datetime import datetime, timedelta
import time
from typing import Dict, List, Optional, Set
from agent.extractor import extraer_palabras_clave
from agent.semantica import indexar_documento, coleccion
from agent.temporal_parser import extraer_referencias_del_texto, parsear_referencia_temporal
from agent.temporal_llm_parser import analizar_temporalidad_con_llm
from agent.visualizador_doble import VisualizadorDobleNivel
from agent.fragmentador import fragmentar_conversacion
from agent.propagacion import crear_propagador, propagar_desde_consulta_integrado
from agent.utils import parse_iso_datetime_safe
from agent.utils import normalizar_timestamp_para_guardar
from agent.pdf_processor import fragmentar_texto_pdf, crear_attachment_pdf
from agent.semantica import calcular_similitudes_batch
from agent.semantica import indexar_documentos_batch
from agent.semantica import verificar_estado_coleccion

# Variable global para el propagador
propagador_global = None

# Nuevas estructuras de datos
conversaciones_metadata = {}
fragmentos_metadata = {}

# Umbral mínimo para crear relaciones
UMBRAL_SIMILITUD = 0.5

def _actualizar_relaciones_incremental(nodo_nuevo: str) -> Dict:
    """
    VERSIÓN OPTIMIZADA - Actualiza relaciones usando batch de similitudes.
    Esto evita cálculos individuales y usa el poder de ChromaDB.
    """
    parametros = usar_parametros_configurables()
    umbral_actual = parametros.get('umbral_similitud', UMBRAL_SIMILITUD)
    inicio_tiempo = time.time()
    
    # Obtener todos los nodos excepto el nuevo
    nodos_existentes = [n for n in grafo_contextos.nodes() if n != nodo_nuevo]
    
    if not nodos_existentes:
        return {
            "tipo_actualizacion": "incremental",
            "nodo_procesado": nodo_nuevo,
            "nodos_comparados": 0,
            "conexiones_creadas": 0,
            "tiempo_ms": 0,
            "total_nodos_grafo": 1,
            "total_relaciones_grafo": 0,
        }
    
    # Metadatos del nodo nuevo
    metadatos_nuevo = metadatos_contextos.get(nodo_nuevo, {})
    claves_nuevo = set(metadatos_nuevo.get("palabras_clave", []))
    fecha_nuevo = metadatos_nuevo.get("timestamp")
    tipo_nuevo = metadatos_nuevo.get("tipo_contexto", "general")
    texto_nuevo = metadatos_nuevo.get("texto", "")
    
    conexiones_creadas = 0
    
    # Calcular TODAS las similitudes semánticas en UN SOLO BATCH
    similitudes_semanticas = calcular_similitudes_batch(texto_nuevo, nodos_existentes)
    
    # Ahora iterar sobre nodos existentes usando las similitudes pre-calculadas
    for nodo_existente in nodos_existentes:
        metadatos_existente = metadatos_contextos.get(nodo_existente, {})
        claves_existente = set(metadatos_existente.get("palabras_clave", []))
        fecha_existente = metadatos_existente.get("timestamp")
        tipo_existente = metadatos_existente.get("tipo_contexto", "general")
        texto_existente = metadatos_existente.get("texto", "")
        
        # Calcular similitud Jaccard (rápido, no necesita optimización)
        similitud_jaccard = _calcular_similitud_jaccard(claves_nuevo, claves_existente)
        
        # Obtener similitud semántica del batch (ya calculada)
        similitud_semantica = similitudes_semanticas.get(nodo_existente, 0.0)
        
        # Calcular similitud estructural (promedio)
        similitud_estructural = (similitud_jaccard + similitud_semantica) / 2
        
        # Calcular relevancia temporal
        relevancia_temporal = _calcular_relevancia_temporal(
            fecha_nuevo, fecha_existente, tipo_nuevo, tipo_existente
        )
        
        # Calcular peso efectivo
        peso_efectivo_bruto = similitud_estructural * (1 + relevancia_temporal)
        peso_efectivo = peso_efectivo_bruto / (1 + peso_efectivo_bruto) # Normalizar a [0,1]
        
        # Solo crear arista si supera el umbral
        if similitud_estructural > umbral_actual:
            datos_arista = {
                "peso_estructural": round(similitud_estructural, 3),
                "relevancia_temporal": round(relevancia_temporal, 3),
                "peso_efectivo": round(peso_efectivo, 3),
                "tipo": "semantica_temporal" if (fecha_nuevo and fecha_existente) else "semantica",
                "tipos_contexto": f"{tipo_nuevo}-{tipo_existente}"
            }
            
            # Crear aristas bidireccionales
            grafo_contextos.add_edge(nodo_nuevo, nodo_existente, **datos_arista)
            grafo_contextos.add_edge(nodo_existente, nodo_nuevo, **datos_arista)
            conexiones_creadas += 1
    
    tiempo_transcurrido = time.time() - inicio_tiempo
    relaciones_unicas = len(grafo_contextos.edges()) // 2
    
    estadisticas = {
        "tipo_actualizacion": "incremental",
        "nodo_procesado": nodo_nuevo,
        "nodos_comparados": len(nodos_existentes),
        "conexiones_creadas": conexiones_creadas,
        "tiempo_ms": round(tiempo_transcurrido * 1000, 2),
        "total_nodos_grafo": len(grafo_contextos.nodes()),
        "total_relaciones_grafo": relaciones_unicas,
    }
    
    return estadisticas

def agregar_conversacion(titulo: str, contenido: str, fecha: str = None, 
                        participantes: List[str] = None, metadata: Dict = None, attachments: Optional[List[Dict]] = None ) -> Dict:
    """
    Agrega una conversación completa con actualización incremental por fragmento.
    VERSIÓN OPTIMIZADA CON BATCH PROCESSING
    """
    # Normalizar fecha
    fecha_normalizada = None
    
    # Caso 1: Conversación explícitamente atemporal
    if fecha == 'ATEMPORAL':
        fecha_normalizada = None
        print(f"⚪ Conversación ATEMPORAL - sin timestamp")
    
    # Caso 2: Conversación con fecha específica
    elif fecha and fecha.strip():  # ✅ Verificar que no sea string vacío
        fecha_normalizada = normalizar_timestamp_para_guardar(fecha)
        if not fecha_normalizada:
            # Si no se puede normalizar, rechazar (no usar fecha actual)
            raise ValueError(f"Formato de fecha inválido: {fecha}")
        print(f"✅ Fecha normalizada: {fecha_normalizada}")
    
    # Caso 3: No se especificó fecha (None o vacío) - CONVERSACIÓN NO TEMPORAL
    else:
        fecha_normalizada = None
        print(f"⚪ Conversación NO TEMPORAL - sin timestamp asignado")
    
    print(f"📋 Resultado final - Fecha: {fecha_normalizada}")

    # Preparar datos de conversación
    conversacion_data = {
        'titulo': titulo,
        'contenido': contenido,
        'fecha': fecha_normalizada,
        'participantes': participantes or [],
        'metadata': metadata or {}
    }
    
    # Fragmentar conversación
    fragmentos = fragmentar_conversacion(conversacion_data)
    
    if not fragmentos:
        raise ValueError("No se pudieron generar fragmentos de esta conversación")
    
    conversacion_id = fragmentos[0]['metadata']['conversacion_id']
    fragmentos_ids = []
    estadisticas_actualizacion = []
    
    # Agregar conversación a metadatos
    conversaciones_metadata[conversacion_id] = {
        'titulo': titulo,
        'fecha': fecha_normalizada,
        'participantes': participantes or [],
        'metadata': metadata or {},
        'total_fragmentos': len(fragmentos),
        'fragmentos_ids': [f['id'] for f in fragmentos],
        'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    }
    
    print(f"📝 Procesando conversación '{titulo}' con {len(fragmentos)} fragmentos...")
    
    # Recolectar todos los fragmentos para indexado batch
    fragmentos_para_indexar_ids = []
    fragmentos_para_indexar_textos = []
    
    # Procesar cada fragmento - PRIMERO preparar todo sin indexar
    for i, fragmento in enumerate(fragmentos):
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
            "es_fragmento": True,
            "conversacion_id": conversacion_id,
            "posicion_fragmento": frag_meta['posicion_en_conversacion']
        }
        
        # Agregar a lista para indexado batch (NO indexar ahora)
        fragmentos_para_indexar_ids.append(frag_id)
        fragmentos_para_indexar_textos.append(frag_meta['texto'])
        
        fragmentos_ids.append(frag_id)
    
    # INDEXAR TODOS LOS FRAGMENTOS EN UN SOLO BATCH
    if fragmentos_para_indexar_ids:
        print(f"Indexando {len(fragmentos_para_indexar_ids)} fragmentos en batch...")
        indexar_documentos_batch(fragmentos_para_indexar_ids, fragmentos_para_indexar_textos)
    
    # AHORA sí, calcular relaciones incrementales para cada fragmento
    for i, fragmento in enumerate(fragmentos):
        frag_id = fragmento['id']
        
        # ACTUALIZACIÓN INCREMENTAL para este fragmento
        stats_frag = _actualizar_relaciones_incremental(frag_id)
        estadisticas_actualizacion.append(stats_frag)
        
        # Mostrar progreso cada 3 fragmentos
        if (i + 1) % 3 == 0:
            print(f"  ✅ Fragmento {i+1}/{len(fragmentos)}: {stats_frag['conexiones_creadas']} conexiones creadas")
    
    # PROCESAR ATTACHMENTS (PDFs)
    fragmentos_pdf_ids = []
    estadisticas_pdf = []
    
    if attachments:
        print(f"Procesando {len(attachments)} attachment(s) para conversación '{titulo}'")
        
        # Lista para batch de PDFs
        fragmentos_pdf_para_indexar_ids = []
        fragmentos_pdf_para_indexar_textos = []
        
        for att_idx, attachment in enumerate(attachments):
            if not attachment.get('extracted_text'):
                print(f"⚠️ Attachment {att_idx} sin texto extraído, saltando...")
                continue
            
            # Fragmentar texto del PDF
            texto_pdf = attachment['extracted_text']
            fragmentos_texto_pdf = fragmentar_texto_pdf(texto_pdf, max_palabras=500)
            
            print(f"📄 PDF '{attachment['filename']}' generó {len(fragmentos_texto_pdf)} fragmentos")
            
            for frag_idx, fragmento_texto in enumerate(fragmentos_texto_pdf):
                # Crear ID único para este fragmento de PDF
                fragmento_id = f"{conversacion_id}_pdf_{att_idx}_{frag_idx}"
                
                # Crear metadata del fragmento PDF
                metadata_fragmento = {
                    'conversacion_id': conversacion_id,
                    'titulo_conversacion': titulo,
                    'tipo': 'pdf_fragment',
                    'titulo': f"{titulo} - {attachment['filename']} (Frag. {frag_idx+1}/{len(fragmentos_texto_pdf)})",
                    'source_document': attachment['filename'],
                    'position_in_doc': frag_idx,
                    'total_fragmentos_pdf': len(fragmentos_texto_pdf),
                    'texto': fragmento_texto,
                    'palabras_clave': extraer_palabras_clave(fragmento_texto),
                    'created_at': datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
                    'es_temporal': fecha_normalizada is not None,
                    'timestamp': fecha_normalizada if fecha_normalizada else None,
                    'tipo_contexto': 'documento',
                    'es_fragmento': True,
                    'es_pdf': True
                }
                
                # Agregar nodo al grafo
                titulo_fragmento = f"{titulo} - PDF: {attachment['filename']} (p.{frag_idx+1})"
                grafo_contextos.add_node(fragmento_id, titulo=titulo_fragmento)
                
                # Guardar en metadatos de fragmentos
                fragmentos_metadata[fragmento_id] = metadata_fragmento
                
                # Mantener compatibilidad con metadatos_contextos
                metadatos_contextos[fragmento_id] = metadata_fragmento
                
                # Agregar a lista para indexado batch
                fragmentos_pdf_para_indexar_ids.append(fragmento_id)
                fragmentos_pdf_para_indexar_textos.append(fragmento_texto)
                
                fragmentos_pdf_ids.append(fragmento_id)
        
        # INDEXAR FRAGMENTOS PDF EN BATCH
        if fragmentos_pdf_para_indexar_ids:
            print(f"Indexando {len(fragmentos_pdf_para_indexar_ids)} fragmentos PDF en batch...")
            indexar_documentos_batch(fragmentos_pdf_para_indexar_ids, fragmentos_pdf_para_indexar_textos)
        
        # AHORA calcular relaciones para PDFs
        for fragmento_id in fragmentos_pdf_ids:
            stats_pdf = _actualizar_relaciones_incremental(fragmento_id)
            estadisticas_pdf.append(stats_pdf)
        
        print(f"✅ Procesados {len(fragmentos_pdf_ids)} fragmentos PDF con relaciones calculadas")
    
    # Actualizar IDs de conversación con PDFs
    conversaciones_metadata[conversacion_id]['fragmentos_ids'].extend(fragmentos_pdf_ids)
    conversaciones_metadata[conversacion_id]['total_fragmentos'] += len(fragmentos_pdf_ids)
    
    # Guardar todo (una sola vez al final)
    guardar_conversaciones_en_disco()
    _guardar_grafo_con_propagador()  #Guardar con propagador solo al final
    
    # Preparar estadísticas finales
    total_conexiones = sum(s['conexiones_creadas'] for s in estadisticas_actualizacion)
    total_conexiones += sum(s['conexiones_creadas'] for s in estadisticas_pdf)
    
    resultado = {
        'conversacion_id': conversacion_id,
        'total_fragmentos': len(fragmentos) + len(fragmentos_pdf_ids),
        'fragmentos_conversacion': len(fragmentos),
        'fragmentos_pdf': len(fragmentos_pdf_ids),
        'total_conexiones_creadas': total_conexiones,
        'fragmentos_ids': conversaciones_metadata[conversacion_id]['fragmentos_ids']
    }
    
    print(f"Conversación '{titulo}' agregada exitosamente")
    print(f"Total fragmentos: {resultado['total_fragmentos']}")
    print(f"Conexiones creadas: {total_conexiones}")

    # Al final de agregar_conversacion, antes del return
    verificar_estado_coleccion()
    
    return resultado

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

def usar_parametros_configurables():
    """Función para usar parámetros desde main.py si están disponibles."""
    try:
        # Intentar importar parámetros desde main
        import main
        return main.parametros_sistema
    except (ImportError, AttributeError) as e:
        print(f"⚠️  No se pudieron cargar parámetros configurables: {e}")
        # Usar valores por defecto si no están disponibles
        return {
            'umbral_similitud': 0.5,
            'k_resultados': 5,
            'factor_refuerzo_temporal': 1.5
        }

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

def _calcular_similitud_estructural(claves_a: Set[str], claves_b: Set[str], texto_a: str, texto_b: str) -> float:
    """
    Calcula similitud estructural como el promedio de similitud Jaccard y semántica.
    NOTA: Esta función ya NO se usa en _actualizar_relaciones_incremental optimizada,
    pero se mantiene por compatibilidad con recalcular_relaciones().
    """
    # Calcular Jaccard
    similitud_jaccard = _calcular_similitud_jaccard(claves_a, claves_b)
    
    # Para similitud semántica, usar un cálculo directo simple
    # (no podemos usar batch aquí porque solo comparamos 2 textos)
    try:
        # Indexar temporalmente texto_a
        temp_id = f"temp_{hash(texto_a)}"
        indexar_documento(temp_id, texto_a)
        
        # Buscar similitud con texto_b
        resultado = coleccion.query(
            query_texts=[texto_b],
            n_results=10,
            include=['distances']
        )
        
        similitud_semantica = 0.0
        if temp_id in resultado['ids'][0]:
            index = resultado['ids'][0].index(temp_id)
            distance = resultado['distances'][0][index]
            similitud_semantica = max(0.0, 1.0 - distance / 2.0)
        
        # Limpiar temporal
        try:
            coleccion.delete(ids=[temp_id])
        except:
            pass
            
    except Exception as e:
        print(f"Error en similitud semántica: {e}")
        similitud_semantica = 0.0
    
    # Promedio
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
    """
    VERSIÓN OPTIMIZADA: Recalcula todas las relaciones usando batch processing.
    Mucho más rápido que el método original.
    """
    print("Iniciando recálculo optimizado de relaciones...")
    inicio_total = time.time()
    
    # Limpiar todas las aristas
    grafo_contextos.clear_edges()
    nodos = list(grafo_contextos.nodes())
    total_nodos = len(nodos)
    
    print(f"Recalculando relaciones para {total_nodos} nodos...")
    print(f"⚙️  Umbral de similitud: {UMBRAL_SIMILITUD}")
    
    pares_unicos_creados = 0
    total_comparaciones = (total_nodos * (total_nodos - 1)) // 2
    comparaciones_realizadas = 0
    
    # Procesar por lotes de nodos para mejor progreso visual
    BATCH_SIZE = 10
    
    for i in range(0, total_nodos, BATCH_SIZE):
        batch_nodos = nodos[i:min(i + BATCH_SIZE, total_nodos)]
        
        for idx_en_batch, nodo_a in enumerate(batch_nodos):
            nodo_idx_global = i + idx_en_batch
            
            metadatos_a = metadatos_contextos.get(nodo_a, {})
            claves_a = set(metadatos_a.get("palabras_clave", []))
            fecha_a = metadatos_a.get("timestamp")
            tipo_a = metadatos_a.get("tipo_contexto", "general")
            texto_a = metadatos_a.get("texto", "")
            
            # Obtener todos los nodos posteriores para comparar
            nodos_restantes = nodos[nodo_idx_global + 1:]
            
            if not nodos_restantes:
                continue
            
            # Calcular TODAS las similitudes semánticas en UN SOLO BATCH
            similitudes_semanticas = calcular_similitudes_batch(texto_a, nodos_restantes)
            
            # Ahora iterar sobre nodos restantes con similitudes pre-calculadas
            for nodo_b in nodos_restantes:
                metadatos_b = metadatos_contextos.get(nodo_b, {})
                claves_b = set(metadatos_b.get("palabras_clave", []))
                fecha_b = metadatos_b.get("timestamp")
                tipo_b = metadatos_b.get("tipo_contexto", "general")
                
                # Calcular Jaccard (rápido)
                similitud_jaccard = _calcular_similitud_jaccard(claves_a, claves_b)
                
                # Obtener similitud semántica del batch (ya calculada)
                similitud_semantica = similitudes_semanticas.get(nodo_b, 0.0)
                
                # Calcular similitud estructural (promedio)
                similitud_estructural = (similitud_jaccard + similitud_semantica) / 2
                
                # Calcular relevancia temporal
                relevancia_temporal = _calcular_relevancia_temporal(
                    fecha_a, fecha_b, tipo_a, tipo_b
                )
                
                # Calcular peso efectivo
                peso_efectivo_bruto = similitud_estructural * (1 + relevancia_temporal)
                peso_efectivo = peso_efectivo_bruto / (1 + peso_efectivo_bruto)
                
                # Solo crear arista si supera el umbral
                if similitud_estructural > UMBRAL_SIMILITUD:
                    datos_arista = {
                        "peso_estructural": round(similitud_estructural, 3),
                        "relevancia_temporal": round(relevancia_temporal, 3),
                        "peso_efectivo": round(peso_efectivo, 3),
                        "tipo": "semantica_temporal" if (fecha_a and fecha_b) else "semantica",
                        "tipos_contexto": f"{tipo_a}-{tipo_b}"
                    }
                    
                    # Crear aristas bidireccionales
                    grafo_contextos.add_edge(nodo_a, nodo_b, **datos_arista)
                    grafo_contextos.add_edge(nodo_b, nodo_a, **datos_arista)
                    pares_unicos_creados += 1
                
                comparaciones_realizadas += 1
            
            # Mostrar progreso cada 5 nodos
            if (nodo_idx_global + 1) % 5 == 0:
                porcentaje = (comparaciones_realizadas / total_comparaciones) * 100
                print(f"  📈 Progreso: {nodo_idx_global + 1}/{total_nodos} nodos | "
                      f"{porcentaje:.1f}% completado | "
                      f"Relaciones creadas: {pares_unicos_creados}")
    
    tiempo_total = time.time() - inicio_total
    
    print(f"\n✅ Recálculo completado en {tiempo_total:.2f} segundos")
    print(f"Pares únicos creados: {pares_unicos_creados}")
    print(f"Total aristas direccionales: {grafo_contextos.number_of_edges()}")
    print(f"Comparaciones procesadas: {comparaciones_realizadas:,}")
    
    return {
        "pares_creados": pares_unicos_creados,
        "tiempo_segundos": round(tiempo_total, 2),
        "comparaciones": comparaciones_realizadas
    }

def _guardar_grafo():
    """Guarda el grafo y metadatos en disco - VERSIÓN OPTIMIZADA."""
    with _lock:
        os.makedirs("data", exist_ok=True)
        
        with open(ARCHIVO_GRAFO, 'wb') as f:
            pickle.dump(grafo_contextos, f)
        
        with open(ARCHIVO_METADATOS, 'w', encoding='utf-8') as f:
            json.dump(metadatos_contextos, f, ensure_ascii=False, indent=2)

        # NO llamar a actualizar_propagador() aquí - se hará al final de cada conversación

# guardar al final del batch
def _guardar_grafo_con_propagador():
    """Guarda el grafo Y actualiza el propagador (solo al final de conversaciones completas)."""
    _guardar_grafo()
    actualizar_propagador()

def guardar_conversaciones_en_disco():
    """Guarda metadatos de conversaciones y fragmentos en disco."""
    os.makedirs("data", exist_ok=True)
    
    with open("data/conversaciones.json", 'w', encoding='utf-8') as f:
        json.dump(conversaciones_metadata, f, ensure_ascii=False, indent=2)
    
    with open("data/fragmentos.json", 'w', encoding='utf-8') as f:
        json.dump(fragmentos_metadata, f, ensure_ascii=False, indent=2)

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
    
    # Cargar también conversaciones y fragmentos
    cargar_conversaciones_desde_disco()

    #Inicializar propagador después de cargar
    actualizar_propagador()

def agregar_contexto(titulo: str, texto: str, es_temporal: bool = None, referencia_temporal: str = None) -> str:
    """Agrega un nuevo contexto con prevención de duplicados y actualización incremental."""
    # PREVENCIÓN DE DUPLICADOS - Verificación antes de agregar
    titulo_norm = titulo.strip().lower()
    texto_norm = " ".join(texto.strip().lower().split())
    
    for ctx_id, meta in metadatos_contextos.items():
        titulo_existente = meta.get("titulo", "").strip().lower()
        texto_existente = " ".join(meta.get("texto", "").strip().lower().split())
        
        # Verificar duplicado exacto o muy similar
        if (titulo_norm == titulo_existente and texto_norm == texto_existente) or \
           (len(texto_norm) > 50 and _calcular_similitud_textual_exacta(texto_norm, texto_existente) > 0.98):
            print(f"Contexto duplicado detectado - no agregando. Retornando ID existente: {ctx_id}")
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
        "created_at": datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
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
            #NORMALIZAR TIMESTAMP ANTES DE GUARDAR
            timestamp_normalizado = normalizar_timestamp_para_guardar(timestamp_usado)
            metadatos["timestamp"] = timestamp_normalizado if timestamp_normalizado else datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        else:
            metadatos["timestamp"] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    metadatos_contextos[id_contexto] = metadatos
    
    # Indexar para búsqueda semántica
    indexar_documento(id_contexto, texto)
    
    # ACTUALIZACIÓN INCREMENTAL en lugar de recálculo completo
    stats_actualizacion = _actualizar_relaciones_incremental(id_contexto)
    
    _guardar_grafo()
    
    # Mostrar estadísticas de la actualización
    print(f"✅ Contexto agregado: {titulo[:50]}...")
    print(f"   🔗 Conexiones creadas: {stats_actualizacion['conexiones_creadas']}")
    print(f"   ⚡ Tiempo: {stats_actualizacion['tiempo_ms']}ms")
    print(f"   📊 Total relaciones: {stats_actualizacion['total_relaciones_grafo']}")
    
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
            es_pdf = metadatos.get("es_pdf", False)
            
            # Emoji por tipo de contexto
            if es_pdf:
                # 📄 NODO DE PDF con información de fragmento
                source_doc = metadatos.get('source_document', 'documento.pdf')
                posicion = metadatos.get('position_in_doc', 0)
                total_frags = metadatos.get('total_fragmentos_pdf', 1)
                
                icono = "📄"
                titulo_con_icono = f"{icono} {source_doc} ({posicion+1}/{total_frags})"
                
                tooltip = f"Documento: {source_doc}\n"
                tooltip += f"Fragmento: {posicion+1} de {total_frags}\n"
                tooltip += f"{metadatos.get('texto', '')[:150]}...\n"
                tooltip += f"Tipo: documento PDF"
                
                # Color especial para PDFs
                group = "pdf"
            else:
                # Nodo de conversación normal
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
                
                tooltip = f"{metadatos.get('titulo', '')}\n{metadatos.get('texto', '')[:100]}...\nTipo: {tipo_contexto}"
                
                group = "temporal" if es_temporal else "atemporal"
            
            nodos.append({
                "id": nodo_id,
                "label": titulo_con_icono,
                "title": tooltip,
                "group": group,
                "es_temporal": es_temporal,
                "tipo_contexto": tipo_contexto,
                "es_pdf": es_pdf
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
        title = f"Peso Estructural: {peso_estructural:.2f}\nRelevancia Temporal: {relevancia_temporal:.2f}\nPeso Efectivo: {peso_efectivo:.2f}\nTipos: {tipos_contexto}"
        
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
    print(f"🔧 CONSTRUYENDO ÁRBOL con factor_refuerzo: {factor_refuerzo}")

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
        
        # ESTRATEGIA ADAPTATIVA: Detectar si estamos en consulta temporal
        # Obtener intención desde atributo temporal de la función (se setea externamente)
        intencion = getattr(construir_arbol_consulta, '_intencion_actual', 'ESTRUCTURAL')
        
        # Calcular peso efectivo según estrategia
        if intencion == "TEMPORAL" and rt > 0.5:
            # 🕐 Fórmula temporal: base temporal + bonus semántico
            we = rt * factor_refuerzo * (1 + ws)
            estrategia_usada = "TEMPORAL"
        else:
            # 📚 Fórmula estructural/mixta: base semántica + bonus temporal
            we = ws * (1 + rt * factor_refuerzo)
            estrategia_usada = "ESTRUCTURAL/MIXTA"

        # Normalizar a [0,1] usando función sigmoidea suave
        we = min(1.0, we / (1 + we))  # Normalización sigmoidea

        print(f"📊 Contexto {cid[:8]}: estrategia={estrategia_usada}, ws={ws:.3f}, rt={rt:.3f}, factor={factor_refuerzo}, we={we:.3f}")
        
        edges.append({
            "from": raiz_id,
            "to": cid,
            "peso_estructural": round(ws, 3),
            "relevancia_temporal": round(rt, 3),
            "peso_efectivo": round(we, 3),
            "label": f"E:{max(0.001, ws):.3f}|T:{max(0.001, rt) if rt > 0 else 0:.3f}|W:{max(0.001, we):.3f}"
        })

    edges_ordenadas = sorted(edges, key=lambda e: e['peso_efectivo'], reverse=True)
    
    return {
        "nodes": nodos,
        "edges": edges_ordenadas,
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
    
    # Obtener factor base configurado
    parametros = usar_parametros_configurables()
    factor_base = parametros.get('factor_refuerzo_temporal', 1.5)
    
    # Analizar intención temporal con contexto MEJORADO
    analisis_intencion = analizar_temporalidad_con_llm(
        pregunta, 
        momento_consulta,
        factor_base=factor_base
    )
    
    referencia_temporal = analisis_intencion.get('timestamp_referencia')
    parametros = usar_parametros_configurables()
    factor_refuerzo = parametros.get('factor_refuerzo_temporal', 1.5)
    ventana_temporal = analisis_intencion.get('ventana_temporal')
    
    # Obtener contextos relevantes usando parámetros configurables
    parametros = usar_parametros_configurables()
    k_busqueda = parametros.get('k_resultados', 5)
    
    from agent.semantica import buscar_similares
    try:
        # BUSCAR MÁS CONTEXTOS INICIALMENTE para mayor diversidad
        ids_candidatos = buscar_similares(pregunta, k=k_busqueda * 3)  # 3x más candidatos
    except Exception as e:
        print(f"❌ Error en búsqueda semántica: {e}")
        ids_candidatos = []
    
    # 🔍 LOGGING: Mostrar contextos candidatos
    print(f"\n📋 CONTEXTOS CANDIDATOS (top {min(10, len(ids_candidatos))}):")
    for i, ctx_id in enumerate(ids_candidatos[:10]):
        if ctx_id in metadatos_contextos:
            titulo = metadatos_contextos[ctx_id].get('titulo', 'Sin título')[:60]
            es_temp = metadatos_contextos[ctx_id].get('es_temporal', False)
            print(f"   {i+1}. {'⏰' if es_temp else '📄'} {titulo}")

    # Filtrar por ventana temporal si existe
    ids_similares = ids_candidatos
    contextos_filtrados_temporalmente = 0
    
    if ventana_temporal and ventana_temporal.get('inicio') and ventana_temporal.get('fin'):
        ventana_inicio = ventana_temporal['inicio']
        ventana_fin = ventana_temporal['fin']
        
        print(f"\n🔍 APLICANDO FILTRO TEMPORAL:")
        print(f"   Ventana: {ventana_inicio} → {ventana_fin}")
        
        # Filtrar contextos por ventana temporal
        ids_en_ventana = []
        
        for ctx_id in ids_candidatos:
            meta = metadatos_contextos.get(ctx_id, {})
            timestamp = meta.get("timestamp")
            
            if timestamp:
                try:
                    # USAR EL PARSER MEJORADO
                    from agent.utils import parse_iso_datetime_safe
                    
                    fecha_contexto = parse_iso_datetime_safe(timestamp)
                    fecha_inicio = parse_iso_datetime_safe(ventana_inicio)  
                    fecha_fin = parse_iso_datetime_safe(ventana_fin)

                    # VERIFICACIÓN ADICIONAL: Asegurar que todas las fechas son naive
                    if fecha_contexto and fecha_contexto.tzinfo is not None:
                        fecha_contexto = fecha_contexto.replace(tzinfo=None)
                    if fecha_inicio and fecha_inicio.tzinfo is not None:
                        fecha_inicio = fecha_inicio.replace(tzinfo=None)
                    if fecha_fin and fecha_fin.tzinfo is not None:
                        fecha_fin = fecha_fin.replace(tzinfo=None)
                    
                    if not fecha_contexto or not fecha_inicio or not fecha_fin:
                        continue
                    
                    # Verificar si está en ventana
                    if fecha_inicio <= fecha_contexto <= fecha_fin:
                        ids_en_ventana.append(ctx_id)
                        contexto_titulo = meta.get("titulo", "Sin título")[:30]
                        print(f"   ✓ {ctx_id[:8]}... '{contexto_titulo}' INCLUIDO")
                        
                except Exception as e:
                    print(f"   ⚠️ Error procesando {ctx_id[:8]}...: {e}")
                    continue
            else:
                print(f"   ⚠️ Contexto {ctx_id[:8]}... sin timestamp - EXCLUIDO")
        
        if ids_en_ventana:
            ids_similares = ids_en_ventana[:k_busqueda]
            contextos_filtrados_temporalmente = len(ids_candidatos) - len(ids_en_ventana)
            print(f"\n   ✅ {len(ids_en_ventana)} contextos en ventana → seleccionando {len(ids_similares)}")
        else:
            print(f"\n   ⚠️ NINGÚN CONTEXTO en ventana temporal. Aplicando fallback...")
            
            # FALLBACK MEJORADO: Buscar en TODOS los contextos
            contextos_con_fechas = []
            
            # PASO 1: Buscar DENTRO de la ventana en TODOS los contextos
            contextos_en_ventana_completa = []
            for ctx_id, meta in metadatos_contextos.items():
                timestamp = meta.get('timestamp')
                if timestamp:
                    from agent.utils import parse_iso_datetime_safe
                    fecha_ctx = parse_iso_datetime_safe(timestamp)
                    if fecha_ctx:
                        # Asegurar que fecha_ctx es naive
                        if fecha_ctx.tzinfo is not None:
                            fecha_ctx = fecha_ctx.replace(tzinfo=None)
                        
                        # Verificar si está en ventana
                        if fecha_inicio <= fecha_ctx <= fecha_fin:
                            contextos_en_ventana_completa.append(ctx_id)
                            titulo = meta.get('titulo', 'Sin título')
                            print(f"      ✓ Encontrado: {titulo[:40]}")
            
            if contextos_en_ventana_completa:
                # Éxito: encontramos contextos en ventana
                ids_similares = contextos_en_ventana_completa[:k_busqueda]
                print(f"\n   📅 Fallback exitoso: {len(contextos_en_ventana_completa)} contextos en ventana")
                contextos_filtrados_temporalmente = 0
            else:
                # PASO 2: Si no hay nada en ventana, buscar por proximidad
                print(f"      ⚠️ Sin contextos en ventana. Buscando por proximidad temporal...")
                
                for ctx_id, meta in metadatos_contextos.items():
                    timestamp = meta.get('timestamp')
                    if timestamp:
                        from agent.utils import parse_iso_datetime_safe
                        fecha_ctx = parse_iso_datetime_safe(timestamp)
                        if fecha_ctx:
                            diferencia = abs((momento_consulta - fecha_ctx).days)
                            contextos_con_fechas.append((ctx_id, diferencia, fecha_ctx))
                
                if contextos_con_fechas:
                    contextos_con_fechas.sort(key=lambda x: x[1])
                    
                    print(f"\n   📅 Contextos por proximidad temporal (top 10):")
                    for ctx_id, dias_diff, fecha_ctx in contextos_con_fechas[:10]:
                        meta = metadatos_contextos.get(ctx_id, {})
                        titulo = meta.get('titulo', 'Sin título')
                        print(f"      - {titulo[:40]}: {fecha_ctx.strftime('%d/%m/%Y')} (±{dias_diff} días)")
                    
                    print(f"\n   📄 Usando {min(k_busqueda, len(contextos_con_fechas))} contextos más cercanos temporalmente")
                    ids_similares = [ctx_id for ctx_id, _, _ in contextos_con_fechas[:k_busqueda]]
                    
                    contextos_filtrados_temporalmente = 0
                else:
                    # Último recurso: búsqueda semántica pura
                    print(f"\n   📄 ÚLTIMO RECURSO: Usando búsqueda semántica pura")
                    ids_similares = ids_candidatos[:k_busqueda]
                    contextos_filtrados_temporalmente = 0
    else:
        # ✅ CASO SEMÁNTICO/ESTRUCTURAL (SIN FILTRO TEMPORAL)
        print(f"\n📚 CONSULTA SEMÁNTICA/ESTRUCTURAL (sin filtro temporal)")
        ids_similares = ids_candidatos[:k_busqueda]
        contextos_filtrados_temporalmente = 0
        print(f"   Usando top {len(ids_similares)} resultados semánticos de {len(ids_candidatos)} candidatos")
    
    # Construir árbol CON INTENCIÓN
    if ids_similares:
        # Pasar intención temporal a construir_arbol_consulta
        intencion_detectada = analisis_intencion.get('intencion_temporal', 'ESTRUCTURAL')
        construir_arbol_consulta._intencion_actual = intencion_detectada
        
        print(f"\n🏗️  Construyendo árbol de consulta con intención: {intencion_detectada}")
        
        arbol = construir_arbol_consulta(pregunta, ids_similares, referencia_temporal, factor_refuerzo, momento_consulta)
    else:
        print(f"\n❌ NO SE ENCONTRARON CONTEXTOS RELEVANTES")
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
    """Verifica contexto en ventana temporal con logging mínimo."""
    meta = metadatos_contextos.get(contexto_id, {})
    timestamp = meta.get("timestamp")
    
    if not timestamp:
        # Si no tiene timestamp pero tiene referencias temporales en el texto,
        # intentar extraerlas
        texto = meta.get("texto", "")
        titulo = meta.get("titulo", "")
        texto_completo = f"{titulo} {texto}"
        
        from agent.temporal_parser import extraer_referencias_del_texto
        referencias = extraer_referencias_del_texto(texto_completo)
        
        if referencias:
            # Usar la primera referencia encontrada
            timestamp = referencias[0][1]
        else:
            print(f"⚠️ Contexto {contexto_id[:8]} sin timestamp - EXCLUIDO")
            return False
    
    try:
        # USAR EL PARSER SEGURO MEJORADO
        from agent.utils import parse_iso_datetime_safe
        
        fecha_contexto = parse_iso_datetime_safe(timestamp)
        fecha_inicio = parse_iso_datetime_safe(ventana_inicio)  
        fecha_fin = parse_iso_datetime_safe(ventana_fin)

        # VERIFICACIÓN ADICIONAL: Asegurar que todas las fechas son naive
        if fecha_contexto and fecha_contexto.tzinfo is not None:
            fecha_contexto = fecha_contexto.replace(tzinfo=None)
        if fecha_inicio and fecha_inicio.tzinfo is not None:
            fecha_inicio = fecha_inicio.replace(tzinfo=None)
        if fecha_fin and fecha_fin.tzinfo is not None:
            fecha_fin = fecha_fin.replace(tzinfo=None)
        
        if not fecha_contexto or not fecha_inicio or not fecha_fin:
            print(f"⚠️ Error parseando fechas para contexto {contexto_id[:8]}")
            print(f"   - Contexto: {timestamp} -> {fecha_contexto}")
            print(f"   - Ventana: {ventana_inicio} -> {fecha_inicio}")
            print(f"   - Ventana: {ventana_fin} -> {fecha_fin}")
            return False
        
        # Logging para debugging con más info
        contexto_titulo = meta.get("titulo", "Sin título")[:30]
        
        resultado = fecha_inicio <= fecha_contexto <= fecha_fin
    
        # LOGGING MÍNIMO - solo cuenta total
        if resultado:
            contexto_titulo = meta.get("titulo", "Sin título")[:20]
            print(f"✓ {contexto_id[:8]} '{contexto_titulo}' en ventana")
        
        return resultado
            
    except Exception as e:
        print(f"⚠️ Error procesando timestamp para contexto {contexto_id[:8]}: {timestamp} - {e}")
        return False
    
# FUNCIONES DE VISUALIZACIÓN DOBLE NIVEL
def exportar_grafo_macro_conversaciones() -> Dict:
    """Exporta vista macro: conversaciones como nodos."""
    visualizador = VisualizadorDobleNivel(
        grafo_contextos, 
        metadatos_contextos, 
        conversaciones_metadata, 
        fragmentos_metadata
    )
    
    return visualizador.generar_vista_macro_conversaciones()

def exportar_grafo_micro_fragmentos(filtro_conversacion: str = None) -> Dict:
    """Exporta vista micro: fragmentos individuales."""
    visualizador = VisualizadorDobleNivel(
        grafo_contextos, 
        metadatos_contextos, 
        conversaciones_metadata, 
        fragmentos_metadata
    )
    
    return visualizador.generar_vista_micro_fragmentos(filtro_conversacion)

def obtener_estadisticas_doble_nivel() -> Dict:
    """Estadísticas comparativas de ambos niveles de visualización."""
    visualizador = VisualizadorDobleNivel(
        grafo_contextos, 
        metadatos_contextos, 
        conversaciones_metadata, 
        fragmentos_metadata
    )
    
    return visualizador.obtener_estadisticas_doble_nivel()

def obtener_propagador():
    """Obtiene o crea la instancia global del propagador."""
    global propagador_global
    if propagador_global is None:
        propagador_global = crear_propagador(grafo_contextos, metadatos_contextos)
    return propagador_global

def actualizar_propagador():
    """Actualiza el propagador cuando cambia el grafo."""
    global propagador_global
    propagador_global = crear_propagador(grafo_contextos, metadatos_contextos)

def configurar_parametros_propagacion(factor_decaimiento: float = None, umbral_activacion: float = None):
    """Configura parámetros del algoritmo de propagación."""
    try:
        propagador = obtener_propagador()
        if propagador:
            propagador.configurar_parametros(factor_decaimiento, umbral_activacion)
            return {
                "status": "parametros_actualizados",
                "factor_decaimiento": propagador.factor_decaimiento,
                "umbral_activacion": propagador.umbral_activacion
            }
        else:
            return {"error": "Propagador no disponible"}
    except Exception as e:
        return {"error": f"Error configurando: {str(e)}"}
    
def obtener_estado_propagacion():
    """Obtiene el estado actual del sistema de propagación."""
    try:
        propagador = obtener_propagador()
        total_nodos = len(grafo_contextos.nodes())
        total_aristas = len(grafo_contextos.edges())
        
        return {
            "propagacion_habilitada": propagador is not None,
            "factor_decaimiento": propagador.factor_decaimiento if propagador else None,
            "umbral_activacion": propagador.umbral_activacion if propagador else None,
            "total_nodos": total_nodos,
            "total_aristas": total_aristas,
            "grafo_disponible": total_nodos > 0
        }
    except Exception as e:
        return {"error": f"Error: {str(e)}"}

def analizar_consulta_con_propagacion(pregunta: str, momento_consulta: Optional[datetime] = None, 
                                               usar_propagacion: bool = True, max_pasos: int = 2,
                                               factor_decaimiento: float = None, 
                                               umbral_activacion: float = None,
                                               k_inicial: int = None,
                                               factor_refuerzo_temporal_custom: float = None) -> Dict:
    """
    Análisis completo de consulta INCLUYENDO propagación dinámica desde contextos relevantes.
        pregunta: Consulta del usuario
        momento_consulta: Momento de la consulta
        usar_propagacion: Si usar propagación además de búsqueda directa
        max_pasos: Pasos de propagación
    """
    # Obtener parámetros configurables si no se especifican
    parametros = usar_parametros_configurables()
    
    if k_inicial is None:
        k_inicial = parametros.get('k_resultados', 5)
    
    if factor_refuerzo_temporal_custom is None:
        factor_refuerzo_temporal_custom = parametros.get('factor_refuerzo_temporal', 1.5)

    if momento_consulta is None:
        momento_consulta = datetime.now()
    
    # Análisis básico (método existente)
    analisis_basico = analizar_consulta_completa(pregunta, momento_consulta)
    
    if not usar_propagacion:
        return analisis_basico
    
    try:
        # USAR PROPAGADOR GLOBAL CON CONFIGURACIÓN APLICADA
        propagador = obtener_propagador()

        # APLICAR PARÁMETROS CON DEBUGGING
        if factor_decaimiento is not None or umbral_activacion is not None:
            print(f"🔧 CONFIGURANDO: factor={factor_decaimiento}, umbral={umbral_activacion}")
            propagador.configurar_parametros(factor_decaimiento, umbral_activacion)
            print(f"🔧 CONFIGURADO: factor={propagador.factor_decaimiento}, umbral={propagador.umbral_activacion}")

        # APLICAR PARÁMETROS SI SE PROPORCIONAN (sobrescribir configuración actual)
        if factor_decaimiento is not None or umbral_activacion is not None:
            propagador.configurar_parametros(factor_decaimiento, umbral_activacion)
        
        # Obtener contextos iniciales (semillas para propagación)
        contextos_directos = analisis_basico.get('contextos_recuperados', [])
        
        if not contextos_directos:
            # Si no hay contextos directos, no hay propagación
            analisis_basico['propagacion'] = {
                'contextos_directos': [],
                'contextos_indirectos': [],
                'solo_por_propagacion': [],
                'total_nodos_alcanzados': 0,
                'mensaje': 'Sin contextos base para propagación'
            }
            return analisis_basico
        
        # PROPAGACIÓN DESDE MÚLTIPLES SEMILLAS
        from agent.extractor import extraer_palabras_clave
        palabras_clave = extraer_palabras_clave(pregunta)
        
        # Propagar desde cada contexto directo encontrado
        todos_contextos_propagados = {}
        caminos_propagacion = {}
        
        for contexto_inicial in contextos_directos:
            if contexto_inicial not in metadatos_contextos:
                continue
                
            # Calcular activación inicial basada en relevancia para esta pregunta
            meta_inicial = metadatos_contextos[contexto_inicial]
            palabras_contexto = set(meta_inicial.get('palabras_clave', []))
            palabras_pregunta = set(palabras_clave)
            
            # Similitud como activación inicial
            interseccion = len(palabras_pregunta & palabras_contexto)
            union = len(palabras_pregunta | palabras_contexto)
            activacion_inicial = interseccion / union if union > 0 else 0.3
            activacion_inicial = max(0.3, min(1.0, activacion_inicial))
            print(f"🌱 PROPAGANDO desde {contexto_inicial[:8]}... con activación {activacion_inicial:.3f}")
            # Propagar desde este contexto
            contextos_alcanzados = propagador.propagar_desde_nodo(
                contexto_inicial, activacion_inicial, max_pasos
            )
            print(f"📡 ALCANZADOS {len(contextos_alcanzados)} nodos desde {contexto_inicial[:8]}")
            
            # Acumular resultados (tomar máxima activación)
            for nodo_id, activacion in contextos_alcanzados.items():
                if nodo_id in todos_contextos_propagados:
                    if activacion > todos_contextos_propagados[nodo_id]['activacion']:
                        todos_contextos_propagados[nodo_id] = {
                            'activacion': activacion,
                            'fuente_principal': contexto_inicial
                        }
                else:
                    todos_contextos_propagados[nodo_id] = {
                        'activacion': activacion,
                        'fuente_principal': contexto_inicial
                    }
        
        # Nodos encontrados solo por propagación
        contextos_directos_set = set(contextos_directos)
        contextos_indirectos_set = set(todos_contextos_propagados.keys())
        solo_por_propagacion = contextos_indirectos_set - contextos_directos_set
        
        # Combinar todos los contextos (directos + propagados)
        todos_contextos = list(contextos_directos_set | contextos_indirectos_set)
        
        # Construir árbol enriquecido con información de propagación
        if todos_contextos:
            referencia_temporal = analisis_basico['analisis_intencion'].get('timestamp_referencia')
            factor_refuerzo = factor_refuerzo_temporal_custom
            
            # Pasar intención temporal a construir_arbol_consulta
            intencion_detectada = analisis_basico['analisis_intencion'].get('intencion_temporal', 'ESTRUCTURAL')
            construir_arbol_consulta._intencion_actual = intencion_detectada
            print(f"* Construyendo árbol con propagación - intención: {intencion_detectada}")
            
            arbol_enriquecido = construir_arbol_consulta(
                pregunta, todos_contextos, referencia_temporal, factor_refuerzo, momento_consulta
            )
            
            # Marcar nodos por origen en el árbol
            for nodo in arbol_enriquecido['nodes']:
                if nodo['id'] in solo_por_propagacion:
                    nodo['encontrado_por'] = 'propagacion'
                    nodo['activacion'] = todos_contextos_propagados[nodo['id']]['activacion']
                    nodo['fuente_propagacion'] = todos_contextos_propagados[nodo['id']]['fuente_principal']
                    # Marcar visualmente con un ícono diferente
                    if nodo.get('label'):
                        nodo['label'] = f"🔄 {nodo['label']}"
                elif nodo['id'] in contextos_directos_set:
                    nodo['encontrado_por'] = 'busqueda_directa'
        else:
            arbol_enriquecido = analisis_basico['arbol_consulta']
        
        # Información detallada de propagación
        info_propagacion = {
            'contextos_directos': list(contextos_directos_set),
            'contextos_indirectos': list(contextos_indirectos_set),
            'solo_por_propagacion': list(solo_por_propagacion),
            'total_nodos_alcanzados': len(todos_contextos_propagados),
            'pasos_propagacion': max_pasos,
            'activaciones': {nodo: info['activacion'] for nodo, info in todos_contextos_propagados.items()},
            'fuentes_propagacion': {nodo: info['fuente_principal'] for nodo, info in todos_contextos_propagados.items()}
        }
        
        # Respuesta enriquecida
        analisis_enriquecido = analisis_basico.copy()
        analisis_enriquecido.update({
            'contextos_recuperados': todos_contextos,
            'arbol_consulta': arbol_enriquecido,
            'propagacion': info_propagacion,
            'estrategia_aplicada': {
                **analisis_basico.get('estrategia_aplicada', {}),
                'propagacion_activada': True,
                'nodos_adicionales_propagacion': len(solo_por_propagacion),
                'contextos_semilla': len(contextos_directos),
                'propagacion_exitosa': len(solo_por_propagacion) > 0
            }
        })
        
        return analisis_enriquecido
        
    except Exception as e:
        print(f"Error en propagación dinámica: {e}")
        # Fallback al análisis básico
        analisis_basico['propagacion'] = {'error': str(e)}
        return analisis_basico