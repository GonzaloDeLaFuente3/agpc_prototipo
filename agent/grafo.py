# agent/grafo.py

contextos = {}

def agregar_contexto(id, texto, relacionados=None):
    if relacionados is None:
        relacionados = []

    contextos[id] = {
        "texto": texto,
        "relaciones": relacionados
    }

def obtener_todos():
    return contextos

def obtener_relacionados(id):
    if id not in contextos:
        return {}

    relacionados = contextos[id]["relaciones"]
    return {rid: contextos[rid] for rid in relacionados if rid in contextos}
