# agent/extractor.py - Optimizado
import spacy

# Cargar modelo español una sola vez
nlp = spacy.load("es_core_news_sm")

def extraer_palabras_clave(texto):
    """Extrae palabras clave relevantes del texto."""
    doc = nlp(texto)
    return list(set([
        token.lemma_.lower() 
        for token in doc 
        if not token.is_stop and token.is_alpha and len(token.text) > 3
    ]))