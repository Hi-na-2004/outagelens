from ..config import get_settings
from . import llm, retrieval

SYSTEM = (
    "You help on-call engineers by comparing their problem with past public incident "
    "reports. Use only the numbered sources. Cite them like [1]. Say what is similar, "
    "the likely cause, how past teams detected it, and how they fixed it. If the sources "
    "do not match the problem, say so plainly. Never invent details."
)


def _context(results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(
            f"[{i}] {r['title']} ({r['company']}, {r['year']}) category: {r['category']}\n"
            f"Root cause: {r['root_cause']}\nDetection: {r['detection']}\n"
            f"Mitigation: {r['mitigation']}\nPrevention: {r['prevention']}\n"
            f"Passage: {r['passage'][:600]}"
        )
    return "\n\n".join(blocks)


def _extractive(results: list[dict]) -> str:
    if not results:
        return "No similar incidents found. Try describing symptoms and what changed recently."
    lines = ["Closest past incidents (no LLM configured, so this is assembled from stored fields):"]
    for i, r in enumerate(results, start=1):
        lines.append(
            f"[{i}] {r['title']}: cause was {r['root_cause']} It was fixed by {r['mitigation']}"
        )
    return "\n".join(lines)


def ask(question: str, top_k: int = 4, **filters) -> dict:
    found = retrieval.search(question, mode="hybrid", top_k=top_k, rerank=True, **filters)
    results = found["results"]
    mode = "extractive"
    text = _extractive(results)
    if results and get_settings().llm_provider != "none":
        try:
            text = llm.generate(
                f"Problem described by the engineer:\n{question}\n\nSources:\n{_context(results)}",
                system=SYSTEM,
            )
            mode = "llm"
        except Exception:
            pass
    return {"answer": text, "answer_mode": mode, "sources": results, "timings_ms": found["timings_ms"]}
