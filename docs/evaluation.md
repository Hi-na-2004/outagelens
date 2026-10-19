# How to evaluate OutageLens honestly

Numbers on a resume only help if you can defend them. This is the method behind `make eval`.

## 1. Build the query set by hand
1. Ingest at least 100 real postmortems (`data/sources.csv` -> `make collect` -> `make ingest`).
2. Run `python -m scripts.make_eval_template -n 60`. It samples incidents and writes stubs.
3. For each stub, read the report and write the query an on-call engineer would type
   mid-incident: symptoms and recent changes, **not** the title or distinctive phrases
   from the report. If your query shares exact rare words with the report, keyword
   search wins trivially and your numbers are inflated.
4. Delete the `_hint_*` fields, save as `eval/queries.jsonl`. Add extra relevant URLs
   when more than one report genuinely fits.

## 2. Keep a held-out split
Tune chunk size, fusion constant and candidate count on about 2/3 of the queries.
Report final numbers on the remaining 1/3 you never tuned against.

## 3. Run and compare
`make eval` prints Recall@1/5/10, MRR and nDCG@10 for vector only, keyword only,
hybrid, and hybrid + rerank. `results/eval_results.json` also lists the queries that
were missed. Read them: the pattern in failures (jargon, vague symptoms, multi-cause
incidents) is your analysis section.

## 4. Experiments worth running (one at a time, one row each)
- Chunk size 120 / 220 / 400 words
- RRF constant 20 / 60 / 100
- Candidate pool 20 / 40 / 80
- Embedding model: bge-small vs all-MiniLM-L6-v2
- With and without category filter

## 5. Latency
`make bench` load tests the API at several concurrency levels. Always report the
hardware (CPU model, RAM, whether Docker ran on a laptop) beside the numbers.
