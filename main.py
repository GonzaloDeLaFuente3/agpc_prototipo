#Comando para ejecutar : uvicorn main:app --reload
# main.py
from fastapi import FastAPI
from agent import grafo
from pydantic import BaseModel
from typing import List, Optional
from agent import responder
from fastapi.staticfiles import StaticFiles
import os
from agent.semantica import indexar_documento
from agent.semantica import buscar_similares

grafo.cargar_desde_disco()# ← cargar contexto si existe

# Reindexar lo que ya está guardado en contexto.json
for id, datos in grafo.obtener_todos().items():
    indexar_documento(id, datos["texto"])

app = FastAPI()

class EntradaContexto(BaseModel):
    titulo: str
    texto: str

@app.post("/contexto/")
def agregar_contexto(entrada: EntradaContexto):
    nuevo_id = grafo.agregar_contexto(entrada.titulo, entrada.texto)
    return {"status": "agregado", "id": nuevo_id}

@app.get("/contexto/")
def obtener_contextos():
    return grafo.obtener_todos()

@app.get("/contexto/relacionados/")
def obtener_relacionados(id: str):
    return grafo.obtener_relacionados(id)

@app.get("/preguntar/")
def preguntar(pregunta: str):
    pregunta = pregunta.strip()
    
    print(f"Pregunta recibida: '{pregunta}'")

    todos_contextos = grafo.obtener_todos()
    
    # Si no hay contextos almacenados
    if not todos_contextos:
        return {"respuesta": "[ERROR] No hay contextos almacenados en el sistema", "contextos_utilizados": []}
    
    # Búsqueda automática usando embeddings semánticos
    print("Buscando contextos relevantes automáticamente...")
    ids_similares = buscar_similares(pregunta, k=5)  # Top 5 más relevantes
    print(f"IDs encontrados: {ids_similares}")
    
    contextos_relevantes = {}
    contextos_utilizados_info = []
    
    for id_similar in ids_similares:
        if id_similar in todos_contextos:
            contextos_relevantes[id_similar] = todos_contextos[id_similar]
            contextos_utilizados_info.append({
                "titulo": todos_contextos[id_similar]["titulo"],
                "id": id_similar
            })
    
    # Verificar que hay contextos para procesar
    if not contextos_relevantes:
        return {"respuesta": "[ERROR] No se encontraron contextos relevantes para la pregunta", "contextos_utilizados": []}

    print(f"Contextos que se enviarán a Gemini: {list(contextos_relevantes.keys())}")
    respuesta = responder.responder_con_huggingface(pregunta, contextos_relevantes)
    
    # Agregar información sobre contextos utilizados a la respuesta
    titulos_utilizados = [info["titulo"] for info in contextos_utilizados_info]
    respuesta_completa = f"{respuesta}\n\n📚 Contextos utilizados: {', '.join(titulos_utilizados)}"
    
    return {
        "respuesta": respuesta_completa,
        "contextos_utilizados": contextos_utilizados_info
    }

@app.get("/buscar/")
def buscar_por_texto(texto: str):
    from agent import grafo
    from agent.semantica import buscar_similares

    texto = texto.strip()
    ids_similares = buscar_similares(texto)
    todos = grafo.obtener_todos()
    resultados = {id: todos[id] for id in ids_similares if id in todos}
    return resultados

# Asegurar que la carpeta static existe
os.makedirs("static", exist_ok=True)

app.mount("/", StaticFiles(directory="static", html=True), name="static")