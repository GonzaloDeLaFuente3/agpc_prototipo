# agent/semantica.py
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Cliente y colección únicos
client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
coleccion = client.get_or_create_collection(name="contextos", embedding_function=embedding_function)

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
    except Exception as e:
        print(f"Error indexando documento {id}: {e}")

def buscar_similares(texto_consulta: str, k: int = 3):
    """Busca documentos semánticamente similares CON LOGGING DETALLADO."""
    try:
        # 🔍 LOGGING PRE-BÚSQUEDA
        print(f"\n🔎 BÚSQUEDA SEMÁNTICA INICIADA:")
        print(f"   ├─ Query: '{texto_consulta[:80]}{'...' if len(texto_consulta) > 80 else ''}'")
        print(f"   ├─ K solicitado: {k}")
        
        # Realizar búsqueda con distancias
        resultado = coleccion.query(
            query_texts=[texto_consulta], 
            n_results=k,
            include=['distances', 'documents']  # ✅ Incluir documentos para debugging
        )
        
        ids = resultado["ids"][0] if resultado["ids"] else []
        distances = resultado.get("distances", [[]])[0]
        documents = resultado.get("documents", [[]])[0]
        
        # 🔍 LOGGING POST-BÚSQUEDA
        print(f"   └─ Resultados encontrados: {len(ids)}")
        
        if ids and len(distances) > 0:
            print(f"\n   📊 TOP {min(10, len(ids))} RESULTADOS:")
            
            # Importar metadatos para mostrar títulos
            from agent.grafo import metadatos_contextos
            
            for i, (id_ctx, dist) in enumerate(zip(ids[:10], distances[:10])):
                similitud = max(0.0, 1.0 - (dist / 2.0))  # Convertir distancia a similitud
                
                # Obtener título del contexto
                meta = metadatos_contextos.get(id_ctx, {})
                titulo = meta.get('titulo', 'Sin título')[:50]
                
                # Mostrar fragmento del documento
                doc_preview = documents[i][:80] if i < len(documents) else "N/A"
                
                print(f"      {i+1}. [{similitud:.3f}] {titulo}")
                print(f"         ID: {id_ctx[:12]}... | Dist: {dist:.3f}")
                print(f"         Preview: \"{doc_preview}...\"")
        else:
            print(f"   ⚠️ NO SE ENCONTRARON RESULTADOS")
        
        return ids
        
    except Exception as e:
        print(f"❌ ERROR en búsqueda semántica: {e}")
        import traceback
        traceback.print_exc()
        return []