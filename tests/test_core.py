import math

import pytest

from app.metrics import mrr, ndcg_at_k, percentile, recall_at_k
from app.services.chunking import chunk_text
from app.services.extraction import heuristic_category
from app.services.retrieval import rrf_fuse, _tokens


def test_chunk_overlap_and_coverage():
    text = " ".join(f"w{i}" for i in range(500))
    chunks = chunk_text(text, max_words=200, overlap=50)
    assert chunks[0].split()[-50:] == chunks[1].split()[:50]
    assert "w499" in chunks[-1]


def test_chunk_short_and_empty():
    assert chunk_text("") == []
    assert chunk_text("a b c", 200, 40) == ["a b c"]


def test_chunk_rejects_bad_overlap():
    with pytest.raises(ValueError):
        chunk_text("a b c", 10, 10)


def test_rrf_prefers_items_ranked_high_in_both_lists():
    fused = rrf_fuse([[1, 2, 3], [3, 1, 4]], k=60)
    assert [cid for cid, _ in fused][:2] == [1, 3]
    assert math.isclose(dict(fused)[1], 1 / 61 + 1 / 62)


def test_tokens_drops_short_words_and_dupes():
    assert _tokens("DNS is down, DNS!") == ["dns", "down"]


def test_metrics():
    ranked = ["a", "b", "c", "d"]
    assert recall_at_k(ranked, ["b", "z"], 2) == 0.5
    assert mrr(ranked, ["c"]) == pytest.approx(1 / 3)
    assert ndcg_at_k(ranked, ["a"], 10) == 1.0
    assert ndcg_at_k(ranked, ["z"], 10) == 0.0
    assert percentile([1, 2, 3, 4, 5], 50) == 3


def test_heuristic_category():
    assert heuristic_category("We deployed a release and had to roll back the rollout") == "bad_deploy"
    assert heuristic_category("nothing recognisable here") == "unknown"
