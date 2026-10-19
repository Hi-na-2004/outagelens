from functools import lru_cache

from ..config import get_settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import CrossEncoder

    return CrossEncoder(get_settings().rerank_model)


def score_pairs(query: str, passages: list[str]) -> list[float]:
    if not passages:
        return []
    return [float(x) for x in _model().predict([(query, p) for p in passages])]
