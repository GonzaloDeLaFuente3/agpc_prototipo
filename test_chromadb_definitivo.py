# test_chromadb_definitivo.py
"""
Script para diagnosticar y resolver el problema de ChromaDB.
"""
import sys
import time

def test_completo():
    print("="*80)
    print("TEST DEFINITIVO DE CHROMADB")
    print("="*80)
    
    # Importar después de print para ver errores
    try:
        from agent.semantica import (
            coleccion, modelo_embeddings, 
            reiniciar_coleccion, indexar_documentos_batch,
            buscar_similares, diagnosticar_chromadb_detallado
        )
    except ImportError as e:
        print(f"❌ Error importando: {e}")
        return
    
    print("\n1️⃣ REINICIANDO COLECCIÓN CHROMADB...")
    resultado = reiniciar_coleccion()
    print(resultado)
    
    print("\n2️⃣ INDEXANDO CASOS DE PRUEBA...")
    
    # Casos de prueba muy específicos
    casos_test = [
        {
            'id': 'test_amparo_1',
            'texto': 'Abogado: Presentar amparo por mora administrativa. El juez ordena al organismo que resuelva en plazo perentorio.',
            'tipo': 'amparo'
        },
        {
            'id': 'test_amparo_2', 
            'texto': 'Ciudadano: Hace 18 meses pedí subsidio en ANSES y no me resuelven nada. Necesito presentar amparo por mora.',
            'tipo': 'amparo'
        },
        {
            'id': 'test_acoso_1',
            'texto': 'Trabajador: Mi supervisor me maltrata constantemente hace 6 meses. Me grita, me humilla delante de todos.',
            'tipo': 'acoso'
        },
        {
            'id': 'test_acoso_2',
            'texto': 'Empleado: Mi jefe me hostiga permanentemente. Hay testigos del maltrato laboral que sufro a diario.',
            'tipo': 'acoso'
        }
    ]
    
    ids = [c['id'] for c in casos_test]
    textos = [c['texto'] for c in casos_test]
    metadatas = [{'tipo': c['tipo']} for c in casos_test]
    
    indexar_documentos_batch(ids, textos, metadatas)
    
    print(f"✅ Indexados {len(casos_test)} casos de prueba")
    
    # Esperar a que ChromaDB procese
    time.sleep(2)
    
    print("\n3️⃣ PROBANDO BÚSQUEDAS...")
    
    # Prueba 1: Buscar "amparo"
    print("\n   A) Búsqueda: 'amparo por mora administrativa'")
    resultados = buscar_similares('amparo por mora administrativa', k=4)
    
    print(f"   Resultados (IDs): {resultados}")
    
    for id_res in resultados:
        caso = next((c for c in casos_test if c['id'] == id_res), None)
        if caso:
            tipo_correcto = '✅' if caso['tipo'] == 'amparo' else '❌'
            print(f"      {tipo_correcto} {id_res}: {caso['tipo']}")
    
    # Prueba 2: Buscar "acoso"
    print("\n   B) Búsqueda: 'maltrato laboral hostigamiento'")
    resultados = buscar_similares('maltrato laboral hostigamiento', k=4)
    
    print(f"   Resultados (IDs): {resultados}")
    
    for id_res in resultados:
        caso = next((c for c in casos_test if c['id'] == id_res), None)
        if caso:
            tipo_correcto = '✅' if caso['tipo'] == 'acoso' else '❌'
            print(f"      {tipo_correcto} {id_res}: {caso['tipo']}")
    
    print("\n4️⃣ DIAGNÓSTICO DETALLADO...")
    diagnosticar_chromadb_detallado()
    
    print("\n" + "="*80)
    print("EVALUACIÓN FINAL")
    print("="*80)
    
    print("""
    ✅ SI LAS BÚSQUEDAS DEVUELVEN LOS TIPOS CORRECTOS:
       → El problema está en el dataset legal_dataset_200.json o en cómo se indexa
       
    ❌ SI LAS BÚSQUEDAS SIGUEN DEVOLVIENDO TIPOS INCORRECTOS:
       → El problema es más profundo en ChromaDB o en el modelo de embeddings
    """)

if __name__ == "__main__":
    test_completo()