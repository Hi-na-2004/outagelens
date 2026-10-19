"""Turns a raw postmortem into structured, filterable fields."""
import json

from . import llm

CATEGORIES = [
    "bad_deploy", "config_change", "capacity_overload", "dependency_failure",
    "network", "database", "hardware_power", "software_bug", "security",
    "human_error", "unknown",
]

_KEYWORDS = {
    "bad_deploy": ["deploy", "rollout", "rolled out", "rollback", "rolled back", "release", "canary"],
    "config_change": ["configuration", "config", "feature flag", "setting", "certificate", "expired"],
    "capacity_overload": ["capacity", "overload", "traffic spike", "thundering herd", "exhaust", "saturat", "throttl"],
    "dependency_failure": ["dependency", "upstream", "third-party", "downstream", "provider"],
    "network": ["network", "bgp", "dns", "routing", "packet", "switch", "fiber"],
    "database": ["database", "replica", "replication", "failover", "postgres", "mysql", "shard", "lock"],
    "hardware_power": ["power", "data center", "datacenter", "hardware", "disk", "cooling", "generator"],
    "software_bug": ["bug", "regression", "memory leak", "race condition", "crash", "regex"],
    "security": ["attack", "ddos", "breach", "credential", "malicious"],
    "human_error": ["operator", "manual", "typo", "accidentally", "mistake", "ran a command"],
}

FIELDS = ["summary", "root_cause", "detection", "mitigation", "prevention", "impact"]

_PROMPT = """Read this incident postmortem and reply with ONE JSON object and nothing else.
Keys: category, summary, root_cause, detection, mitigation, prevention, impact.
- category must be one of: {cats}
- every other value is at most two plain sentences, written in your own words
- if the report does not say, use "not stated"

POSTMORTEM:
{text}
"""


def heuristic_category(text: str) -> str:
    low = text.lower()
    scores = {c: sum(low.count(k) for k in kws) for c, kws in _KEYWORDS.items()}
    best, hits = max(scores.items(), key=lambda kv: kv[1])
    return best if hits > 0 else "unknown"


def _heuristic(text: str) -> dict:
    first = " ".join(text.split()[:60])
    out = {f: "not stated" for f in FIELDS}
    out["summary"] = first
    out["category"] = heuristic_category(text)
    return out


def extract(text: str, use_llm: bool = True) -> dict:
    if not use_llm:
        return _heuristic(text)
    try:
        raw = llm.generate(
            _PROMPT.format(cats=", ".join(CATEGORIES), text=text[:12000]),
            system="You extract structured facts from engineering postmortems.",
            max_tokens=600,
        )
        data = json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
    except Exception:
        return _heuristic(text)

    out = {f: str(data.get(f) or "not stated").strip() for f in FIELDS}
    cat = str(data.get("category", "")).strip()
    out["category"] = cat if cat in CATEGORIES else heuristic_category(text)
    return out
