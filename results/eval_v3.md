Evaluated on 62 queries: 6 hand-written, 56 LLM-drafted from the incident reports.

| Strategy | Group | n | Recall@1 | Recall@5 | Recall@10 | MRR |
|---|---|---|---|---|---|---|
| vector only | hand-written | 6 | 0.333 | 0.833 | 0.833 | 0.514 |
| vector only | LLM-drafted | 56 | 0.625 | 0.911 | 0.964 | 0.742 |
| vector only | all | 62 | 0.597 | 0.903 | 0.952 | 0.720 |
| keyword only | hand-written | 6 | 0.000 | 0.333 | 0.500 | 0.188 |
| keyword only | LLM-drafted | 56 | 0.536 | 0.768 | 0.893 | 0.631 |
| keyword only | all | 62 | 0.484 | 0.726 | 0.855 | 0.588 |
| hybrid (RRF) | hand-written | 6 | 0.167 | 0.333 | 0.833 | 0.272 |
| hybrid (RRF) | LLM-drafted | 56 | 0.661 | 0.946 | 0.964 | 0.764 |
| hybrid (RRF) | all | 62 | 0.613 | 0.887 | 0.952 | 0.717 |
| hybrid + rerank | hand-written | 6 | 0.333 | 0.500 | 0.833 | 0.465 |
| hybrid + rerank | LLM-drafted | 56 | 0.839 | 0.946 | 0.982 | 0.892 |
| hybrid + rerank | all | 62 | 0.790 | 0.903 | 0.968 | 0.850 |
