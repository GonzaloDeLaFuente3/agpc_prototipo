# agent/semantica.py - OPTIMIZADO CON BATCHES
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import List, Dict
import traceback

# Cliente y colección únicos
client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
coleccion = client.get_or_create_collection(name="contextos", embedding_function=embedding_function)

# CACHÉ PARA EVITAR RECÁLCULOS
_embedding_cache = {}

def indexar_documento(id: str, texto: str):
    """Indexa un documento para búsqueda semántica."""
    try:
        # Verificar si el documento ya existe
        existing = coleccion.get(ids=[id])
        if existing['ids']:
            # Si existe, actualizar
            coleccion.update(documents=[texto], ids=[id])
        else:
            # Si no existe, agregar
            coleccion.add(documents=[texto], ids=[id])
        
        # Guardar en caché
        _embedding_cache[id] = texto
        
    except Exception as e:
        print(f"Error indexando documento {id}: {e}")

# NUEVA FUNCIÓN: INDEXADO POR LOTES
def indexar_documentos_batch(ids: List[str], textos: List[str]):
    """
    Indexa múltiples documentos en un solo batch.
    MUCHO más eficiente que indexar uno por uno.
    """
    if not ids or not textos or len(ids) != len(textos):
        print("⚠️ Error: IDs y textos deben tener la misma longitud")
        return
    
    try:
        # Verificar cuáles ya existen
        try:
            existing = coleccion.get(ids=ids)
            existing_ids = set(existing['ids']) if existing and existing['ids'] else set()
        except Exception as e:
            print(f"⚠️ Error al verificar existentes: {e}")
            existing_ids = set()
        
        # Separar en nuevos y existentes
        ids_nuevos = []
        textos_nuevos = []
        ids_actualizar = []
        textos_actualizar = []
        
        for id, texto in zip(ids, textos):
            if id in existing_ids:
                ids_actualizar.append(id)
                textos_actualizar.append(texto)
            else:
                ids_nuevos.append(id)
                textos_nuevos.append(texto)
        
        # Agregar nuevos en batch
        if ids_nuevos:
            coleccion.add(documents=textos_nuevos, ids=ids_nuevos)
            print(f"✅ Indexados {len(ids_nuevos)} documentos nuevos en batch")
        
        # Actualizar existentes en batch
        if ids_actualizar:
            coleccion.update(documents=textos_actualizar, ids=ids_actualizar)
            print(f"✅ Actualizados {len(ids_actualizar)} documentos en batch")
        
        # Importante: Asegurar que ChromaDB persista los cambios
        try:
            # Forzar un peek para asegurar que se guardaron
            coleccion.peek(limit=1)
        except:
            pass
        
        # Actualizar caché
        for id, texto in zip(ids, textos):
            _embedding_cache[id] = texto
            
        print(f"✅ Total indexado correctamente: {len(ids)} documentos")
            
    except Exception as e:
        print(f"❌ Error en indexado batch: {e}")
        traceback.print_exc()
        
        # FALLBACK: Si el batch falla, intentar uno por uno
        print("⚠️ Intentando indexado individual como fallback...")
        for id, texto in zip(ids, textos):
            try:
                indexar_documento(id, texto)
            except Exception as e2:
                print(f"❌ Error indexando {id}: {e2}")

def buscar_similares(texto_consulta: str, k: int = 3):
    """Busca documentos semánticamente similares."""
    try:
        resultado = coleccion.query(query_texts=[texto_consulta], n_results=k)
        return resultado["ids"][0]
    except Exception as e:
        print(f"Error en búsqueda semántica: {e}")
        return []

# NUEVA FUNCIÓN: SIMILITUD BATCH
def calcular_similitudes_batch(texto_nuevo: str, nodos_existentes: List[str]) -> Dict[str, float]:
    """
    Calcula similitud de un texto nuevo contra múltiples nodos existentes.
    Retorna un diccionario {nodo_id: similitud}
    """
    if not nodos_existentes:
        return {}
    
    if not texto_nuevo or not texto_nuevo.strip():
        print("⚠️ Texto nuevo vacío en calcular_similitudes_batch")
        return {}
    
    try:
        # Verificar que la colección tiene datos
        count = coleccion.count()
        if count == 0:
            print("⚠️ La colección de embeddings está vacía")
            return {}
        
        # Buscar los k vecinos más cercanos
        k = min(len(nodos_existentes), 100)
        
        resultado = coleccion.query(
            query_texts=[texto_nuevo],
            n_results=k,
            include=['distances']
        )
        
        if not resultado or not resultado.get('ids') or not resultado['ids'][0]:
            print("⚠️ No se obtuvieron resultados de la búsqueda")
            return {}
        
        # Convertir distancias a similitudes
        similitudes = {}
        nodos_set = set(nodos_existentes)
        
        for nodo_id, distance in zip(resultado['ids'][0], resultado['distances'][0]):
            if nodo_id in nodos_set:
                # Convertir distancia a similitud (0=idéntico, 2=muy diferente)
                similitud = max(0.0, 1.0 - distance / 2.0)
                similitudes[nodo_id] = similitud
        
        print(f"✅ Calculadas {len(similitudes)} similitudes de {len(nodos_existentes)} nodos")
        return similitudes
        
    except Exception as e:
        print(f"❌ Error en similitud batch: {e}")
        traceback.print_exc()
        
        # FALLBACK: Retornar similitudes vacías (se usará solo Jaccard)
        print("⚠️ Usando solo similitud Jaccard como fallback")
        return {}

#FUNCIÓN PARA LIMPIAR CACHÉ
def limpiar_cache():
    """Limpia el caché de embeddings (útil después de procesar muchos datos)"""
    global _embedding_cache
    _embedding_cache = {}
    print("🧹 Caché de embeddings limpiado")

def verificar_estado_coleccion():
    """Función de diagnóstico para verificar el estado de ChromaDB"""
    try:
        count = coleccion.count()
        print(f"📊 Estado de ChromaDB:")
        print(f"   - Total documentos: {count}")
        
        if count > 0:
            peek = coleccion.peek(limit=3)
            print(f"   - Primeros IDs: {peek['ids'][:3]}")
        
        return count
    except Exception as e:
        print(f"❌ Error verificando colección: {e}")
        return 0