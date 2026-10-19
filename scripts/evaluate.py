"""Compare retrieval strategies on a hand-labelled query set.
Writes results/eval_results.md (paste into your README) and .json."""
import argparse
import json
import statistics
from pathlib import Path

from app.metrics import mrr, ndcg_at_k, recall_at_k
from app.services import retrieval

STRATEGIES = [
    ("vector only", dict(mode="vector", rerank=False)),
    ("keyword only", dict(mode="keyword", rerank=False)),
    ("hybrid (RRF)", dict(mode="hybrid", rerank=False)),
    ("hybrid + rerank", dict(mode="hybrid", rerank=True)),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries", default="eval/queries.jsonl")
    ap.add_argument("--out", default="results/eval_results")
    args = ap.parse_args()

    cases = [json.loads(l) for l in Path(args.queries).open() if l.strip()]
    cases = [c for c in cases if c.get("query", "").strip() and c.get("relevant_urls")]
    if not cases:
        raise SystemExit("No labelled queries found. See docs/evaluation.md")

    retrieval.search(cases[0]["query"], rerank=True)  # warm up model loading
    summary = {}
    for name, cfg in STRATEGIES:
        r1, r5, r10, rr, nd, lat, misses = [], [], [], [], [], [], []
        for c in cases:
            out = retrieval.search(c["query"], top_k=10, **cfg)
            ranked = [x["url"] for x in out["results"]]
            rel = c["relevant_urls"]
            r1.append(recall_at_k(ranked, rel, 1))
            r5.append(recall_at_k(ranked, rel, 5))
            r10.append(recall_at_k(ranked, rel, 10))
            rr.append(mrr(ranked, rel))
            nd.append(ndcg_at_k(ranked, rel, 10))
            lat.append(out["timings_ms"]["total_ms"])
            if recall_at_k(ranked, rel, 10) == 0:
                misses.append(c["query"])
        summary[name] = {
            "recall@1": statistics.mean(r1), "recall@5": statistics.mean(r5),
            "recall@10": statistics.mean(r10), "mrr": statistics.mean(rr),
            "ndcg@10": statistics.mean(nd), "mean_latency_ms": statistics.mean(lat),
            "n_queries": len(cases), "missed_queries": misses,
        }

    lines = [f"Evaluated on {len(cases)} hand-labelled queries.\n",
             "| Strategy | Recall@1 | Recall@5 | Recall@10 | MRR | nDCG@10 | Mean latency (ms) |",
             "|---|---|---|---|---|---|---|"]
    for name, m in summary.items():
        lines.append(f"| {name} | {m['recall@1']:.3f} | {m['recall@5']:.3f} | {m['recall@10']:.3f} "
                     f"| {m['mrr']:.3f} | {m['ndcg@10']:.3f} | {m['mean_latency_ms']:.0f} |")
    Path(args.out + ".md").write_text("\n".join(lines) + "\n")
    Path(args.out + ".json").write_text(json.dumps(summary, indent=2))
    print("\n".join(lines))
    print(f"\nSaved {args.out}.md and .json. Read the missed_queries in the JSON: they are your failure analysis.")


if __name__ == "__main__":
    main()
