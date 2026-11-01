# Requirement traceability — 2026-10-31

**Original company requirement coverage: NOT VERIFIED.** The original problem statement and submission instructions were not supplied. It is impossible to enumerate their requirements honestly. Rows below trace the user's explicit repair/acceptance specification, not invented company requirements. No earlier AI recommendation has been treated as authoritative company scope.

| ID | Requirement | Implementation | Tests | Evidence / outcome | Status |
|---|---|---|---|---|---|
| SRC-01 | Original company problem statement and instructions | Unavailable | None | No authoritative originals supplied | NOT VERIFIED |
| SRC-02 | Full independent audit and evidence JSON | Only user narrative available | Baseline and acceptance probes | Findings independently reproduced where possible | PARTIAL |
| GIT-01 | Inspect actual owner branch/uncommitted partial work | Remote clone and uploaded critical samples | Git inspection/sample comparison | Remote clean; owner local state inaccessible | PARTIAL |
| SAFE-01 | Checkpoint/preserve existing work; no commit/push/main DB writes | External checkpoint; isolated DBs | Git/data preservation review | No tracked data changed; no staging/commit/push | PASS |
| ID-01 | Persistent IDs for shipment/RMA/inspection/repair on populated DB | app/utils/id_generator.py; services | test_persistent_id_generation; sequential acceptance | Upsert + lock + high-water recovery; focused/full tests | PASS |
| ID-02 | Cold concurrent allocation, formats and rollback | Same | test_cold_concurrent_sequences; format/rollback tests | Eight concurrent allocations for each entity pass | PASS |
| ID-03 | Validate on the actual MySQL server | MySQL dialect exercised through MariaDB | Not an actual MySQL server run | MariaDB 10.11.14 only | NOT VERIFIED |
| LIFE-01 | Validate transitions and append atomic movement/domain events | lifecycle_service and live services; custody API | full lifecycle/rollback/invalid dispatch tests | Live normal lifecycle replay matches each step | PASS |
| LIFE-02 | Correct recipient/location/null handling | shipment delivery API; record_transition | loss/recovery; explicit recipient; origin tests | New events record explicit recipient; legacy owner default documented | PASS |
| REPLAY-01 | Deterministic replay including inspection/repair/history gaps | projection_service.py | test_full_live_lifecycle; equal timestamp test | Normal newly recorded lifecycle passes | PASS |
| REPLAY-02 | All valid preserved non-anomalous assets reconstruct | bulk_replay; acceptance_audit | Full 20,000-asset audit | 4,956 exceptions, 4,928 unlabelled; exact records retained | PARTIAL |
| AGE-01 | One dispatch-cycle age rule for list/detail/API/overdue/analytics | LifecycleService; AssetService; analytics | age/timezone/multiple cycle/API/pagination tests | List and analytics overdue totals both 1,098 | PASS |
| REFUND-01 | Detection independent of reference markers/ground truth | FinancialValidator.audit_obligations | rename test; legitimate partial/multiple-cycle tests | 10 preserved-seed duplicates survive reference renaming | PASS |
| REFUND-02 | Idempotency and original obligation relationships | DepositService; related_ledger_id; unique migration | idempotency, cycle limit, unique-key tests | Retries return same row; excess invalid requests rejected | PASS |
| FIN-01 | Portfolio arithmetic cannot hide individual deficits | FinancialValidator; reconciliation API | positive portfolio/negative asset acceptance | Arithmetic true, individuals false; reconciliation false | PASS |
| FIN-02 | Validate signs/deductions/references/cycles/exceptions | Same | deduction, cross-asset, multi-cycle tests | Separate structured findings returned | PASS |
| UI-01 | Filter changes reset pagination; all categories dynamic | app/static/index.html | Headless browser acceptance | Both filter reset checks and all eight categories pass | PASS |
| UI-02 | Visible status aliases and UNDER_REPAIR value | AssetService; HTML | alias tests and browser search | At Location/In Transit/In Repair handled | PASS |
| UI-03 | Overdue applied before count/page slicing | AssetService | page-boundary and empty-result tests | Filtered counts and page boundaries pass | PASS |
| DB-01 | Reliable blank installation | Alembic 0026 + 0027 | Blank migrations and full load; schema inspection | 16 tables plus Alembic version, no missing indexes/FKs/unique constraints | PASS |
| AUTH-01 | Protect business APIs; invalid/expired tokens and roles | dependencies; main; auth; portal fetch | unauth/invalid/expired/forged-role tests; browser | Fail-closed route policy passes | PASS |
| AUTH-02 | Review password handling/reset/configuration | AuthService/EmailService/config/Streamlit | password recovery, expired reset, fallback-removal tests | Known backdoor/default OTP disclosure removed; operational hardening remains | PARTIAL |
| DATA-01 | Preserve baseline counts/seed/original data | Generator; unchanged data files | counts, Git hashes, final tests | All baseline counts and seed retained | PASS |
| DATA-02 | Current generator reproducibility and source manifest | reproducibility.py; manifest.py | Two full in-memory passes | Counts and logical checksums match | PASS |
| DATA-03 | Historical files exactly equal current fresh generation | Artifact version comparison | Byte/checksum comparison | Different anomaly targets; preserved, version-paired, no false identity claim | PARTIAL |
| TEST-01 | Existing plus new regression suites pass | tests/ | python -m pytest -v on both dataset versions | 116 passed for each paired database/ground-truth set | PASS |
| DOC-01 | Correct docs/progress/report/traceability | README/docs/prompts/reports | Evidence-driven review | Reports identify unverified originals and remaining gaps | PASS |
| DEPLOY-01 | External Better Auth/Supabase/cloud integrations | Configuration/planning only | No deployed integration evidence | Not promoted to company requirement | NOT VERIFIED |
