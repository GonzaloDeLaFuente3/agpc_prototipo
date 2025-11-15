#!/usr/bin/env python3
"""
Verifica si hay duplicados en el dataset original.
"""

import json

print("="*80)
print("VERIFICACIÓN DE DATASET ORIGINAL")
print("="*80)

# Cargar dataset
with open('legal_dataset_200.json', 'r', encoding='utf-8') as f:
    dataset = json.load(f)

conversaciones = dataset.get('conversaciones', [])
print(f"\n📊 Total conversaciones: {len(conversaciones)}")

# Buscar conversaciones con "amparo por mora"
conversaciones_amparo = []
for i, conv in enumerate(conversaciones):
    contenido = conv.get('contenido', '')
    if 'amparo por mora' in contenido.lower():
        conversaciones_amparo.append({
            'index': i,
            'titulo': conv.get('titulo', ''),
            'contenido': contenido,
            'hash': hash(contenido)  # Para detectar duplicados
        })

print(f"✅ Encontradas {len(conversaciones_amparo)} conversaciones con 'amparo por mora'\n")

# Verificar duplicados por contenido
contenidos_vistos = {}
duplicados = []

for i, conv in enumerate(conversaciones_amparo):
    contenido_hash = conv['hash']
    
    if contenido_hash in contenidos_vistos:
        duplicados.append({
            'original_idx': contenidos_vistos[contenido_hash],
            'duplicado_idx': i,
            'titulo': conv['titulo']
        })
    else:
        contenidos_vistos[contenido_hash] = i

if duplicados:
    print(f"⚠️ ENCONTRADOS {len(duplicados)} DUPLICADOS:")
    for dup in duplicados:
        print(f"   - '{dup['titulo']}' (indices: {dup['original_idx']} y {dup['duplicado_idx']})")
else:
    print("✅ NO hay conversaciones duplicadas")

print("\n" + "="*80)
print("ANÁLISIS DE CONTENIDO")
print("="*80)

# Mostrar primeras 3 conversaciones completas
print("\n📋 Primeras 3 conversaciones de amparo:\n")
for i, conv in enumerate(conversaciones_amparo[:3], 1):
    print(f"{i}. TÍTULO: {conv['titulo']}")
    print(f"   ÍNDICE: {conv['index']}")
    print(f"   LONGITUD: {len(conv['contenido'])} caracteres")
    print(f"   CONTENIDO COMPLETO:")
    print(f"   {'-'*76}")
    print(f"   {conv['contenido']}")
    print(f"   {'-'*76}\n")

# Analizar estructura
print("\n" + "="*80)
print("ANÁLISIS DE FRAGMENTACIÓN ESPERADA")
print("="*80)

from agent.fragmentador import criterio_fragmentacion_semantica

for i, conv in enumerate(conversaciones_amparo[:3], 1):
    print(f"\n{i}. Conversación: {conv['titulo']}")
    
    fragmentos = criterio_fragmentacion_semantica(conv['contenido'])
    
    print(f"   Fragmentos generados: {len(fragmentos)}")
    
    for j, frag in enumerate(fragmentos, 1):
        print(f"\n   Fragmento {j}:")
        print(f"      Longitud: {len(frag)} caracteres")
        print(f"      Palabras: {len(frag.split())} palabras")
        print(f"      Contenido: {frag[:100]}...")
        
        # Verificar si hay duplicados en los fragmentos
        if j > 1 and frag == fragmentos[j-2]:
            print(f"      ⚠️ DUPLICADO del fragmento anterior")

print("\n" + "="*80)
print("FIN DE LA VERIFICACIÓN")
print("="*80)