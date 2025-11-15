#!/usr/bin/env python3
"""
Inspecciona qué texto se indexó REALMENTE en ChromaDB para casos de amparo.
"""

import sys
sys.path.append('.')

from agent.semantica import coleccion, modelo_embeddings
import json
import os

print("="*80)
print("INSPECCIÓN DE INDEXACIÓN - CASOS DE AMPARO")
print("="*80)

# Variables globales
conversaciones_amparo = []
fragmentos_amparo = []

# 1. Buscar el dataset en varias ubicaciones posibles
print("\n1️⃣ BUSCANDO DATASET...")
posibles_rutas = [
    'legal_dataset_200.json',
    'data/legal_dataset_200.json',
    'datasets/legal_dataset_200.json',
    '../legal_dataset_200.json'
]

dataset_path = None
for ruta in posibles_rutas:
    if os.path.exists(ruta):
        dataset_path = ruta
        break

if dataset_path:
    print(f"✅ Dataset encontrado en: {dataset_path}")
    try:
        with open(dataset_path, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        conversaciones = dataset.get('conversaciones', [])
        print(f"✅ Dataset cargado: {len(conversaciones)} conversaciones")
        
        # Buscar conversaciones con "amparo por mora"
        for i, conv in enumerate(conversaciones):
            contenido = conv.get('contenido', '')
            if 'amparo por mora' in contenido.lower():
                conversaciones_amparo.append({
                    'index': i,
                    'titulo': conv.get('titulo', 'Sin título'),
                    'contenido': contenido,
                    'contenido_completo': contenido
                })
        
        print(f"✅ Encontradas {len(conversaciones_amparo)} conversaciones con 'amparo por mora'")
        
        if conversaciones_amparo:
            print(f"\n📋 Primera conversación de amparo (ORIGINAL):")
            print(f"   Título: {conversaciones_amparo[0]['titulo']}")
            print(f"   Contenido completo ({len(conversaciones_amparo[0]['contenido'])} caracteres):")
            print(f"   {conversaciones_amparo[0]['contenido'][:500]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error cargando dataset: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"⚠️ Dataset no encontrado en ubicaciones conocidas")
    print(f"   Rutas buscadas:")
    for ruta in posibles_rutas:
        print(f"   - {ruta}")
    print(f"\n   Continuando con análisis de ChromaDB...")

# 2. Buscar en ChromaDB los fragmentos indexados con "amparo"
print("\n2️⃣ INSPECCIONANDO FRAGMENTOS INDEXADOS EN CHROMADB...")
try:
    all_docs = coleccion.get(include=['documents', 'metadatas'])
    
    for i, (id, doc, meta) in enumerate(zip(
        all_docs['ids'], 
        all_docs['documents'],
        all_docs.get('metadatas', [{}] * len(all_docs['ids']))
    )):
        if 'amparo' in doc.lower():
            fragmentos_amparo.append({
                'id': id,
                'texto': doc,
                'longitud': len(doc),
                'metadata': meta
            })
    
    print(f"✅ Encontrados {len(fragmentos_amparo)} fragmentos con 'amparo' en ChromaDB")
    
    if fragmentos_amparo:
        print(f"\n📋 Primeros 5 fragmentos indexados:")
        for i, frag in enumerate(fragmentos_amparo[:5], 1):
            print(f"\n   {i}. ID: {frag['id'][:40]}")
            print(f"      Longitud: {frag['longitud']} caracteres")
            print(f"      Metadata: {frag['metadata']}")
            print(f"      Texto completo:")
            print(f"      '{frag['texto']}'")
            print()
            
            # ANÁLISIS DEL FRAGMENTO
            if frag['longitud'] < 100:
                print(f"      ⚠️ FRAGMENTO MUY CORTO (<100 chars)")
            
            if 'amparo por mora' in frag['texto'].lower():
                print(f"      ✅ Contiene 'amparo por mora' completo")
            else:
                print(f"      ⚠️ NO contiene 'amparo por mora' completo")
    else:
        print(f"❌ NO se encontraron fragmentos con 'amparo'")
        print(f"   Esto indica que el dataset NO se cargó o se limpió ChromaDB")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

# 3. Análisis de longitud de fragmentos
print("\n3️⃣ ANÁLISIS DE LONGITUD DE FRAGMENTOS")
print("-"*80)

if fragmentos_amparo:
    longitudes = [f['longitud'] for f in fragmentos_amparo]
    print(f"Estadísticas de longitud:")
    print(f"  Mínimo: {min(longitudes)} caracteres")
    print(f"  Máximo: {max(longitudes)} caracteres")
    print(f"  Promedio: {sum(longitudes)/len(longitudes):.0f} caracteres")
    
    # Contar fragmentos cortos
    muy_cortos = sum(1 for l in longitudes if l < 100)
    cortos = sum(1 for l in longitudes if 100 <= l < 200)
    normales = sum(1 for l in longitudes if l >= 200)
    
    print(f"\nDistribución:")
    print(f"  Muy cortos (<100 chars): {muy_cortos} ({muy_cortos/len(longitudes)*100:.1f}%)")
    print(f"  Cortos (100-200 chars): {cortos} ({cortos/len(longitudes)*100:.1f}%)")
    print(f"  Normales (>200 chars): {normales} ({normales/len(longitudes)*100:.1f}%)")
    
    if muy_cortos > len(longitudes) * 0.5:
        print(f"\n⚠️ PROBLEMA CRÍTICO: >50% de fragmentos son muy cortos")
        print(f"   → Los embeddings tendrán baja calidad")
        print(f"   → Necesitas revisar la fragmentación en agent/fragmentador.py")

# 4. Probar búsqueda con diferentes queries
print("\n4️⃣ PRUEBA DE BÚSQUEDAS CON DIFERENTES QUERIES")
print("-"*80)

queries = [
    "Amparo por mora administrativa",
    "amparo por mora",
    "amparo",
    "mora administrativa",
    "presentar amparo"
]

for query in queries:
    try:
        print(f"\n📍 Query: '{query}'")
        emb = modelo_embeddings.encode(query)
        resultado = coleccion.query(
            query_embeddings=[emb.tolist()],
            n_results=5,
            include=['documents', 'distances']
        )
        
        print("   Top 5 resultados:")
        for i, (doc, dist) in enumerate(zip(
            resultado['documents'][0],
            resultado['distances'][0]
        ), 1):
            tiene_amparo = '✅' if 'amparo' in doc.lower() else '❌'
            print(f"   {i}. {tiene_amparo} Dist: {dist:.4f}")
            print(f"      {doc[:100]}...")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")

# 5. Comparar con dataset original si está disponible
if conversaciones_amparo and fragmentos_amparo:
    print("\n5️⃣ COMPARACIÓN: ORIGINAL vs INDEXADO")
    print("-"*80)
    
    print("\n📄 CONVERSACIÓN ORIGINAL:")
    print(f"  Longitud: {len(conversaciones_amparo[0]['contenido_completo'])} caracteres")
    print(f"  Texto completo:")
    print(f"  {conversaciones_amparo[0]['contenido_completo'][:400]}...")
    
    print("\n📦 FRAGMENTOS INDEXADOS DE ESTA CONVERSACIÓN:")
    # Buscar fragmentos que puedan corresponder a esta conversación
    fragmentos_relacionados = [f for f in fragmentos_amparo 
                               if 'test_' not in f['id']]  # Excluir casos de test
    
    if fragmentos_relacionados:
        print(f"  Encontrados {len(fragmentos_relacionados)} fragmentos (excluyendo tests)")
        for i, frag in enumerate(fragmentos_relacionados[:3], 1):
            print(f"\n  Fragmento {i}:")
            print(f"    Longitud: {frag['longitud']} caracteres")
            print(f"    Texto: {frag['texto'][:200]}...")
    else:
        print(f"  ⚠️ No se encontraron fragmentos (solo hay casos de test)")

print("\n" + "="*80)
print("FIN DE LA INSPECCIÓN")
print("="*80)

# DIAGNÓSTICO FINAL
print("\n📊 DIAGNÓSTICO FINAL:")
print("-"*80)

if not fragmentos_amparo:
    print("❌ PROBLEMA CRÍTICO: No hay fragmentos de 'amparo' en ChromaDB")
    print("   SOLUCIÓN: Necesitas cargar el dataset con:")
    print("   python cargar_dataset_limpio.py")

elif all('test_' in f['id'] for f in fragmentos_amparo):
    print("⚠️ ADVERTENCIA: Solo hay casos de TEST en ChromaDB")
    print("   Los casos de test funcionan bien (como vimos antes)")
    print("   SOLUCIÓN: Necesitas cargar el dataset real con:")
    print("   python cargar_dataset_limpio.py")

elif fragmentos_amparo:
    muy_cortos = sum(1 for f in fragmentos_amparo if f['longitud'] < 100)
    if muy_cortos > len(fragmentos_amparo) * 0.5:
        print("❌ PROBLEMA: Fragmentos muy cortos")
        print("   Los fragmentos son demasiado cortos para buenos embeddings")
        print("   SOLUCIÓN: Modificar agent/fragmentador.py para fragmentos más largos")
    else:
        print("✅ Fragmentos tienen longitud aceptable")
        print("   SOLUCIÓN: El problema puede estar en el índice HNSW")
        print("   Prueba reindexar con: python cargar_dataset_limpio.py")

print("\n💡 RECOMENDACIÓN:")
print("   1. Borra ChromaDB y datos: rmdir /s /q chroma_db && rmdir /s /q data")
print("   2. Reinicia servidor: python main.py")  
print("   3. Carga dataset: python cargar_dataset_limpio.py")