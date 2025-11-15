# cargar_dataset_limpio.py
import requests
import json
import time

def cargar_dataset_limpio():
    """Carga el dataset con verificación completa."""
    
    print("=" * 70)
    print("CARGA LIMPIA DE DATASET CON VERIFICACIÓN")
    print("=" * 70)
    
    # 1. Verificar que el servidor está corriendo
    try:
        response = requests.get("http://localhost:8000/")
        print("✅ Servidor AGPC activo")
    except:
        print("❌ ERROR: Servidor no está corriendo. Ejecuta 'python main.py' primero")
        return
    
    # 2. Reiniciar colección ChromaDB
    print("\n🗑️  Reiniciando colección ChromaDB...")
    response = requests.post("http://localhost:8000/debug/reiniciar-coleccion/")
    print(response.json())
    
    # 3. Cargar dataset
    print("\n📂 Cargando dataset legal_dataset_200.json...")
    
    with open('legal_dataset_200.json', 'r', encoding='utf-8') as f:
        dataset = json.load(f)
    
    conversaciones = dataset.get('conversaciones', [])
    print(f"📋 Total conversaciones a procesar: {len(conversaciones)}")
    
    # 4. Procesar en batches pequeños con verificación
    BATCH_SIZE = 10
    total_procesadas = 0
    
    for i in range(0, len(conversaciones), BATCH_SIZE):
        batch = conversaciones[i:i+BATCH_SIZE]
        
        print(f"\n📦 Procesando batch {i//BATCH_SIZE + 1}/{(len(conversaciones)-1)//BATCH_SIZE + 1}")
        
        response = requests.post(
            "http://localhost:8000/conversacion/procesar-batch/",
            json={'conversaciones': batch}
        )
        
        if response.status_code == 200:
            resultado = response.json()
            total_procesadas += len(batch)
            print(f"✅ Batch procesado - Total: {total_procesadas}/{len(conversaciones)}")
        else:
            print(f"❌ Error en batch: {response.status_code}")
            print(response.text)
            break
        
        # Pequeña pausa entre batches
        time.sleep(0.5)
    
    # 5. Verificación final
    print("\n" + "=" * 70)
    print("VERIFICACIÓN FINAL")
    print("=" * 70)
    
    # Verificar búsqueda
    print("\n🔍 Probando búsqueda de 'Amparo por mora administrativa'...")
    response = requests.get(
        "http://localhost:8000/buscar/",
        params={'texto': 'Amparo por mora administrativa', 'k': 10}
    )
    
    if response.status_code == 200:
        resultados = response.json()
        print(f"✅ Búsqueda exitosa - {len(resultados)} resultados")
        
        # Mostrar primeros 5 resultados
        print("\n📊 Primeros 5 resultados:")
        for i, r in enumerate(resultados[:5], 1):
            titulo = r.get('titulo', 'Sin título')[:60]
            texto = r.get('texto', '')[:80]
            print(f"  {i}. {titulo}")
            print(f"     {texto}...")
            
            # Verificar si contiene "amparo"
            if 'amparo' in titulo.lower() or 'amparo' in texto.lower():
                print(f"     ✅ CORRECTO - Contiene 'amparo'")
            else:
                print(f"     ❌ INCORRECTO - No contiene 'amparo'")
    else:
        print(f"❌ Error en búsqueda: {response.status_code}")
    
    print("\n" + "=" * 70)
    print("PROCESO COMPLETADO")
    print("=" * 70)

if __name__ == "__main__":
    cargar_dataset_limpio()