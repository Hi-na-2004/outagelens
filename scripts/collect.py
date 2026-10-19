"""Download public postmortems listed in data/sources.csv (columns: url,company)
and save cleaned text to data/raw/incidents.jsonl.

Be a polite crawler: one request per second, identify yourself, and check each
site's terms. Store links plus your own extracted fields, do not republish articles."""
import argparse
import csv
import json
import time
from pathlib import Path

import httpx
import trafilatura

UA = "OutageLens-research/1.0 (personal portfolio project)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="data/sources.csv")
    ap.add_argument("--out", default="data/raw/incidents.jsonl")
    ap.add_argument("--min-words", type=int, default=150)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = set()
    if out.exists():
        done = {json.loads(line)["url"] for line in out.open() if line.strip()}

    saved = skipped = 0
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True, timeout=30) as client, \
            out.open("a") as fh:
        for row in csv.DictReader(Path(args.sources).open()):
            url = row["url"].strip()
            if not url or url.startswith("#") or url in done:
                continue
            try:
                resp = client.get(url)
                resp.raise_for_status()
                text = trafilatura.extract(resp.text, include_comments=False) or ""
                meta = trafilatura.extract_metadata(resp.text)
            except Exception as exc:
                print(f"skip  {url}  ({exc})")
                skipped += 1
                continue
            if len(text.split()) < args.min_words:
                print(f"skip  {url}  (too short)")
                skipped += 1
                continue
            year = int(meta.date[:4]) if meta and meta.date else None
            title = (meta.title if meta and meta.title else url).strip()
            fh.write(json.dumps({"url": url, "company": row.get("company", "").strip(),
                                 "title": title, "year": year, "text": text}) + "\n")
            fh.flush()
            saved += 1
            print(f"saved {url}")
            time.sleep(1.0)
    print(f"done: {saved} saved, {skipped} skipped -> {out}")


if __name__ == "__main__":
    main()
