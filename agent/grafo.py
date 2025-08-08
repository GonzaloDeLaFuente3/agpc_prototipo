# agent/grafo.py

from agent.extractor import extraer_palabras_clave
import json
import os
from agent.semantica import indexar_documento


ARCHIVO_JSON = "data/contexto.json"
contextos = {}

# ---------------------------
# Funciones de persistencia
# ---------------------------

def guardar_en_disco():
    os.makedirs("data", exist_ok=True)
    with open(ARCHIVO_JSON, "w", encoding="utf-8") as f:
        json.dump(contextos, f, ensure_ascii=False, indent=2)

def cargar_desde_disco():
    global contextos
    if os.path.exists(ARCHIVO_JSON):
        with open(ARCHIVO_JSON, "r", encoding="utf-8") as f:
            contextos = json.load(f)
    else:
        contextos = {}
# ----------------------------------------------------------------

def agregar_contexto(id, texto, relacionados=None):
    if relacionados is None:
        relacionados = []

    claves = extraer_palabras_clave(texto)

    contextos[id] = {
        "texto": texto,
        "relaciones": relacionados,
        "palabras_clave": claves
    }
    
    guardar_en_disco()
    indexar_documento(id, texto)

def obtener_todos():
    return contextos

def obtener_relacionados(id):
    if id not in contextos:
        return {}

    relacionados = contextos[id]["relaciones"]
    return {rid: contextos[rid] for rid in relacionados if rid in contextos}

def sugerir_relaciones(id):
    if id not in contextos:
        return []

    claves_base = set(contextos[id]["palabras_clave"])
    sugerencias = []

    for otro_id, datos in contextos.items():
        if otro_id == id:
            continue
        claves_otro = set(datos.get("palabras_clave", []))
        coincidencias = claves_base.intersection(claves_otro)

        if coincidencias:
            sugerencias.append({
                "id": otro_id,
                "coincidencias": list(coincidencias)
            })

    return sugerencias

