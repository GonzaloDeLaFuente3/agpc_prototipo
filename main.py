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

grafo.cargar_desde_disco()# ← cargar contexto si existe

# Reindexar lo que ya está guardado en contexto.json
for id, datos in grafo.obtener_todos().items():
    indexar_documento(id, datos["texto"])

app = FastAPI()



class EntradaContexto(BaseModel):
    titulo: str
    texto: str

# @app.get("/")
# def read_root():
#     return {"message": "AGPC prototipo funcionando"}

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

@app.get("/contexto/sugerencias/")
def sugerir_relaciones(id: str):
    return grafo.sugerir_relaciones(id)



@app.get("/preguntar/")
def preguntar(pregunta: str, id: str):
    pregunta = pregunta.strip()
    id = id.strip()  # <- esto elimina espacios y saltos de línea

    print(f"ID solicitado: '{id}'")

    # Verificar que el contexto existe
    todos_contextos = grafo.obtener_todos()
    
    if id not in todos_contextos:
        return {"respuesta": f"[ERROR] No se encontró el contexto con id: {id}"}

    relacionados = grafo.obtener_relacionados(id)
    
    relacionados[id] = todos_contextos[id]  # incluir el nodo base
    

    # Verificar que hay contextos para procesar
    if not relacionados:
        return {"respuesta": "[ERROR] No se encontraron contextos relacionados"}

    respuesta = responder.responder_con_huggingface(pregunta, relacionados)
    return {"respuesta": respuesta}

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