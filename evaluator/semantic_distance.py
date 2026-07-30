from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


# Load once at module level (important for performance)
_model = SentenceTransformer("all-MiniLM-L6-v2")


# us to test distance from wordplay to answer
def semantic_distance(text1: str, text2: str) -> float:
    """
    Returns semantic distance between two strings (the wordplay and the answer) in [0, 1],
    where 0 = identical meaning, 1 = maximally different.
    """
    embeddings = _model.encode([text1, text2], normalize_embeddings=True)
    similarity = cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]
    distance = 1.0 - similarity
    return float(distance)



# print(f"SCORE: {semantic_distance(": body of water with layer", "SEABED")}")