from sentence_transformers import SentenceTransformer
import numpy as np

# Cargar modelo
print("🔄 Cargando modelo...")
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print("✅ Modelo cargado")

# Textos de prueba
texto1 = "Amparo por mora administrativa"
texto2 = "Ciudadano solicitó subsidio en ANSES y no resuelven el trámite"
texto3 = "Pedido de quiebra por cesación de pagos"

# Generar embeddings
print("\n🔄 Generando embeddings...")
emb1 = model.encode([texto1])[0]
emb2 = model.encode([texto2])[0]
emb3 = model.encode([texto3])[0]

# Calcular similitudes
def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

sim_1_2 = cosine_similarity(emb1, emb2)
sim_1_3 = cosine_similarity(emb1, emb3)

print(f"\n📊 RESULTADOS:")
print(f"Similitud entre '{texto1}' y '{texto2}': {sim_1_2:.4f}")
print(f"Similitud entre '{texto1}' y '{texto3}': {sim_1_3:.4f}")
print(f"\n{'✅' if sim_1_2 > sim_1_3 else '❌'} El texto 2 {'ES' if sim_1_2 > sim_1_3 else 'NO ES'} más similar a texto 1 que texto 3")