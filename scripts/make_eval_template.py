"""Sample ingested incidents and write eval/queries.template.jsonl.
For each line, YOU write the "query": how an on-call engineer would describe the
symptoms WITHOUT copying words from the report's title. See docs/evaluation.md."""
import argparse
import json

from psycopg.rows import dict_row

from app import db


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=50)
    ap.add_argument("--out", default="eval/queries.template.jsonl")
    args = ap.parse_args()

    with db.get_pool().connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT url, title, category, summary FROM incidents ORDER BY random() LIMIT %s", (args.n,))
        rows = cur.fetchall()
    with open(args.out, "w") as fh:
        for r in rows:
            fh.write(json.dumps({"query": "", "relevant_urls": [r["url"]],
                                 "_hint_title": r["title"], "_hint_summary": r["summary"]}) + "\n")
    print(f"wrote {len(rows)} stubs to {args.out}. Fill in 'query', delete the _hint fields, "
          f"save as eval/queries.jsonl")


if __name__ == "__main__":
    main()
