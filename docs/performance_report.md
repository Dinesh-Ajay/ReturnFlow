# Performance Report

Measured on 2026-10-30 with Python 3.13.9, Windows 11, and local MySQL 9.1.0. The actual dataset contained 20,009 assets, 10,000 shipments, 100,039 custody events, and 34,148 ledger entries.

Run `python -m app.validation.benchmark` to reproduce the read-only measurements. The command measures full-profile generation in memory and database operations against the configured database. Database operations use one warm-up followed by three `perf_counter` runs; the median is reported. Machine-readable output is written to `data/exports/performance_results.json`.

| Operation | Dataset / measured work | Median |
| --- | --- | ---: |
| Full-profile in-memory generation | 20,000 assets, 10,000 shipments, 100,030 generated custody events | 1.234458 s |
| Generated custody events per generation second | Count divided by generator elapsed time | 81,031.51 events/s |
| Database validation | 222,882 mapped rows | 1.754463 s |
| Custody history retrieval | One asset history | 0.000930 s |
| Asset search | Search for first ordered asset ID | 0.339896 s |
| Anomaly detection and evaluation | Five rule detectors and 50 labels | 0.832681 s |
| Analytics overview | Actual database metrics query | 0.326006 s |

The generator throughput is a measured in-memory generation rate. It does not represent database insertion or anomaly detection throughput. The former static `~67,000 evt/s` dashboard display was removed because it did not identify a measured operation.

Database insertion was **not benchmarked** in this report. The generator refuses populated targets unless `--replace-existing` is explicitly supplied, and the audit did not run a replacement load against the user's working database. An isolated full-profile insert in the disposable audit test database took 37.755 seconds during setup; that one-off setup timing was not repeated using the benchmark methodology and is not treated as a benchmark result.

No query plans (`EXPLAIN ANALYZE`) were captured, and no N+1 trace profiler was run. The asset search and analytics timings are relatively high on this machine; investigate MySQL query plans and ORM query counts before asserting an index or query optimization. Index declarations are documented in `docs/data_dictionary.md` and `database/schema.sql`.
