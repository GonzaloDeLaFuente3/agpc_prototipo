#Comando para ejecutar : uvicorn main:app --reload
# main.py
from fastapi import FastAPI
from agent import grafo
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class EntradaContexto(BaseModel):
    id: str
    texto: str
    relacionados: Optional[List[str]] = []

@app.get("/")
def read_root():
    return {"message": "AGPC prototipo funcionando"}

@app.post("/contexto/")
def agregar_contexto(entrada: EntradaContexto):
    grafo.agregar_contexto(entrada.id, entrada.texto, entrada.relacionados)
    return {"status": "agregado"}

@app.get("/contexto/")
def obtener_contextos():
    return grafo.obtener_todos()

@app.get("/contexto/relacionados/")
def obtener_relacionados(id: str):
    return grafo.obtener_relacionados(id)

@app.get("/contexto/sugerencias/")
def sugerir_relaciones(id: str):
    return grafo.sugerir_relaciones(id)
