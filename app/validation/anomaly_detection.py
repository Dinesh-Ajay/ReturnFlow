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
            "total_detected": eval_metrics["total_detected"],
            "detected_by_type": eval_metrics["detected_by_type"],
            "evaluation_metrics": eval_metrics,
            "detected_sample": detected_anomalies[:10]
        }

    @classmethod
    def evaluate_detection_metrics(cls, db: Session) -> Dict[str, Any]:
        """Read-only detector/evaluation entry point used by report downloads."""
        detected = []
        detected.extend(CustodyValidator.detect_simultaneous_locations(db))
        detected.extend(LifecycleValidator.detect_return_before_dispatch(db))
        detected.extend(FinancialValidator.detect_duplicate_refunds(db))
        detected.extend(LifecycleValidator.detect_repairs_without_inspection(db))
        detected.extend(CustodyValidator.detect_missing_custody_actors(db))
        gt_path = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")
        if not os.path.isfile(gt_path):
            raise FileNotFoundError(f"Ground-truth evaluation data not found: {gt_path}")
        with open(gt_path, "r", encoding="utf-8") as source:
            ground_truth = json.load(source)
        return cls.evaluate_against_ground_truth(detected, ground_truth)

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
        negative_keys = set()
        for gt in ground_truth:
            key = (gt.get("issue_type"), str(gt.get("record_id")))
            expected = str(gt.get("expected_detection", gt.get("expected_decision", ""))).upper()
            if expected in {"NORMAL", "NEGATIVE", "NO_ANOMALY", "FALSE"}:
                negative_keys.add(key)
            else:
                gt_keys.add(key)

        detected_by_type = {}
        injected_by_type = {}
        for gt in ground_truth:
            if str(gt.get("expected_detection", gt.get("expected_decision", ""))).upper() not in {"NORMAL", "NEGATIVE", "NO_ANOMALY", "FALSE"}:
                kind = gt.get("issue_type", "UNKNOWN")
                injected_by_type[kind] = injected_by_type.get(kind, 0) + 1
        # A single issue can be returned through multiple joins. Count a
        # record/type pair once so it cannot inflate precision or recall.
        unique_detected = {(d["issue_type"], str(d["record_id"])): d for d in detected}
        for d in unique_detected.values():
            itype = d["issue_type"]
            detected_by_type[itype] = detected_by_type.get(itype, 0) + 1

        tp = 0
        fp = 0
        matched_gt = set()

        for key, d in unique_detected.items():
            if key in gt_keys:
                tp += 1
                matched_gt.add(key)
            else:
                fp += 1

        total_injected = len(gt_keys)
        fn = len(gt_keys - matched_gt)
        tn = len(negative_keys - set(unique_detected)) if negative_keys else None

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        fpr = (fp / (fp + tn)) if tn is not None and (fp + tn) > 0 else None

        return {
            "total_injected": total_injected,
            "total_detected": len(unique_detected),
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "f1_score": round(f1, 6),
            "false_positive_rate": round(fpr, 6) if fpr is not None else None,
            "precision_pct": round(precision * 100, 2),
            "recall_pct": round(recall * 100, 2),
            "f1_score_pct": round(f1 * 100, 2),
            "false_positive_rate_pct": round(fpr * 100, 2) if fpr is not None else None,
            "evaluation_note": "No labelled negative population; TN and false positive rate are unavailable." if tn is None else None,
            "detected_by_type": detected_by_type,
            "injected_by_type": injected_by_type,
        }

    @classmethod
    def persist_detection_results(cls, db: Session, detected: List[Dict[str, Any]]):
        now = datetime.now(timezone.utc)
        # Select only operational identifiers. Do not hydrate ORM instances,
        # because the legacy table also contains ground-truth label columns.
        operational_rows = db.query(
            AnomalyRecord.issue_id, AnomalyRecord.affected_record_id
        ).all()
        existing_records = {
            str(record_id): issue_id for issue_id, record_id in operational_rows
            if record_id is not None
        }
        counter = max((int(issue_id[4:]) for issue_id, _ in operational_rows
                       if issue_id.startswith("DET-") and issue_id[4:].isdigit()), default=0) + 1
        
        for d in detected:
            rec_id_str = str(d["record_id"])
            if rec_id_str in existing_records:
                db.query(AnomalyRecord).filter(
                    AnomalyRecord.issue_id == existing_records[rec_id_str]
                ).update({
                    AnomalyRecord.detected_decision: d["expected_decision"],
                    AnomalyRecord.detection_status: "DETECTED",
                    AnomalyRecord.detected_at: now,
                }, synchronize_session=False)
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
                existing_records[rec_id_str] = new_id
        db.commit()
