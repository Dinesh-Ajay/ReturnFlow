import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.config import settings
from app.validation.integrity import IntegrityValidator
from app.validation.custody import CustodyValidator
from app.validation.lifecycle import LifecycleValidator
from app.validation.financial import FinancialValidator
from app.models.anomaly_record import AnomalyRecord

class AnomalyDetectionEngine:
    """
    Independent anomaly detection engine that identifies defects across all business entities
    and evaluates detection performance against ground-truth benchmarks.
    """

    @classmethod
    def run_detection(cls, db: Session) -> Dict[str, Any]:
        t0 = time.perf_counter()

        # Run independent detectors across all domains
        detected_anomalies: List[Dict[str, Any]] = []

        # 1. Custody simultaneous locations
        detected_anomalies.extend(CustodyValidator.detect_simultaneous_locations(db))

        # 2. Return before dispatch
        detected_anomalies.extend(LifecycleValidator.detect_return_before_dispatch(db))

        # 3. Duplicate refunds
        detected_anomalies.extend(FinancialValidator.detect_duplicate_refunds(db))

        # 4. Repairs without inspection
        detected_anomalies.extend(LifecycleValidator.detect_repairs_without_inspection(db))

        # 5. Missing custody actors
        detected_anomalies.extend(CustodyValidator.detect_missing_custody_actors(db))

        t1 = time.perf_counter()
        detection_duration = t1 - t0

        # Load ground truth independently for evaluation
        gt_path = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")
        ground_truth: List[Dict[str, Any]] = []
        if os.path.exists(gt_path):
            with open(gt_path, "r", encoding="utf-8") as f:
                ground_truth = json.load(f)

        # Evaluate detection performance against ground-truth
        eval_metrics = cls.evaluate_against_ground_truth(detected_anomalies, ground_truth)

        # Update database anomaly records
        cls.persist_detection_results(db, detected_anomalies)

        return {
            "detection_duration_seconds": round(detection_duration, 4),
            "total_detected": len(detected_anomalies),
            "detected_by_type": eval_metrics["detected_by_type"],
            "evaluation_metrics": eval_metrics,
            "detected_sample": detected_anomalies[:10]
        }

    @classmethod
    def evaluate_against_ground_truth(
        cls,
        detected: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculates Precision, Recall, False Positive Rate (FPR), False Negative Rate (FNR).
        Matching criterion: (issue_type, record_id) or (issue_type, asset_id).
        """
        gt_keys = set()
        for gt in ground_truth:
            gt_keys.add((gt["issue_type"], str(gt["record_id"])))
            if gt.get("asset_id"):
                gt_keys.add((gt["issue_type"], str(gt["asset_id"])))

        detected_by_type = {}
        for d in detected:
            itype = d["issue_type"]
            detected_by_type[itype] = detected_by_type.get(itype, 0) + 1

        tp = 0
        fp = 0
        matched_gt = set()

        for d in detected:
            key1 = (d["issue_type"], str(d["record_id"]))
            key2 = (d["issue_type"], str(d["asset_id"]))
            if key1 in gt_keys or key2 in gt_keys:
                tp += 1
                matched_gt.add(key1 if key1 in gt_keys else key2)
            else:
                fp += 1

        total_injected = len(ground_truth)
        fn = max(0, total_injected - tp)

        precision = (tp / (tp + fp) * 100.0) if (tp + fp) > 0 else 100.0
        recall = (tp / total_injected * 100.0) if total_injected > 0 else 100.0
        fnr = (fn / total_injected * 100.0) if total_injected > 0 else 0.0
        fpr = (fp / (tp + fp) * 100.0) if (tp + fp) > 0 else 0.0

        return {
            "total_injected": total_injected,
            "total_detected": len(detected),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision_pct": round(precision, 2),
            "recall_pct": round(recall, 2),
            "false_positive_rate_pct": round(fpr, 2),
            "false_negative_rate_pct": round(fnr, 2),
            "detected_by_type": detected_by_type
        }

    @classmethod
    def persist_detection_results(cls, db: Session, detected: List[Dict[str, Any]]):
        now = datetime.now(timezone.utc)
        existing_records = {r.affected_record_id: r for r in db.query(AnomalyRecord).all()}
        
        counter = 1
        for d in detected:
            rec_id_str = str(d["record_id"])
            if rec_id_str in existing_records:
                rec = existing_records[rec_id_str]
                rec.detected_decision = d["expected_decision"]
                rec.detection_status = "DETECTED"
                rec.detected_at = now
            else:
                new_id = f"DET-{counter:06d}"
                counter += 1
                new_rec = AnomalyRecord(
                    issue_id=new_id,
                    affected_asset_id=d.get("asset_id"),
                    affected_record_id=rec_id_str,
                    entity_name=d["entity_name"],
                    issue_type=d["issue_type"],
                    severity=d["severity"],
                    description=d["description"],
                    ground_truth_label=None,
                    expected_decision=d["expected_decision"],
                    detected_decision=d["expected_decision"],
                    detection_status="DETECTED",
                    is_injected=False,
                    detected_at=now
                )
                db.add(new_rec)
                existing_records[rec_id_str] = new_rec
        db.commit()
