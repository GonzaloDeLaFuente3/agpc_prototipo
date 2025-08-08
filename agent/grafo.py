# agent/grafo.py

from agent.extractor import extraer_palabras_clave
import json
import os
from agent.semantica import indexar_documento
import uuid


ARCHIVO_JSON = "data/contexto.json"
contextos = {}


# Funciones de persistencia
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
# ---------------------------

# Relaciones automáticas
def recalcular_relaciones():
    """Recalcula relaciones entre todos los contextos"""
    for id_a, datos_a in contextos.items():
        claves_a = set(datos_a.get("palabras_clave", []))
        relaciones = []
        for id_b, datos_b in contextos.items():
            if id_a == id_b:
                continue
            claves_b = set(datos_b.get("palabras_clave", []))
            if claves_a & claves_b:
                relaciones.append(id_b)
        datos_a["relaciones"] = relaciones

def agregar_contexto(titulo, texto):
    id = str(uuid.uuid4())  # Generar ID único
    claves = extraer_palabras_clave(texto)

    contextos[id] = {
        "titulo": titulo,
        "texto": texto,
        "relaciones": [],# se llenará al recalcular
        "palabras_clave": claves
    }

    recalcular_relaciones()  # recalcula para todos
    guardar_en_disco()
    indexar_documento(id, texto)
    return id

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

