#!/usr/bin/env python3
"""
Script de diagnóstico para verificar embeddings en ChromaDB
"""

import sys
sys.path.append('.')

from agent.semantica import coleccion, modelo_embeddings

print("="*60)
print("DIAGNÓSTICO DE CHROMADB")
print("="*60)

# 1. Verificar contenido de la colección
print("\n1️⃣ CONTENIDO DE CHROMADB:")
try:
    count = coleccion.count()
    print(f"   Total de documentos: {count}")
    
    # Obtener algunos documentos de ejemplo
    sample = coleccion.peek(limit=5)
    print(f"\n   📋 Primeros 5 documentos:")
    for i, (id, doc) in enumerate(zip(sample['ids'], sample['documents'])):
        print(f"   {i+1}. ID: {id[:30]}...")
        print(f"      Texto: {doc[:80]}...")
        print()
except Exception as e:
    print(f"   ❌ Error: {e}")

# 2. Buscar "Amparo" directamente en los documentos
print("\n2️⃣ BÚSQUEDA DIRECTA DE 'AMPARO' EN DOCUMENTOS:")
try:
    # Obtener TODOS los documentos
    all_docs = coleccion.get()
    
    amparo_docs = []
    for i, (id, doc) in enumerate(zip(all_docs['ids'], all_docs['documents'])):
        if 'amparo' in doc.lower():
            amparo_docs.append({
                'id': id,
                'texto': doc[:150]
            })
    
    print(f"   ✅ Encontrados {len(amparo_docs)} documentos con 'amparo'")
    for i, doc in enumerate(amparo_docs[:5]):
        print(f"   {i+1}. {doc['texto']}...")
        print()
    
except Exception as e:
    print(f"   ❌ Error: {e}")

# 3. Generar embedding de "Amparo por mora administrativa" y buscar
print("\n3️⃣ BÚSQUEDA SEMÁNTICA:")
try:
    pregunta = "Amparo por mora administrativa"
    print(f"   Pregunta: '{pregunta}'")
    
    # Generar embedding
    embedding_pregunta = modelo_embeddings.encode(pregunta)
    print(f"   ✅ Embedding generado (dimensión: {len(embedding_pregunta)})")
    
    # Buscar en ChromaDB
    resultados = coleccion.query(
        query_embeddings=[embedding_pregunta.tolist()],
        n_results=10
    )
    
    print(f"\n   📊 Top 10 resultados por similitud:")
    for i, (id, doc, dist) in enumerate(zip(
        resultados['ids'][0], 
        resultados['documents'][0], 
        resultados['distances'][0]
    )):
        # Resaltar si contiene "amparo"
        tiene_amparo = '✅' if 'amparo' in doc.lower() else '❌'
        
        print(f"   {i+1}. {tiene_amparo} Distancia: {dist:.4f}")
        print(f"      ID: {id[:30]}...")
        print(f"      Texto: {doc[:100]}...")
        print()
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 4. Verificar si los embeddings fueron generados correctamente
print("\n4️⃣ VERIFICAR EMBEDDINGS EN CHROMADB:")
try:
    # Obtener un documento con embeddings
    sample_with_embeddings = coleccion.get(
        ids=all_docs['ids'][:3],
        include=['documents', 'embeddings']
    )
    
    print(f"   📋 Verificando primeros 3 documentos:")
    for i, (id, doc, emb) in enumerate(zip(
        sample_with_embeddings['ids'],
        sample_with_embeddings['documents'],
        sample_with_embeddings['embeddings']
    )):
        print(f"   {i+1}. ID: {id[:30]}...")
        print(f"      Texto: {doc[:80]}...")
        print(f"      Embedding: {'✅ Existe' if emb and len(emb) > 0 else '❌ NO EXISTE'}")
        if emb:
            print(f"      Dimensión: {len(emb)}")
        print()
        
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*60)
print("FIN DEL DIAGNÓSTICO")
print("="*60)