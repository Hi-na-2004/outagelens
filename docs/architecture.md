# Architecture notes

## Why incident-level results
Chunks are the unit of search, but an engineer wants incidents. After ranking chunks,
the best chunk per incident is kept and duplicates are dropped, so one long report
cannot fill the whole result list.

## Why RRF instead of weighted scores
Cosine similarity and `ts_rank_cd` are on different scales. Reciprocal Rank Fusion
uses ranks only, so there is no weight to hand-tune and it behaves predictably when
one retriever returns nothing (for example, a query of only stop words).

## Why Postgres full-text instead of a separate BM25 library
One datastore, one transaction boundary, and the keyword index lives beside the
vectors. Trade-off: `ts_rank_cd` is not BM25. A dedicated BM25 index is a good
experiment to run and report.

## Structured extraction
Each report is read once at ingestion. The LLM returns category, summary, root cause,
detection, mitigation, prevention and impact. If the model's JSON is invalid or the
category is outside the allowed list, a keyword heuristic takes over, so ingestion never
fails because of the model.

## Known limitations (put these in your README, they show maturity)
- HNSW with a selective filter can return fewer than N rows (post-filtering). If
  filtered recall drops, raise `hnsw.ef_search` or use pgvector iterative scans.
- Heuristic categories are coarse; one incident often has several causes.
- Relevance labels are binary and written by one person.
