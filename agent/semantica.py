# agent/semantica.py 
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import List, Dict
import traceback

# Cliente y colección únicos
client = chromadb.PersistentClient(path="./chroma_db")

#  CREAR MODELO EXPLÍCITO (generar embeddings manualmente)
from sentence_transformers import SentenceTransformer
modelo_embeddings = SentenceTransformer('all-MiniLM-L6-v2')

# CREAR COLECCIÓN CON CONFIGURACIÓN HNSW OPTIMIZADA
coleccion = client.get_or_create_collection(
    name="contextos",
    metadata={
        "hnsw:space": "cosine",           # Métrica de distancia
        "hnsw:construction_ef": 200,      # Mayor precisión en construcción
        "hnsw:search_ef": 200,            # Mayor precisión en búsqueda
        "hnsw:M": 16                      # Más conexiones por nodo
    }
)

# CACHÉ PARA EVITAR RECÁLCULOS
_embedding_cache = {}

def indexar_documento(id: str, texto: str):
    """Indexa un documento para búsqueda semántica."""
    try:
        # Generar embedding explícitamente
        embedding = modelo_embeddings.encode([texto])[0]
        
        # Verificar si el documento ya existe
        existing = coleccion.get(ids=[id])
        if existing['ids']:
            # Si existe, actualizar
            coleccion.update(
                documents=[texto], 
                ids=[id],
                embeddings=[embedding.tolist()]  # PASAR EMBEDDING
            )
        else:
            # Si no existe, agregar
            coleccion.add(
                documents=[texto], 
                ids=[id],
                embeddings=[embedding.tolist()]  # PASAR EMBEDDING
            )
        
        # Guardar en caché
        _embedding_cache[id] = texto
        
    except Exception as e:
        print(f"Error indexando documento {id}: {e}")

# INDEXADO POR LOTES
def indexar_documentos_batch(ids: List[str], textos: List[str], metadatas: List[Dict] = None):
    """
    Indexa múltiples documentos en un solo batch.
    MUCHO más eficiente que indexar uno por uno.
    """
    if not ids or not textos or len(ids) != len(textos):
        print(" Error: IDs y textos deben tener la misma longitud")
        return
    
    # Si no se proporcionan metadatos, crear lista vacía
    if metadatas is None:
        metadatas = [{}] * len(ids)
    
    try:
        # Verificar cuáles ya existen
        try:
            existing = coleccion.get(ids=ids)
            existing_ids = set(existing['ids']) if existing and existing['ids'] else set()
        except Exception as e:
            print(f" Error al verificar existentes: {e}")
            existing_ids = set()
        
        # Separar en nuevos y existentes
        ids_nuevos = []
        textos_nuevos = []
        metadatas_nuevos = []
        ids_actualizar = []
        textos_actualizar = []
        metadatas_actualizar = []
        
        for id, texto, metadata in zip(ids, textos, metadatas):
            if id in existing_ids:
                ids_actualizar.append(id)
                textos_actualizar.append(texto)
                metadatas_actualizar.append(metadata)
            else:
                ids_nuevos.append(id)
                textos_nuevos.append(texto)
                metadatas_nuevos.append(metadata)
        
        # Generar embeddings explícitamente para documentos nuevos
        if ids_nuevos:
            print(f"🔄 Generando embeddings para {len(ids_nuevos)} documentos nuevos...")
            embeddings_nuevos = modelo_embeddings.encode(textos_nuevos, show_progress_bar=False)
            
            coleccion.add(
                documents=textos_nuevos, 
                ids=ids_nuevos,
                embeddings=embeddings_nuevos.tolist(),
                metadatas=metadatas_nuevos  # PASAR METADATOS
            )
            print(f" Indexados {len(ids_nuevos)} documentos nuevos en batch")
        
        # Generar embeddings para actualizaciones
        if ids_actualizar:
            print(f" Generando embeddings para {len(ids_actualizar)} documentos a actualizar...")
            embeddings_actualizar = modelo_embeddings.encode(textos_actualizar, show_progress_bar=False)
            
            coleccion.update(
                documents=textos_actualizar, 
                ids=ids_actualizar,
                embeddings=embeddings_actualizar.tolist(),
                metadatas=metadatas_actualizar  # ✅ PASAR METADATOS
            )
            print(f" Actualizados {len(ids_actualizar)} documentos en batch")
        
        #  Asegurar que ChromaDB persista los cambios
        try:
            coleccion.peek(limit=1)
        except:
            pass
        
        # Actualizar caché
        for id, texto in zip(ids, textos):
            _embedding_cache[id] = texto
            
        print(f" Total indexado correctamente: {len(ids)} documentos")
            
    except Exception as e:
        print(f" Error en indexado batch: {e}")
        traceback.print_exc()
        
        # FALLBACK: Si el batch falla, intentar uno por uno
        print(" Intentando indexado individual como fallback...")
        for id, texto in zip(ids, textos):
            try:
                indexar_documento(id, texto)
            except Exception as e2:
                print(f" Error indexando {id}: {e2}")

def buscar_similares(texto_consulta: str, k: int = 3):
    """Busca documentos semánticamente similares CON embedding explícito."""
    try:
        # GENERAR EMBEDDING EXACTAMENTE COMO RAG
        print(f" Buscando similares para: '{texto_consulta[:50]}...'")
        embedding_consulta = modelo_embeddings.encode(texto_consulta)  # SIN LISTA, SIN [0]
        print(f" Embedding generado: shape={embedding_consulta.shape}")
        
        # BUSCAR usando embedding explícito
        resultado = coleccion.query(
            query_embeddings=[embedding_consulta.tolist()],  #  USAR EMBEDDING
            n_results=k,
            include=['documents', 'distances']  #  Incluir info para debugging
        )
        
        if resultado and resultado.get('ids') and resultado['ids'][0]:
            print(f" Encontrados {len(resultado['ids'][0])} resultados similares")
            # Mostrar los primeros 3 resultados para debugging
            for i, (id, dist) in enumerate(zip(resultado['ids'][0][:3], resultado['distances'][0][:3])):
                doc_preview = resultado['documents'][0][i][:50] if resultado.get('documents') else 'N/A'
                print(f"   {i+1}. {id[:8]}... (dist={dist:.3f}): {doc_preview}...")
            return resultado["ids"][0]
        else:
            print(" No se encontraron resultados")
            return []
            
    except Exception as e:
        print(f" Error en búsqueda semántica: {e}")
        import traceback
        traceback.print_exc()
        return []

# SIMILITUD BATCH
def calcular_similitudes_batch(texto_nuevo: str, nodos_existentes: List[str]) -> Dict[str, float]:
    """
    Calcula similitud de un texto nuevo contra múltiples nodos existentes.
    Retorna un diccionario {nodo_id: similitud}
    """
    if not nodos_existentes:
        return {}
    
    if not texto_nuevo or not texto_nuevo.strip():
        print("Texto nuevo vacío en calcular_similitudes_batch")
        return {}
    
    try:
        # Verificar que la colección tiene datos
        count = coleccion.count()
        if count == 0:
            print("⚠️ La colección de embeddings está vacía")
            return {}
        
        # Buscar los k vecinos más cercanos
        k = min(len(nodos_existentes), 100)
        
        #  GENERAR EMBEDDING EXPLÍCITAMENTE
        embedding_consulta = modelo_embeddings.encode(texto_nuevo)  #  SIN LISTA, SIN [0]

        resultado = coleccion.query(
            query_embeddings=[embedding_consulta.tolist()],  #  USAR EMBEDDING
            n_results=k,
            include=['distances']
        )
        
        if not resultado or not resultado.get('ids') or not resultado['ids'][0]:
            print(" No se obtuvieron resultados de la búsqueda")
            return {}
        
        # Convertir distancias a similitudes
        similitudes = {}
        nodos_set = set(nodos_existentes)
        
        for nodo_id, distance in zip(resultado['ids'][0], resultado['distances'][0]):
            if nodo_id in nodos_set:
                # Convertir distancia a similitud (0=idéntico, 2=muy diferente)
                similitud = max(0.0, 1.0 - distance / 2.0)
                similitudes[nodo_id] = similitud
        
        print(f" Calculadas {len(similitudes)} similitudes de {len(nodos_existentes)} nodos")
        return similitudes
        
    except Exception as e:
        print(f" Error en similitud batch: {e}")
        traceback.print_exc()
        
        # FALLBACK: Retornar similitudes vacías (se usará solo Jaccard)
        print("⚠️ Usando solo similitud Jaccard como fallback")
        return {}

#FUNCIÓN PARA LIMPIAR CACHÉ
def limpiar_cache():
    """Limpia el caché de embeddings (útil después de procesar muchos datos)"""
    global _embedding_cache
    _embedding_cache = {}
    print(" Caché de embeddings limpiado")

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
        print(f" Error verificando colección: {e}")
        return 0
    
def reiniciar_coleccion():
    """
    Reinicia completamente la colección de ChromaDB.
    PRECAUCIÓN: Esto elimina TODOS los embeddings indexados.
    Usar solo cuando se necesita recargar el dataset desde cero.
    """
    global coleccion, _embedding_cache
    
    try:
        # Eliminar colección existente
        client.delete_collection(name="contextos")
        print("  Colección 'contextos' eliminada")
        
        # Recrear colección vacía
        coleccion = client.get_or_create_collection(
            name="contextos",
            metadata={"hnsw:space": "cosine"}  # ✅ SIN embedding_function
        )
        print(" Colección 'contextos' recreada (vacía)")
        
        # Limpiar caché
        _embedding_cache = {}
        print(" Caché de embeddings limpiado")
        
        # Verificar estado
        count = coleccion.count()
        print(f"📊 Estado final: {count} documentos en colección")
        
        return {
            "status": "success",
            "mensaje": "Colección reiniciada correctamente",
            "documentos_actuales": count
        }
        
    except Exception as e:
        print(f" Error al reiniciar colección: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": "error",
            "mensaje": str(e)
        }
    
def verificar_y_reparar_indice():
    """
    Fuerza a ChromaDB a reconstruir el índice HNSW.
    Usar después de cargar datasets grandes.
    """
    try:
        count = coleccion.count()
        print(f"📊 Verificando índice ChromaDB: {count} documentos")
        
        if count == 0:
            print("⚠️ Colección vacía - no hay nada que reparar")
            return
        
        # Forzar reconstrucción del índice haciendo una consulta dummy
        dummy_embedding = modelo_embeddings.encode("verificación de índice")
        resultado = coleccion.query(
            query_embeddings=[dummy_embedding.tolist()],
            n_results=min(10, count)
        )
        
        print(f" Índice verificado - {len(resultado['ids'][0])} resultados en consulta de prueba")
        
        # Verificar que los embeddings están presentes
        sample = coleccion.get(limit=3, include=['embeddings'])
        
        if sample and sample.get('embeddings'):
            print(f" Embeddings presentes en {len(sample['embeddings'])} documentos de muestra")
        else:
            print(f" ERROR: Los embeddings NO están presentes en la base de datos")
            return False
        
        return True
        
    except Exception as e:
        print(f" Error verificando índice: {e}")
        import traceback
        traceback.print_exc()
        return False
    
def diagnosticar_chromadb_detallado():
    """
    Diagnóstico exhaustivo de ChromaDB para detectar problemas de indexación.
    """
    print("\n" + "="*70)
    print("DIAGNÓSTICO DETALLADO DE CHROMADB")
    print("="*70)
    
    try:
        # 1. Información básica
        count = coleccion.count()
        print(f"\n1 ESTADÍSTICAS BÁSICAS:")
        print(f"   Total documentos: {count}")
        
        if count == 0:
            print("    Colección vacía")
            return
        
        # 2. Verificar que los embeddings están presentes
        print(f"\n2 VERIFICAR EMBEDDINGS:")
        sample = coleccion.get(limit=5, include=['embeddings', 'documents'])
        
        if sample and sample.get('embeddings') is not None and len(sample.get('embeddings', [])) > 0:
            print(f"    Embeddings presentes en muestra")
            for i, emb in enumerate(sample['embeddings'][:3]):
                if emb:
                    print(f"   - Doc {i+1}: embedding dimension = {len(emb)}")
                else:
                    print(f"   - Doc {i+1}:  SIN embedding")
        else:
            print(f"    NO se encontraron embeddings")
            return
        
        # 3. Buscar documentos con "amparo" y obtener sus embeddings
        print(f"\n3 ANÁLISIS DE DOCUMENTOS CON 'AMPARO':")
        
        todos_docs = coleccion.get(include=['documents', 'embeddings'])
        docs_con_amparo = []
        
        for i, doc in enumerate(todos_docs['documents']):
            if doc and 'amparo' in doc.lower():
                docs_con_amparo.append({
                    'id': todos_docs['ids'][i],
                    'texto': doc[:100],
                    'embedding': todos_docs['embeddings'][i] if todos_docs.get('embeddings') else None
                })
        
        print(f"   Encontrados {len(docs_con_amparo)} documentos con 'amparo'")
        
        if not docs_con_amparo:
            print("    No se encontraron documentos con 'amparo'")
            return
        
        # 4. Probar búsqueda semántica con el PRIMER documento de amparo
        print(f"\n4 PRUEBA DE BÚSQUEDA SEMÁNTICA:")
        
        doc_amparo = docs_con_amparo[0]
        print(f"   Usando como consulta: {doc_amparo['texto'][:80]}...")
        
        # Generar embedding para la consulta
        embedding_consulta = modelo_embeddings.encode(doc_amparo['texto'][:100])
        
        # Buscar
        resultado = coleccion.query(
            query_embeddings=[embedding_consulta.tolist()],
            n_results=10,
            include=['documents', 'distances']
        )
        
        print(f"\n   📊 Top 10 resultados:")
        for i, (id_res, dist, doc_res) in enumerate(zip(
            resultado['ids'][0], 
            resultado['distances'][0], 
            resultado['documents'][0]
        ), 1):
            tiene_amparo = '✅' if 'amparo' in doc_res.lower() else '❌'
            print(f"   {i}. {tiene_amparo} Distancia: {dist:.4f}")
            print(f"      {doc_res[:80]}...")
            
            # Verificar si el documento original está en los resultados
            if id_res == doc_amparo['id']:
                print(f"      🎯 ESTE ES EL DOCUMENTO ORIGINAL (debería estar en pos 1)")
        
        # 5. Calcular similitud directa entre embeddings
        print(f"\n5️⃣ VERIFICACIÓN DE EMBEDDINGS:")
        
        if doc_amparo['embedding']:
            import numpy as np
            from numpy.linalg import norm
            
            emb_original = np.array(doc_amparo['embedding'])
            emb_consulta = np.array(embedding_consulta)
            
            # Similitud coseno manual
            similitud = np.dot(emb_original, emb_consulta) / (norm(emb_original) * norm(emb_consulta))
            distancia = 1 - similitud
            
            print(f"   Similitud coseno (manual): {similitud:.4f}")
            print(f"   Distancia coseno (manual): {distancia:.4f}")
            print(f"   Esta distancia debería ser ~0.0 (documento idéntico)")
            
            if distancia > 0.1:
                print(f"   ADVERTENCIA: Distancia muy alta para documento idéntico")
                print(f"   Esto indica que ChromaDB NO está usando los embeddings correctos")
        
        print("\n" + "="*70)
        print("FIN DEL DIAGNÓSTICO")
        print("="*70)
        
    except Exception as e:
        print(f"\n Error en diagnóstico: {e}")
        import traceback
        traceback.print_exc()