from functools import lru_cache

import numpy as np

from ..config import get_settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(get_settings().embed_model)


def embed_documents(texts: list[str], batch_size: int = 32) -> np.ndarray:
    return _model().encode(
        texts, batch_size=batch_size, normalize_embeddings=True, show_progress_bar=False
    )


def embed_query(query: str) -> np.ndarray:
    prefix = get_settings().query_prefix
    return _model().encode(prefix + query, normalize_embeddings=True)
