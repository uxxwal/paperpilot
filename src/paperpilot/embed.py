from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "BAAI/bge-small-en-v1.5"
EMBED_DIM = 384
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str], batch_size: int = 32) -> np.ndarray:
    """Embed chunks. Returns shape (len(texts), 384), each row length 1."""
    return get_model().encode(
        texts, batch_size=batch_size, normalize_embeddings=True, convert_to_numpy=True
    )


def embed_query(question: str) -> np.ndarray:
    """Embed a search question (with the BGE query prefix), Returns shape (384,)."""
    return embed_texts([QUERY_PREFIX + question])[0]
