#!/usr/bin/env python3
"""
Comparación directa AGPC vs RAG - Búsqueda semántica
"""

import sys
sys.path.append('.')

from agent.semantica import coleccion as coleccion_agpc, modelo_embeddings as modelo_agpc

print("="*70)
print("COMPARACIÓN: AGPC vs RAG - Búsqueda Semántica")
print("="*70)

# Pregunta de prueba
pregunta = "Amparo por mora administrativa"
print(f"\n🔍 PREGUNTA: '{pregunta}'")
print("="*70)

# 1. AGPC - Búsqueda
print("\n1️⃣ BÚSQUEDA CON AGPC:")
print("-"*70)
try:
    # Generar embedding
    embedding_agpc = modelo_agpc.encode(pregunta)
    print(f"✅ Embedding generado")
    print(f"   Modelo: {modelo_agpc}")
    print(f"   Dimensión: {embedding_agpc.shape}")
    
    # Buscar
    resultados_agpc = coleccion_agpc.query(
        query_embeddings=[embedding_agpc.tolist()],
        n_results=10
    )
    
    print(f"\n📊 Top 10 resultados AGPC:")
    for i, (id, doc, dist) in enumerate(zip(
        resultados_agpc['ids'][0],
        resultados_agpc['documents'][0],
        resultados_agpc['distances'][0]
    )):
        tiene_amparo = '✅' if 'amparo' in doc.lower() else '❌'
        print(f"{i+1}. {tiene_amparo} Distancia: {dist:.4f}")
        print(f"   Texto: {doc[:80]}...")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 2. Verificar si los documentos con "amparo" existen
print("\n" + "="*70)
print("2️⃣ VERIFICACIÓN: ¿Existen documentos con 'amparo'?")
print("-"*70)
try:
    all_docs = coleccion_agpc.get()
    
    docs_amparo = []
    for id, doc in zip(all_docs['ids'], all_docs['documents']):
        if 'amparo por mora' in doc.lower():
            docs_amparo.append((id, doc))
    
    print(f"✅ Encontrados {len(docs_amparo)} documentos con 'amparo por mora'")
    
    if len(docs_amparo) > 0:
        print(f"\n📋 Primeros 3 documentos con 'amparo por mora':")
        for i, (id, doc) in enumerate(docs_amparo[:3]):
            print(f"{i+1}. ID: {id[:30]}...")
            print(f"   Texto: {doc[:150]}...")
            print()
        
        # Calcular distancia directa con el primero
        print("\n🔬 PRUEBA DE SIMILITUD DIRECTA:")
        print("-"*70)
        
        doc_test = docs_amparo[0][1]
        print(f"Documento de prueba: {doc_test[:100]}...")
        
        # Generar embeddings
        emb_pregunta = modelo_agpc.encode(pregunta)
        emb_documento = modelo_agpc.encode(doc_test)
        
        # Calcular distancia coseno manualmente
        from numpy import dot
        from numpy.linalg import norm
        
        cos_sim = dot(emb_pregunta, emb_documento)/(norm(emb_pregunta)*norm(emb_documento))
        cos_dist = 1 - cos_sim
        
        print(f"✅ Similitud coseno: {cos_sim:.4f}")
        print(f"✅ Distancia coseno: {cos_dist:.4f}")
        print()
        print("⚠️ Si esta distancia es BAJA (<0.5) pero ChromaDB no lo encuentra en top 10,")
        print("   entonces hay un problema con ChromaDB.")
        
    else:
        print("❌ NO se encontraron documentos con 'amparo por mora'")
        print("⚠️ Esto indica que el dataset NO se cargó correctamente.")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)
print("FIN DE LA COMPARACIÓN")
print("="*70)