# agent/semantica.py - Optimizado y actualizado
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
    """Busca documentos semánticamente similares."""
    try:
        resultado = coleccion.query(query_texts=[texto_consulta], n_results=k)
        return resultado["ids"][0]
    except Exception as e:
        print(f"Error en búsqueda semántica: {e}")
        return []