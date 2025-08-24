# agent/semantica.py - Optimizado
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# Cliente y colección únicos
client = chromadb.PersistentClient(path="./chroma_db")
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
coleccion = client.get_or_create_collection(name="contextos", embedding_function=embedding_function)

def indexar_documento(id: str, texto: str):
    """Indexa un documento para búsqueda semántica."""
    try:
        coleccion.add(documents=[texto], ids=[id])
    except chromadb.errors.IDAlreadyExistsError:
        pass  # Ya indexado

def buscar_similares(texto_consulta: str, k: int = 3):
    """Busca documentos semánticamente similares."""
    resultado = coleccion.query(query_texts=[texto_consulta], n_results=k)
    return resultado["ids"][0]