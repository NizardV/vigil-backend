from sentence_transformers import SentenceTransformer

# Modèle multilingue léger — parfait pour du contenu FR/EN
_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")


def get_embedding(text: str) -> list[float]:
    """Génère un embedding 768D pour un texte donné."""
    embedding = _model.encode(text, normalize_embeddings=True)
    return embedding.tolist()

