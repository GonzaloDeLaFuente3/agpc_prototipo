#Comando para ejecutar : uvicorn main:app --reload
# main.py
from fastapi import FastAPI
from agent import grafo

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "AGPC prototipo funcionando"}

@app.post("/contexto/")
def agregar_contexto(id: str, texto: str):
    grafo.agregar_contexto(id, texto)
    return {"status": "agregado"}

@app.get("/contexto/")
def obtener_contextos():
    return grafo.obtener_todos()
