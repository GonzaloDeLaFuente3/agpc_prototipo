# agent/extractor.py
import spacy #librería de procesamiento de lenguaje natural

# Cargar el modelo en español
nlp = spacy.load("es_core_news_sm")

def extraer_palabras_clave(texto):#toma un texto y devuelve las palabras más importantes, limpiando y procesando el contenido.
    doc = nlp(texto)#spaCy analiza todo el texto y lo "entiende" gramaticalmente
    palabras = [
        token.lemma_.lower() # lemmatiza la palabra, la convierte a minúsculas
        for token in doc 
        if not token.is_stop and token.is_alpha and len(token.text) > 3 # filtra palabras que no son palabras vacías, son alfabéticas y tienen más de 3 caracteres
    ]
    return list(set(palabras))  # eliminar repeticiones
