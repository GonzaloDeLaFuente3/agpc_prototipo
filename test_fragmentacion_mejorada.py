#!/usr/bin/env python3
"""
Prueba la fragmentación mejorada.
"""

from agent.fragmentador import criterio_fragmentacion_semantica
import json

print("="*80)
print("TEST DE FRAGMENTACIÓN MEJORADA")
print("="*80)

# Cargar primera conversación de amparo
with open('legal_dataset_200.json', 'r', encoding='utf-8') as f:
    dataset = json.load(f)

conversacion = None
for conv in dataset.get('conversaciones', []):
    if 'amparo por mora' in conv.get('contenido', '').lower():
        conversacion = conv
        break

print(f"\n📄 CONVERSACIÓN ORIGINAL:")
print(f"   Título: {conversacion['titulo']}")
print(f"   Longitud: {len(conversacion['contenido'])} caracteres")
print(f"   Palabras: {len(conversacion['contenido'].split())} palabras")
print(f"\n   Contenido:")
print(f"   {'-'*76}")
print(f"   {conversacion['contenido']}")
print(f"   {'-'*76}")

print(f"\n📦 FRAGMENTACIÓN CON NUEVO ALGORITMO:")
print(f"   (min_palabras=50, max_palabras=300)")

fragmentos = criterio_fragmentacion_semantica(
    conversacion['contenido'],
    max_palabras=300,
    min_palabras=50
)

print(f"\n✅ Total fragmentos: {len(fragmentos)}")

for i, frag in enumerate(fragmentos, 1):
    palabras = len(frag.split())
    print(f"\n   Fragmento {i}:")
    print(f"      Longitud: {len(frag)} caracteres")
    print(f"      Palabras: {palabras} palabras")
    print(f"      Contenido:")
    print(f"      {'-'*72}")
    print(f"      {frag}")
    print(f"      {'-'*72}")
    
    # Verificar calidad
    if palabras < 20:
        print(f"      ⚠️ WARNING: Fragmento muy corto")
    elif palabras < 50:
        print(f"      ⚠️ Fragmento corto (debajo de min_palabras)")
    else:
        print(f"      ✅ Fragmento con buen contexto")

print("\n" + "="*80)
print("COMPARACIÓN:")
print(f"   Antes: 5 fragmentos de 12-15 palabras cada uno")
print(f"   Ahora: {len(fragmentos)} fragmentos de ~{sum(len(f.split()) for f in fragmentos)//len(fragmentos) if fragmentos else 0} palabras promedio")
print("="*80)