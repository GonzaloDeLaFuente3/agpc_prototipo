# agent/grafo.py

from agent.extractor import extraer_palabras_clave

contextos = {}

def agregar_contexto(id, texto, relacionados=None):
    if relacionados is None:
        relacionados = []

    claves = extraer_palabras_clave(texto)

    contextos[id] = {
        "texto": texto,
        "relaciones": relacionados,
        "palabras_clave": claves
    }

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

