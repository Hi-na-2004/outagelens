| Strategy | Concurrency | Requests | Errors | QPS | p50 ms | p95 ms | p99 ms |
|---|---|---|---|---|---|---|---|
| hybrid | 1 | 60 | 0 | 10.8 | 88.4 | 138.2 | 163.1 |
| hybrid | 8 | 60 | 0 | 6.5 | 1091.0 | 2106.6 | 2336.3 |
| hybrid+rerank | 1 | 60 | 0 | 0.2 | 4985.3 | 7495.0 | 7687.9 |
| hybrid+rerank | 8 | 60 | 0 | 0.2 | 34041.3 | 63582.9 | 67143.4 |
