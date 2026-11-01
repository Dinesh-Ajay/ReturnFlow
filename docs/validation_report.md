# Validation repair update — 2026-10-31

This section supersedes historical all-clear claims below. Verification used dedicated disposable MariaDB databases, never the owner's working database.

- Complete final suite: **116 passed**, one third-party Starlette/httpx deprecation warning.
- Preserved baseline: 20,000 assets; 10,000 shipments; 100,030 custody events; 12,400 RMAs and inspections; 1,348 repairs; 34,148 ledger rows; 50 anomaly labels.
- Structural integrity: PASS; zero PK/FK/orphan/declared-unique violations in the baseline audit.
- Independent detector: 50 TP, 0 FP, 0 FN against the matching committed positive-label set. No labelled-negative population; TN/FPR unavailable.
- Finance: portfolio arithmetic balanced, but individual obligations invalid; 10 duplicate refunds, 10 over-refunds, 10 negative asset liabilities. `is_reconciled=false` is the correct seed result, not a failed arithmetic calculation.
- Replay: 15,044 fully consistent assets; 4,956 exceptions, including 4,928 unlabelled assets. Historical replay acceptance remains PARTIAL. Exact IDs/reasons are in `evidence/event_replay_exceptions.json` in the repair package.
- Standing: full list and analytics overdue counts agree at 1,098 for reference date 2026-10-22.
- Clean install: blank database -> all migrations -> full constrained generation load succeeded. All model tables/indexes/FKs/unique constraints were found by the full audit.
- Original company compliance NOT VERIFIED because original assessment files were absent.

## Historical report (not evidence for the repaired snapshot)

# ReturnFlow Validation Report

Read-only database audit run: 2026-10-30 (local MySQL database, server 9.1.0).
Counts below were queried from the database; they are not dashboard values.

## Record counts

| Table | Actual rows | Expected minimum |
| --- | ---: | ---: |
| `asset_types` | 8 | Inspect |
| `owners` | 40 | Inspect |
| `locations` | 30 | Inspect |
| `reusable_assets` | 20,009 | 20,000 |
| `shipments` | 10,000 | 10,000 |
| `shipment_assets` | 20,000 | Inspect |
| `custody_events` | 100,039 | 100,000 |
| `return_authorizations` | 12,400 | Inspect |
| `return_authorization_assets` | 12,400 | Inspect |
| `inspections` | 12,400 | Inspect |
| `repairs` | 1,348 | Inspect |
| `deposit_ledger` | 34,148 | Inspect |
| `anomaly_records` | 50 | Inspect |

The database also has 9 users/OTP rows combined (1 user, 9 OTP rows). The mapped-table integrity audit checked 222,882 rows total.

## Integrity and lifecycle checks

`python -m app.validation.counts` checks actual table counts against the three required minimums. `IntegrityValidator.validate_all` inspects mapped primary keys, required/optional foreign-key references, orphan rows, and declared unique constraints.

Observed result: **0 primary-key violations, 0 foreign-key violations, 0 orphan records, and 0 duplicate identifiers**. Declared constraints and ID pattern checks passed. Lifecycle transition unit checks pass in the test suite; the audit does not prove every historical state projection is consistent for all records.

## Anomaly evaluation

The five rule detectors evaluated the separate `data/ground_truth/ground_truth.json` labels by `(scenario type, record ID)`, with duplicate findings collapsed by that key.

| Scenario | Labelled injected | Detected |
| --- | ---: | ---: |
| Simultaneous custody | 10 | 10 |
| Return before dispatch | 10 | 10 |
| Duplicate deposit refund | 10 | 10 |
| Repair without inspection | 10 | 10 |
| Missing custody actor | 10 | 10 |

Observed confusion matrix: **TP 50, FP 0, FN 0**. Precision, recall, and F1 are each 1.0 (100%). TN and false-positive rate are unavailable because this ground-truth file contains no labelled negative population. These figures describe this synthetic labelled sample only.

Ground-truth labels are read after the operational detectors finish and are used for evaluation only. The operational anomaly table currently has ground-truth-related columns for legacy compatibility; the detection rules do not filter on or use those values.

## Financial reconciliation

Ledger convention: `DEPOSIT_CHARGE`, `DAMAGE_CHARGE`, and `LOSS_CHARGE` are positive amounts; `DEPOSIT_REFUND` is negative. Outstanding liability is collected deposits minus refunds, damage deductions, and loss deductions, plus signed adjustments. `REPAIR_CHARGE` is tracked separately and does not reduce deposit liability under the existing service convention.

| Measure | Actual |
| --- | ---: |
| Deposit charges | $3,909,680.00 |
| Refunds | $2,333,839.25 |
| Damage deductions | $90,966.75 |
| Loss deductions | $77,890.00 |
| Adjustments | $0.00 |
| Net outstanding liability | $1,406,984.00 |
| Unreconciled sign/reference transactions | 0 |
| Duplicate-refund findings | 10 |

The duplicate refunds are deliberately injected anomalies and are counted separately from arithmetic reconciliation. No ledger rows were changed by this audit.

## Automated tests

The suite was run against the dedicated database `returnflow_audit_test_20261030`, with its own matching generated ground-truth file: **58 passed, 0 failed, 0 skipped**. The suite is guarded to refuse a database name that is not clearly a test database. One upstream Starlette/httpx deprecation warning was emitted.

Command: `python -m pytest -q` after setting both `DATABASE_URL` and `TEST_DATABASE_URL` to a dedicated `*_test` database. A full-profile test dataset must be present first.

## Current limits

- Database writes/insertion timing is reported separately because the full-profile generator is not incremental; it now refuses populated targets unless replacement is explicitly requested.
- This audit did not run a destructive full-profile load against the working development database.
- The suite verifies covered service and API behavior; it does not exercise a browser GUI for every navigation path.
