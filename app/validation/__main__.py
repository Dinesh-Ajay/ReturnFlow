import os
import json
import time
from app.database.session import SessionLocal
from app.utils.logging_config import setup_logging, logger
from app.config import settings
from app.validation.integrity import IntegrityValidator
from app.validation.financial import FinancialValidator
from app.validation.anomaly_detection import AnomalyDetectionEngine

def run_all_validation():
    setup_logging()
    logger.info("=== Starting ReturnFlow Comprehensive Data Validation & Anomaly Detection ===")

    t0 = time.perf_counter()
    db = SessionLocal()

    try:
        # 1. Structural & Referential Integrity Validation
        logger.info("Running primary/foreign key integrity checks...")
        integrity_results = IntegrityValidator.validate_all(db)

        # 2. Financial Ledger Reconciliation
        logger.info("Running financial ledger reconciliation...")
        financial_results = FinancialValidator.reconcile_ledger_totals(db)

        # 3. Anomaly Detection & Ground-Truth Evaluation
        logger.info("Executing independent anomaly detection engine...")
        anomaly_results = AnomalyDetectionEngine.run_detection(db)

        t1 = time.perf_counter()
        total_duration = t1 - t0

        validation_summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "total_duration_seconds": round(total_duration, 4),
            "integrity_checks": integrity_results,
            "financial_reconciliation": financial_results,
            "anomaly_detection": anomaly_results,
            "overall_status": "PASSED" if integrity_results["passed"] and financial_results["is_reconciled"] else "DISCREPANCY_DETECTED"
        }

        # Export to data/exports/validation_summary.json
        os.makedirs(settings.EXPORTS_DIR, exist_ok=True)
        out_path = os.path.join(settings.EXPORTS_DIR, "validation_summary.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(validation_summary, f, indent=2)

        eval_m = anomaly_results["evaluation_metrics"]
        logger.info("=== Validation & Evaluation Summary ===")
        logger.info(f"Integrity Checks Passed:         {integrity_results['passed']}")
        logger.info(f"Financial Ledger Reconciled:     {financial_results['is_reconciled']} (Net Liability: ${financial_results['net_liability']:,.2f})")
        logger.info(f"Injected Ground-Truth Anomalies: {eval_m['total_injected']}")
        logger.info(f"Detected Anomalies:              {eval_m['total_detected']}")
        logger.info(f"True Positives:                  {eval_m['true_positives']}")
        logger.info(f"False Positives:                 {eval_m['false_positives']}")
        logger.info(f"False Negatives:                 {eval_m['false_negatives']}")
        logger.info(f"Detection Precision:             {eval_m['precision_pct']}%")
        logger.info(f"Detection Recall:                {eval_m['recall_pct']}%")
        logger.info(f"Total Validation Time:           {total_duration:.3f}s")
        logger.info(f"Report exported to: {out_path}")

        return validation_summary

    finally:
        db.close()

if __name__ == "__main__":
    run_all_validation()
