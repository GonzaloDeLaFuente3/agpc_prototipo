import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ✅ Cliente persistente nuevo
client = chromadb.PersistentClient(path="./chroma_db")

# ✅ Función de embeddings
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

# ✅ Crear colección
coleccion = client.get_or_create_collection(name="contextos", embedding_function=embedding_function)

def indexar_documento(id, texto):
    try:
        coleccion.add(documents=[texto], ids=[id])
    except chromadb.errors.IDAlreadyExistsError:
        pass  # Ya está indexado

def buscar_similares(texto_consulta, k=3):
    resultado = coleccion.query(query_texts=[texto_consulta], n_results=k)
    ids = resultado["ids"][0]
    return ids
