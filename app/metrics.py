"""Ranking metrics. `ranked` is a list of incident URLs, best first;
`relevant` is the set of URLs a human marked as correct for the query."""
import math


def recall_at_k(ranked: list[str], relevant: list[str], k: int) -> float:
    if not relevant:
        return 0.0
    return len(set(ranked[:k]) & set(relevant)) / len(set(relevant))


def mrr(ranked: list[str], relevant: list[str]) -> float:
    rel = set(relevant)
    for i, item in enumerate(ranked, start=1):
        if item in rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked: list[str], relevant: list[str], k: int) -> float:
    rel = set(relevant)
    dcg = sum(1.0 / math.log2(i + 2) for i, item in enumerate(ranked[:k]) if item in rel)
    ideal = sum(1.0 / math.log2(i + 2) for i in range(min(len(rel), k)))
    return dcg / ideal if ideal else 0.0


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    idx = min(len(xs) - 1, max(0, math.ceil(p / 100 * len(xs)) - 1))
    return xs[idx]
