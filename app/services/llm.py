import httpx

from ..config import get_settings


class LLMUnavailable(RuntimeError):
    pass


def generate(prompt: str, system: str = "", max_tokens: int = 700) -> str:
    s = get_settings()
    if s.llm_provider == "ollama":
        r = httpx.post(
            f"{s.ollama_url}/api/chat",
            json={
                "model": s.ollama_model,
                "stream": False,
                "options": {"num_predict": max_tokens, "temperature": 0.2},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=s.llm_timeout_s,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]

    if s.llm_provider == "anthropic":
        if not s.anthropic_api_key:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set")
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": s.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": s.anthropic_model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=s.llm_timeout_s,
        )
        r.raise_for_status()
        return "".join(b.get("text", "") for b in r.json()["content"])

    raise LLMUnavailable("LLM_PROVIDER is 'none'")
