import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from .config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id          SERIAL PRIMARY KEY,
    url         TEXT UNIQUE NOT NULL,
    title       TEXT NOT NULL,
    company     TEXT,
    year        INT,
    category    TEXT NOT NULL DEFAULT 'unknown',
    summary     TEXT,
    root_cause  TEXT,
    detection   TEXT,
    mitigation  TEXT,
    prevention  TEXT,
    impact      TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           SERIAL PRIMARY KEY,
    incident_id  INT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    chunk_index  INT NOT NULL,
    content      TEXT NOT NULL,
    embedding    vector({dim}),
    tsv          tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    UNIQUE (incident_id, chunk_index)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS incidents_category_idx ON incidents (category);
"""

_pool: ConnectionPool | None = None


def init_schema() -> None:
    s = get_settings()
    with psycopg.connect(s.database_url, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(SCHEMA.format(dim=s.embed_dim))


def get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            get_settings().database_url,
            min_size=2,
            max_size=10,
            kwargs={"autocommit": True},
            configure=register_vector,
            open=True,
        )
    return _pool
