# agent/grafo.py

contextos = {}

def agregar_contexto(id, texto):
    contextos[id] = {
        "texto": texto,
        "relaciones": []
    }

def obtener_todos():
    return contextos
