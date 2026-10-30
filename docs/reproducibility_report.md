# ReturnFlow Reproducibility & Determinism Report

This report documents the verification of deterministic data generation in **ReturnFlow** using the fixed random seed `20261022`.

---

## 1. Reproducibility Configuration

- **Fixed Random Seed:** `20261022`
- **Reference Evaluation Date:** `2026-10-22`
- **ID Generator Strategy:** Deterministic state machine counters with zero-padded formatting.
- **Python Pseudo-Random Number Generator:** `random.Random(seed)` initialized once per generation cycle and passed explicitly to all generators.

---

## 2. Multi-Run Comparison Verification

The generation pipeline was executed in two independent passes with identical seed configuration. The resulting datasets were compared across row counts, primary key sequences, and ground-truth anomaly labels.

### Row Count Comparison

| Entity Table | Run 1 Record Count | Run 2 Record Count | Match Status |
| :--- | :--- | :--- | :--- |
| `asset_types` | 8 | 8 | **IDENTICAL** |
| `owners` | 40 | 40 | **IDENTICAL** |
| `locations` | 30 | 30 | **IDENTICAL** |
| `reusable_assets` | 20,000 | 20,000 | **IDENTICAL** |
| `shipments` | 10,000 | 10,000 | **IDENTICAL** |
| `shipment_assets` | 20,000 | 20,000 | **IDENTICAL** |
| `custody_events` | 100,030 | 100,030 | **IDENTICAL** |
| `return_authorizations` | 12,400 | 12,400 | **IDENTICAL** |
| `return_authorization_assets`| 12,400 | 12,400 | **IDENTICAL** |
| `inspections` | 12,400 | 12,400 | **IDENTICAL** |
| `repairs` | 1,348 | 1,348 | **IDENTICAL** |
| `deposit_ledger` | 34,148 | 34,148 | **IDENTICAL** |
| `anomaly_records` | 50 | 50 | **IDENTICAL** |

---

## 3. Structural & Primary Key Invariance

1. **Asset IDs:**
   - Both runs produced the exact sequence `ASSET-0000001` through `ASSET-0020000`.
   - Serial numbers mapped identically: `ASSET-0000001` -> `SN-PALLET-0000001`, `ASSET-0000002` -> `SN-CONTAINER-0000002`, etc.
2. **Shipment IDs:**
   - Exact sequence `SHP-2026-000001` through `SHP-2026-010000`.
3. **Custody Event IDs:**
   - Deterministic per-asset sequence: `CUST-ASSET-0000001-000001`, `CUST-ASSET-0000001-000002`, etc.
4. **Ground-Truth Labels:**
   - All 50 injected anomaly instances mapped to identical `issue_id` values (`ANOM-000001` through `ANOM-000050`), affecting identical target records and asset IDs.

---

## 4. Automated Reproducibility Test

Automated verification is incorporated into the pytest suite in `tests/test_reproducibility.py`.
Execution command:
```bash
python -m pytest tests/test_reproducibility.py -v
```
Result: **PASSED (100% Assertion Match)**.
