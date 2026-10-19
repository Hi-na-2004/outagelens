import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from . import db
from .config import get_settings
from .services import answer, retrieval

log = logging.getLogger("outagelens")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_schema()
    db.get_pool()
    yield


app = FastAPI(title="OutageLens", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


class SearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    mode: Literal["vector", "keyword", "hybrid"] = "hybrid"
    top_k: int = Field(5, ge=1, le=20)
    rerank: bool = False
    category: str | None = None
    company: str | None = None
    year_from: int | None = None


class AskRequest(BaseModel):
    query: str = Field(min_length=3, max_length=2000)
    top_k: int = Field(4, ge=1, le=8)
    category: str | None = None
    company: str | None = None
    year_from: int | None = None


@app.middleware("http")
async def timing(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Process-Time-ms"] = f"{ms:.1f}"
    if request.url.path.startswith("/api"):
        log.info("%s %s %d %.1fms", request.method, request.url.path, response.status_code, ms)
    return response


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    try:
        with db.get_pool().connection() as conn:
            conn.execute("SELECT 1")
        return {"status": "ok", "llm_provider": get_settings().llm_provider}
    except Exception as exc:
        raise HTTPException(503, f"database unavailable: {exc}")


@app.post("/api/search")
def search(req: SearchRequest):
    return retrieval.search(**req.model_dump())


@app.post("/api/ask")
def ask(req: AskRequest):
    data = req.model_dump()
    return answer.ask(data.pop("query"), **data)


@app.get("/api/meta")
def meta():
    with db.get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT category, count(*) AS n FROM incidents GROUP BY 1 ORDER BY n DESC")
        categories = cur.fetchall()
        cur.execute("SELECT company, count(*) AS n FROM incidents GROUP BY 1 ORDER BY n DESC")
        companies = cur.fetchall()
    return {"categories": categories, "companies": companies}


@app.get("/api/stats")
def stats():
    s = get_settings()
    with db.get_pool().connection() as conn:
        incidents = conn.execute("SELECT count(*) FROM incidents").fetchone()[0]
        chunks = conn.execute("SELECT count(*) FROM chunks").fetchone()[0]
    return {
        "incidents": incidents,
        "chunks": chunks,
        "embed_model": s.embed_model,
        "rerank_model": s.rerank_model,
        "chunk_words": s.chunk_words,
        "chunk_overlap": s.chunk_overlap,
        "llm_provider": s.llm_provider,
    }
