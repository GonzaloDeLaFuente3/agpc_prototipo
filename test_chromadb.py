import chromadb
from sentence_transformers import SentenceTransformer

# Conectar a ChromaDB (igual que en agent/semantica.py)
client = chromadb.PersistentClient(path="./chroma_db")
modelo_embeddings = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

coleccion = client.get_or_create_collection(
    name="contextos",
    metadata={"hnsw:space": "cosine"}
)

print(f"📊 Total documentos en ChromaDB: {coleccion.count()}")

# Buscar casos de "Amparo"
print("\n🔍 Buscando: 'Amparo por mora administrativa'")
query_text = "Amparo por mora administrativa"
embedding_query = modelo_embeddings.encode([query_text])[0]

resultados = coleccion.query(
    query_embeddings=[embedding_query.tolist()],
    n_results=5,
    include=['documents', 'metadatas', 'distances']
)

print(f"\n📋 Top 5 resultados:")
for i in range(len(resultados['ids'][0])):
    doc_id = resultados['ids'][0][i]
    texto = resultados['documents'][0][i][:100] + "..."
    distancia = resultados['distances'][0][i]
    
    # Intentar obtener metadata si existe
    titulo = "Sin título"
    if resultados.get('metadatas') and resultados['metadatas'][0] and i < len(resultados['metadatas'][0]):
        meta = resultados['metadatas'][0][i]
        if meta:
            titulo = meta.get('titulo', 'Sin título')
    
    print(f"\n{i+1}. Distancia: {distancia:.4f}")
    print(f"   Título: {titulo}")
    print(f"   Texto: {texto}")

# Verificar si existen documentos con "Amparo" en el texto
print("\n\n🔍 Verificando si hay documentos con 'Amparo' indexados...")
all_docs = coleccion.get(limit=10000)

amparo_docs = []
for i, doc in enumerate(all_docs['documents']):
    if 'amparo' in doc.lower():
        amparo_docs.append({
            'id': all_docs['ids'][i],
            'texto': doc[:100]
        })

print(f"✅ Encontrados {len(amparo_docs)} documentos con 'amparo'")
if amparo_docs:
    print("\n📋 Primeros 5:")
    for doc in amparo_docs[:5]:
        print(f"   - {doc['texto']}...")