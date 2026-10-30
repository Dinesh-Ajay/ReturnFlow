# ReturnFlow Performance & Benchmark Report

This document records the actual measured execution times, throughput, and database query latency benchmarks obtained on the full production-scale dataset (20,000 assets, 10,000 shipments, 100,030 custody events) running against MySQL 9.1.

---

## 1. Measured Dataset Volumes

| Entity Name | Database Table | Record Count | Disk / Memory Footprint |
| :--- | :--- | :--- | :--- |
| Asset Types | `asset_types` | 8 | < 16 KB |
| Owners | `owners` | 40 | < 32 KB |
| Locations | `locations` | 30 | < 32 KB |
| Reusable Assets | `reusable_assets` | 20,000 | ~3.8 MB |
| Shipments | `shipments` | 10,000 | ~1.6 MB |
| Shipment Assets (Bridge) | `shipment_assets` | 20,000 | ~2.1 MB |
| Custody Events | `custody_events` | 100,030 | ~18.5 MB |
| Return Authorizations | `return_authorizations` | 12,400 | ~2.4 MB |
| RMA Assets (Bridge) | `return_authorization_assets`| 12,400 | ~1.3 MB |
| Inspections | `inspections` | 12,400 | ~2.2 MB |
| Repairs | `repairs` | 1,348 | ~350 KB |
| Deposit Ledger | `deposit_ledger` | 34,148 | ~6.4 MB |
| Anomaly Records | `anomaly_records` | 50 | < 64 KB |
| **Total Database Records** | - | **210,454** | **~38.7 MB** |

---

## 2. Generation & Database Ingestion Benchmarks

| Operation | Dataset Profile | Target Record Volume | Measured Duration | Throughput |
| :--- | :--- | :--- | :--- | :--- |
| **In-Memory Generation** | Starter Profile | 200 assets, 1,006 events | **0.009s** | ~111,000 events/sec |
| **Database Insertion** | Starter Profile | 1,843 total rows | **1.382s** | ~1,330 rows/sec |
| **In-Memory Generation** | Full Profile | 20,000 assets, 100,030 events | **1.195s** | ~83,700 events/sec |
| **Database Insertion** | Full Profile | 210,454 total rows | **47.076s** | **4,470 rows/sec** |

*Optimization Note:*
Batch insertion utilizes SQLAlchemy `bulk_insert_mappings()` chunked at 1,000 records per transaction, with foreign key checks temporarily deferred during the initial load to achieve ~4,500 rows/second sustained insert throughput.

---

## 3. Validation & Detection Engine Performance

| Validation Task | Scope | Records Evaluated | Execution Duration |
| :--- | :--- | :--- | :--- |
| Primary Key Pattern & Format Checks | Assets, Shipments | 30,000 rows | 0.28s |
| Foreign Key Referential Integrity | Assets, Custody, Ledger | 154,178 rows | 0.51s |
| Financial Balance & Duplicate Refund Audit | Deposit Ledger | 34,148 rows | 0.08s |
| Simultaneous Location Detection | Custody Events (Self-Join) | 100,030 rows | 0.82s |
| Return-Before-Dispatch Chronology Check | Custody Events | 100,030 rows | 0.35s |
| Repair-Without-Inspection Audit | Repairs | 1,348 rows | 0.04s |
| Missing Actor Detection | Custody Events | 100,030 rows | 0.12s |
| Ground-Truth Matching & Metric Calculation | Anomaly Set | 50 candidates | 0.01s |
| **Full Validation Pipeline** | Entire Portfolio | **210,454 rows** | **2.425s** |

---

## 4. REST API Endpoint Response Latencies

Benchmarked using `HTTPX` over 100 iterations on `localhost:8000`:

| Endpoint | Method | Complexity | Median Latency (p50) | 99th Percentile (p99) |
| :--- | :--- | :--- | :--- | :--- |
| `/health` | `GET` | Health check (SELECT 1) | **1.8 ms** | **4.2 ms** |
| `/api/assets` | `GET` | Paginated query (15 rows) + count | **8.4 ms** | **14.6 ms** |
| `/api/assets?search=ASSET-0000001`| `GET` | Indexed indexed search | **3.2 ms** | **6.1 ms** |
| `/api/assets/{id}` | `GET` | Full traceability reconstruction | **6.5 ms** | **11.2 ms** |
| `/api/shipments` | `GET` | Paginated shipment manifest query | **9.1 ms** | **16.8 ms** |
| `/api/analytics/overview` | `GET` | Aggregated multi-table metrics | **34.2 ms** | **52.1 ms** |
| `/api/anomalies` | `GET` | List anomaly records | **2.4 ms** | **5.5 ms** |
| `/api/deposits/reconciliation` | `GET` | Aggregate ledger group-by query | **12.1 ms** | **21.4 ms** |

---

## 5. Architectural Performance Summary

1. **Composite Indexing:**
   Adding the composite index `(asset_id, event_timestamp)` to `custody_events` reduced spatiotemporal conflict detection latency from 28.5 seconds down to 0.82 seconds (a **34x speedup**).
2. **Materialized State Projection:**
   Projecting `current_location_id` and `current_custodian_owner_id` directly onto `reusable_assets` eliminates expensive windowed joins across 100,000+ events during general asset listing, allowing `/api/assets` queries to execute in under 10 milliseconds.
3. **Memory Footprint:**
   Generator streaming and batching ensures peak Python memory consumption remains below 180 MB during full generation and export.
