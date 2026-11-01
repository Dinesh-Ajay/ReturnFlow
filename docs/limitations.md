# ReturnFlow Known Limitations & Future Improvements

This document transparently records current system limitations and planned architectural enhancements.

---

## 1. Known Architectural Limitations

1. **Single Currency Handling:**
   - The current financial ledger assumes all deposit, repair, and penalty figures are denominated in USD. Multi-currency conversions and foreign exchange hedging are not currently implemented.
2. **Fixed Reference Date:**
   - Synthetic data generation and overdue standing calculations use a static `REFERENCE_DATE` (`2026-10-22`) for perfect reproducibility. In live production, this should switch to `datetime.now(timezone.utc)`.
3. **In-Process Background Task Execution:**
   - Long-running dataset generation and full validation passes currently execute in Python thread/process contexts. At hyper-scale (> 1,000,000 assets), an asynchronous task queue (e.g. Celery / Redis / Temporal) is recommended.
4. **Physical RFID / Telemetry Scans:**
   - Scan events are modeled as discrete REST API / batch operations. Real-time MQTT / WebSocket streaming ingestion from dock door RFID readers is not yet included.
5. **Labelled-negative population:**
   - The ground-truth benchmark contains injected positives only. TN and false-positive rate are therefore unavailable; the reported 0 false positives is limited to detected records compared to the positive labels.
6. **Generator database load behavior:**
   - The generator is a full-profile loader, not an incremental reconciler. It now refuses populated targets by default; `--replace-existing` is an explicit destructive option for disposable databases only.
7. **Legacy ground-truth columns:**
   - `anomaly_records` retains `ground_truth_label`, `expected_decision`, and `is_injected` columns for backward compatibility. Detection rules do not use these fields, but physical separation into a dedicated relational table has not been migrated.
8. **Migration and schema coverage:**
   - This audit added no database migration. Historical custody retention on asset deletion, CHECK constraints, and all lifecycle-versus-projection consistency cases were not exhaustively tested.
9. **Export limits and scope:**
   - Asset exports honor existing search/type/status/overdue filters. Other export endpoints currently export full table contents with no date-range parameters. PDFs intentionally show a bounded summary for some record types while indicating the full count; CSV/JSON contain the exported rows.
10. **PDF parser verification:**
   - Generated downloads returned PDF headers, cross-reference trailers, and EOF markers. A dedicated PDF reader library is not installed in the environment, so parser-level open verification remains incomplete.
11. **Performance coverage:**
   - Database insert throughput was not benchmarked with repeated measurements. Query plans and N+1 instrumentation were not captured.
12. **Browser regression coverage:**
   - API-level downloads and the existing frontend's download handler were inspected/tested. The complete UI navigation and download flow was not exercised in a real browser session.

---

## 2. Planned Future Improvements

1. **Automated Handoff Smart Contracts:**
   - Implement verifiable custody handoffs using cryptographic signatures from carrier and receiver drivers upon dock transfer.
2. **Predictive Loss Risk Modeling:**
   - Incorporate an ML classifier trained on custody dwell times, carrier routes, and asset types to predict probability of asset loss 10 days before reaching overdue thresholds.
3. **Geo-Fencing & GPS Telemetry:**
   - Extend `Location` with geospatial polygon boundaries (`ST_GeomFromText`) and integrate automated transit geofence triggers.
4. **Automated Deposit Escrow Integration:**
   - Integrate automated ACH / credit card deposit pre-authorization holds and automated settlement via banking APIs.


## Remaining limitations after repair — 2026-10-31 (supersedes stronger earlier claims)

- Overall status PARTIAL: 4,956 of 20,000 preserved historical assets have replay/projection exceptions; 4,928 are not anomaly-labelled. Exact records and reasons are in the delivered evidence. Historical records were not changed merely to force agreement.
- Actual MySQL 8/9 server execution and PostgreSQL/Supabase end-to-end operation NOT VERIFIED; MariaDB 10.11.14 was exercised.
- Original company problem statement/instructions and full independent report/evidence JSON were absent. Local unpublished changes and the owner's actual working database were inaccessible.
- The freshly generated dataset and committed artifact set have different anomaly targets. Each must use its own independent label file; historical producer commit is unknown.
- The four-role policy does not implement tenant isolation. Session revocation, distributed login throttling, hashed reset tokens, comprehensive XSS/CSP review and production hardening remain. SMTP external delivery was not tested.
- Delivery without explicit recipient uses the legacy legal-owner default. Supply receiving_owner_id for actual custody attribution.
- ORM custody history is append-only, but a privileged raw SQL administrator can modify it. No database trigger or cryptographic event signing was added.
- Legacy ambiguous financial obligations are reported, not reassigned to conceal a deficit. A signed liability ledger is not double-entry accounting or external bank reconciliation.
- Existing migrations preserve rows and add schema/idempotency; they do not automatically repair arbitrary schema drift. MySQL-family DDL is nontransactional. Review/back up before any live upgrade.
- No direct local working-tree update or GitHub push was performed. Apply the delivered patch only after reviewing local changes.
