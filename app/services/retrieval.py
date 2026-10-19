"""Hybrid retrieval: pgvector (meaning) + Postgres full-text (exact terms),
merged with Reciprocal Rank Fusion, optionally reordered by a cross-encoder.
Results are returned per incident, not per chunk."""
import re
import time

from psycopg.rows import dict_row

from .. import db
from ..config import get_settings
from . import embeddings, rerank as reranker

MODES = ("vector", "keyword", "hybrid")
_INCIDENT_COLS = (
    "id, url, title, company, year, category, summary, "
    "root_cause, detection, mitigation, prevention, impact"
)


def rrf_fuse(rank_lists: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """Each list is chunk ids, best first. A chunk's score is the sum of 1/(k+rank)."""
    scores: dict[int, float] = {}
    for ranking in rank_lists:
        for rank, cid in enumerate(ranking, start=1):
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)


def _tokens(query: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[a-z0-9]{3,}", query.lower())))


def _filters(category, company, year_from) -> tuple[str, list]:
    conds, params = [], []
    if category:
        conds.append("i.category = %s")
        params.append(category)
    if company:
        conds.append("i.company ILIKE %s")
        params.append(company)
    if year_from:
        conds.append("i.year >= %s")
        params.append(year_from)
    return ("".join(f" AND {c}" for c in conds), params)


def _query(sql: str, params: list) -> list[dict]:
    with db.get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 2)


def search(
    query: str,
    mode: str = "hybrid",
    top_k: int = 5,
    rerank: bool = False,
    category: str | None = None,
    company: str | None = None,
    year_from: int | None = None,
) -> dict:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}")
    s = get_settings()
    where, fparams = _filters(category, company, year_from)
    n = s.candidates
    timings: dict[str, float] = {}
    t_all = time.perf_counter()
    rows: dict[int, dict] = {}
    rankings: list[list[int]] = []

    if mode in ("vector", "hybrid"):
        t = time.perf_counter()
        qvec = embeddings.embed_query(query)
        timings["embed_ms"] = _ms(t)
        t = time.perf_counter()
        found = _query(
            f"""SELECT c.id, c.incident_id, c.content FROM chunks c
                JOIN incidents i ON i.id = c.incident_id
                WHERE true{where} ORDER BY c.embedding <=> %s LIMIT %s""",
            [*fparams, qvec, n],
        )
        timings["vector_ms"] = _ms(t)
        rows.update({r["id"]: r for r in found})
        rankings.append([r["id"] for r in found])

    if mode in ("keyword", "hybrid"):
        tokens = _tokens(query)
        t = time.perf_counter()
        found = []
        if tokens:
            tsq = " | ".join(tokens)
            found = _query(
                f"""SELECT c.id, c.incident_id, c.content FROM chunks c
                    JOIN incidents i ON i.id = c.incident_id
                    WHERE c.tsv @@ to_tsquery('english', %s){where}
                    ORDER BY ts_rank_cd(c.tsv, to_tsquery('english', %s)) DESC LIMIT %s""",
                [tsq, *fparams, tsq, n],
            )
        timings["keyword_ms"] = _ms(t)
        rows.update({r["id"]: r for r in found})
        rankings.append([r["id"] for r in found])

    t = time.perf_counter()
    ordered = rrf_fuse(rankings, s.rrf_k)
    timings["fuse_ms"] = _ms(t)

    if rerank and ordered:
        t = time.perf_counter()
        ids = [cid for cid, _ in ordered[:n]]
        scores = reranker.score_pairs(query, [rows[c]["content"] for c in ids])
        ordered = sorted(zip(ids, scores), key=lambda kv: kv[1], reverse=True)
        timings["rerank_ms"] = _ms(t)

    picks, seen = [], set()
    for cid, score in ordered:
        row = rows[cid]
        if row["incident_id"] in seen:
            continue
        seen.add(row["incident_id"])
        picks.append((row, score))
        if len(picks) == top_k:
            break

    t = time.perf_counter()
    meta = {}
    if picks:
        meta = {
            r["id"]: r
            for r in _query(
                f"SELECT {_INCIDENT_COLS} FROM incidents WHERE id = ANY(%s)",
                [[row["incident_id"] for row, _ in picks]],
            )
        }
    timings["db_fetch_ms"] = _ms(t)

    results = []
    for row, score in picks:
        item = dict(meta[row["incident_id"]])
        item["score"] = round(float(score), 4)
        item["passage"] = row["content"]
        results.append(item)

    timings["total_ms"] = _ms(t_all)
    return {"mode": mode, "reranked": bool(rerank), "results": results, "timings_ms": timings}
