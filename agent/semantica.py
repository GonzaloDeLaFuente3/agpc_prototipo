import chromadb #Base de datos vectorial especializada en búsquedas semánticas
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
#Es el motor de búsqueda semántica inteligente que encuentra documentos relacionados por significado, no solo por palabras exactas.

# Cliente persistente nuevo
client = chromadb.PersistentClient(path="./chroma_db") # Base de datos persistente en disco, para no recalcular todo cada vez

# Función de embeddings
embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2") #Modelo de IA que convierte texto en "vectores" (números que representan el significado)

# Crear colección
coleccion = client.get_or_create_collection(name="contextos", embedding_function=embedding_function)

def indexar_documento(id, texto):
    # Toma el texto → lo convierte en vector numérico → lo guarda
    # El vector "captura" el significado del texto
    try:
        coleccion.add(documents=[texto], ids=[id])
    except chromadb.errors.IDAlreadyExistsError:
        pass  # Ya está indexado, manejo de duplicados

def buscar_similares(texto_consulta, k=3):
    # Convierte tu pregunta en vector
    # Encuentra los 3 documentos con vectores más "similares"
    # Similitud = proximidad en el espacio vectorial
    resultado = coleccion.query(query_texts=[texto_consulta], n_results=k)
    ids = resultado["ids"][0]
    return ids
