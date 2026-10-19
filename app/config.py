from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://outage:outage_dev@localhost:5432/outagelens"

    embed_model: str = "BAAI/bge-small-en-v1.5"
    embed_dim: int = 384
    query_prefix: str = "Represent this sentence for searching relevant passages: "
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    chunk_words: int = 220
    chunk_overlap: int = 40
    candidates: int = 40      # chunks pulled from each retriever before fusion
    rrf_k: int = 60           # reciprocal-rank-fusion constant

    llm_provider: str = "none"  # none | ollama | anthropic
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    llm_timeout_s: float = 120.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
