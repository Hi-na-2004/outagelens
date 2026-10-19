"""Load test the running API. Reports p50/p95/p99 latency and throughput per
concurrency level, for plain hybrid search and for hybrid + rerank."""
import argparse
import asyncio
import json
import random
import time
from pathlib import Path

import httpx

from app.metrics import percentile

FALLBACK = ["latency spiked right after a deploy", "database failover caused errors",
            "dns outage", "certificate expired and traffic dropped", "disk full on primary"]


async def run(client, url, queries, total, concurrency, payload_extra):
    latencies, errors = [], 0
    sem = asyncio.Semaphore(concurrency)

    async def one():
        nonlocal errors
        async with sem:
            t = time.perf_counter()
            try:
                r = await client.post(url, json={"query": random.choice(queries), "top_k": 5, **payload_extra})
                r.raise_for_status()
                latencies.append((time.perf_counter() - t) * 1000)
            except Exception:
                errors += 1

    t0 = time.perf_counter()
    await asyncio.gather(*[one() for _ in range(total)])
    wall = time.perf_counter() - t0
    return {"requests": total, "errors": errors, "qps": round(len(latencies) / wall, 1),
            "p50_ms": round(percentile(latencies, 50), 1), "p95_ms": round(percentile(latencies, 95), 1),
            "p99_ms": round(percentile(latencies, 99), 1)}


async def main_async(a):
    queries = FALLBACK
    qp = Path(a.queries)
    if qp.exists():
        qs = [json.loads(l).get("query", "") for l in qp.open() if l.strip()]
        queries = [q for q in qs if q.strip()] or FALLBACK

    rows = []
    async with httpx.AsyncClient(timeout=120, limits=httpx.Limits(max_connections=256)) as client:
        await run(client, f"{a.base}/api/search", queries, 20, 2, {})  # warm up
        for label, extra in [("hybrid", {"mode": "hybrid"}), ("hybrid+rerank", {"mode": "hybrid", "rerank": True})]:
            for c in a.concurrency:
                res = await run(client, f"{a.base}/api/search", queries, a.requests, c, extra)
                rows.append({"strategy": label, "concurrency": c, **res})
                print(rows[-1])

    lines = ["| Strategy | Concurrency | Requests | Errors | QPS | p50 ms | p95 ms | p99 ms |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['strategy']} | {r['concurrency']} | {r['requests']} | {r['errors']} | "
                     f"{r['qps']} | {r['p50_ms']} | {r['p95_ms']} | {r['p99_ms']} |")
    Path(a.out).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    ap.add_argument("--queries", default="eval/queries.jsonl")
    ap.add_argument("--requests", type=int, default=300)
    ap.add_argument("--concurrency", type=int, nargs="+", default=[1, 8, 32])
    ap.add_argument("--out", default="results/benchmark.md")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
