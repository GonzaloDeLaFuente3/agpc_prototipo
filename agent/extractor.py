# agent/extractor.py

import spacy #librería de procesamiento de lenguaje natural

# Cargar el modelo en español
nlp = spacy.load("es_core_news_sm")

def extraer_entidades(texto):
    doc = nlp(texto)
    return list(set([ent.text.lower() for ent in doc.ents]))  # sin repeticiones

def extraer_palabras_clave(texto):
    doc = nlp(texto)
    palabras = [
        token.lemma_.lower()
        for token in doc
        if not token.is_stop and token.is_alpha and len(token.text) > 3
    ]
    return list(set(palabras))  # eliminar repeticiones
