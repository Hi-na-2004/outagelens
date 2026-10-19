.PHONY: up demo collect ingest eval bench test
up:        ## start Postgres + API
	docker compose up --build -d
demo:      ## load the 6 synthetic incidents (smoke test only)
	docker compose exec app python -m scripts.ingest --source data/sample/synthetic.jsonl --no-llm
collect:   ## download postmortems listed in data/sources.csv
	docker compose exec app python -m scripts.collect
ingest:    ## load collected real incidents
	docker compose exec app python -m scripts.ingest --source data/raw/incidents.jsonl
eval:      ## retrieval quality: recall@k, MRR, nDCG across 4 strategies
	docker compose exec app python -m scripts.evaluate
bench:     ## latency + throughput under concurrency
	docker compose exec app python -m scripts.benchmark
test:
	python -m pytest -q
