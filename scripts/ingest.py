"""Read a JSONL file of incidents, extract structured fields, chunk, embed, store."""
import argparse
import json
from pathlib import Path

from app import db
from app.config import get_settings
from app.services import embeddings, extraction
from app.services.chunking import chunk_text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="data/raw/incidents.jsonl")
    ap.add_argument("--no-llm", action="store_true", help="heuristic extraction only")
    ap.add_argument("--force", action="store_true", help="re-ingest existing URLs")
    args = ap.parse_args()

    s = get_settings()
    db.init_schema()
    pool = db.get_pool()
    records = [json.loads(line) for line in Path(args.source).open() if line.strip()]
    print(f"{len(records)} records in {args.source}")

    added = 0
    for rec in records:
        with pool.connection() as conn:
            if not args.force and conn.execute(
                "SELECT 1 FROM incidents WHERE url = %s", (rec["url"],)
            ).fetchone():
                continue

            fields = extraction.extract(rec["text"], use_llm=not args.no_llm)
            chunks = chunk_text(rec["text"], s.chunk_words, s.chunk_overlap)
            vectors = embeddings.embed_documents(chunks)

            with conn.transaction():
                iid = conn.execute(
                    """INSERT INTO incidents
                       (url,title,company,year,category,summary,root_cause,detection,
                        mitigation,prevention,impact)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                       ON CONFLICT (url) DO UPDATE SET
                         title=EXCLUDED.title, company=EXCLUDED.company, year=EXCLUDED.year,
                         category=EXCLUDED.category, summary=EXCLUDED.summary,
                         root_cause=EXCLUDED.root_cause, detection=EXCLUDED.detection,
                         mitigation=EXCLUDED.mitigation, prevention=EXCLUDED.prevention,
                         impact=EXCLUDED.impact
                       RETURNING id""",
                    (rec["url"], rec["title"], rec.get("company"), rec.get("year"),
                     fields["category"], fields["summary"], fields["root_cause"],
                     fields["detection"], fields["mitigation"], fields["prevention"],
                     fields["impact"]),
                ).fetchone()[0]
                conn.execute("DELETE FROM chunks WHERE incident_id = %s", (iid,))
                for idx, (text, vec) in enumerate(zip(chunks, vectors)):
                    conn.execute(
                        "INSERT INTO chunks (incident_id, chunk_index, content, embedding) "
                        "VALUES (%s,%s,%s,%s)",
                        (iid, idx, text, vec),
                    )
            added += 1
            print(f"ingested [{fields['category']}] {rec['title'][:70]} ({len(chunks)} chunks)")
    print(f"done: {added} new incidents")


if __name__ == "__main__":
    main()
