import json
import statistics

from app.metrics import mrr, recall_at_k
from app.services import retrieval

cases = [json.loads(l) for l in open("eval/queries.final2.jsonl", encoding="utf-8") if l.strip()]
assert len(cases) == 62, len(cases)
STRATS = [("vector only", dict(mode="vector", rerank=False)),
          ("keyword only", dict(mode="keyword", rerank=False)),
          ("hybrid (RRF)", dict(mode="hybrid", rerank=False)),
          ("hybrid + rerank", dict(mode="hybrid", rerank=True))]
GROUPS = [("hand-written", range(0, 6)),
          ("LLM-drafted", range(6, 62)),
          ("all", range(0, 62))]

retrieval.search(cases[0]["query"], rerank=True)
ranked = {}
for name, cfg in STRATS:
    ranked[name] = []
    for c in cases:
        out = retrieval.search(c["query"], top_k=10, **cfg)
        ranked[name].append([x["url"] for x in out["results"]])

lines = ["Evaluated on 62 queries: 6 hand-written, 56 LLM-drafted from the incident reports.", "",
         "| Strategy | Group | n | Recall@1 | Recall@5 | Recall@10 | MRR |",
         "|---|---|---|---|---|---|---|"]
for name, _ in STRATS:
    for gname, idx in GROUPS:
        idx = list(idx)
        vals = {k: [] for k in (1, 5, 10)}
        rr = []
        for i in idx:
            rel = cases[i]["relevant_urls"]
            for k in vals:
                vals[k].append(recall_at_k(ranked[name][i], rel, k))
            rr.append(mrr(ranked[name][i], rel))
        lines.append("| %s | %s | %d | %.3f | %.3f | %.3f | %.3f |" % (
            name, gname, len(idx), statistics.mean(vals[1]), statistics.mean(vals[5]),
            statistics.mean(vals[10]), statistics.mean(rr)))

text = "\n".join(lines)
print("\n" + text)
open("results/eval_v3.md", "w", encoding="utf-8").write(text + "\n")

missed = {}
for name, _ in STRATS:
    missed[name] = [cases[i]["query"] for i in range(62)
                    if recall_at_k(ranked[name][i], cases[i]["relevant_urls"], 10) == 0]
json.dump(missed, open("results/eval_v3_missed.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("\nMissed in top 10:", {k: len(v) for k, v in missed.items()})
print("Saved results/eval_v3.md and results/eval_v3_missed.json")
