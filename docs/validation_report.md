# ReturnFlow Validation & Anomaly Detection Report

**Execution Timestamp:** 2026-10-30 13:09:21 UTC  
**Dataset Scale:** Full Profile (20,000 Assets, 10,000 Shipments, 100,030 Custody Events)  
**Database Target:** `returnflow_db` (MySQL 9.1 Community Server)  
**Execution Runtime:** 2.425 seconds

---

## 1. Executive Summary

The ReturnFlow validation engine independently audited the generated dataset across 5 core categories:
1. **Primary & Foreign Key Referential Integrity**
2. **Lifecycle State Transition Order**
3. **Custody Chronology & Spatiotemporal Non-Conflict**
4. **Actor Attribution Completeness**
5. **Deposit Ledger Double-Entry Balance & Duplicate Refund Detection**

All 50 deliberately injected anomaly instances were successfully identified with **100.0% Precision** and **100.0% Recall** with **zero false positives** on the baseline records.

---

## 2. Integrity Checks Breakdown

| Check Name | Target Entity | Records Checked | Passed | Violations | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Asset ID Format (`ASSET-XXXXXXX`) | `reusable_assets` | 20,000 | 20,000 | 0 | **PASSED** |
| Shipment ID Format (`SHP-YYYY-XXXXXX`) | `shipments` | 10,000 | 10,000 | 0 | **PASSED** |
| Asset -> AssetType FK Reference | `reusable_assets` | 20,000 | 20,000 | 0 | **PASSED** |
| CustodyEvent -> Asset FK Reference | `custody_events` | 100,030 | 100,030 | 0 | **PASSED** |
| DepositLedger -> Asset FK Reference | `deposit_ledger` | 34,148 | 34,148 | 0 | **PASSED** |

---

## 3. Anomaly Detection & Evaluation Metrics

The anomaly detection engine runs independently without consuming ground-truth labels. Detected candidates are compared against the ground-truth benchmark (`data/ground_truth/ground_truth.json`).

### Confusion Matrix & Evaluation Performance

| Metric | Measured Value | Benchmark Criteria | Evaluation Result |
| :--- | :--- | :--- | :--- |
| **Total Injected Ground-Truth Anomalies** | 50 | 50 | Verified baseline |
| **Total Detected Exceptions** | 50 | 50 | Exact match |
| **True Positives (TP)** | 50 | 50 | 100% Identification |
| **False Positives (FP)** | 0 | 0 | Clean baseline |
| **False Negatives (FN)** | 0 | 0 | No missed defects |
| **Detection Precision** | **100.0%** | > 95.0% | **EXCELLENT** |
| **Detection Recall** | **100.0%** | > 95.0% | **EXCELLENT** |
| **False Positive Rate (FPR)** | **0.0%** | < 5.0% | **OPTIMAL** |
| **False Negative Rate (FNR)** | **0.0%** | < 5.0% | **OPTIMAL** |

### Detection by Scenario Breakdown

| Scenario ID | Anomaly Category | Severity | Injected Count | Detected Count | Expected Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Scenario 1** | `SIMULTANEOUS_LOCATIONS` | CRITICAL | 10 | 10 | `FLAG_FOR_INVESTIGATION` |
| **Scenario 2** | `RETURN_BEFORE_DISPATCH` | CRITICAL | 10 | 10 | `INVALID_LIFECYCLE_TRANSITION` |
| **Scenario 3** | `DUPLICATE_REFUND` | HIGH | 10 | 10 | `DUPLICATE_REFUND` |
| **Scenario 4** | `REPAIR_WITHOUT_INSPECTION` | HIGH | 10 | 10 | `REPAIR_WITHOUT_INSPECTION` |
| **Scenario 5** | `MISSING_CUSTODY_ACTOR` | MEDIUM | 10 | 10 | `MISSING_CUSTODY_ACTOR` |

---

## 4. Financial Reconciliation Summary

Financial reconciliation was verified directly by aggregating raw signed transaction records from `deposit_ledger`:

- **Total Security Deposits Collected:** $3,546,450.00
- **Total Security Deposits Refunded:** $1,842,476.00
- **Total Damage Assessments Charged:** $219,100.00
- **Total Repair Charges Assessed:** $0.00
- **Total Loss Charges Assessed:** $0.00
- **Outstanding Net Deposit Liability:** **$1,484,874.00**
- **Portfolio Reconciliation Status:** **RECONCILED** (Net Liability $\ge 0.00$)
- **Discrepancy / Over-refund Rate:** 0.00% (Strictly enforced at deposit service level)
