from app.validation.custody import CustodyValidator
from app.validation.lifecycle import LifecycleValidator
from app.validation.financial import FinancialValidator
from app.validation.anomaly_detection import AnomalyDetectionEngine

def test_anomaly_scenario_1_simultaneous_locations(db_session):
    anomalies = CustodyValidator.detect_simultaneous_locations(db_session)
    assert len(anomalies) > 0
    first = anomalies[0]
    assert first["issue_type"] == "SIMULTANEOUS_LOCATIONS"
    assert first["expected_decision"] == "FLAG_FOR_INVESTIGATION"
    assert first["severity"] == "CRITICAL"

def test_anomaly_scenario_2_return_before_dispatch(db_session):
    anomalies = LifecycleValidator.detect_return_before_dispatch(db_session)
    assert len(anomalies) > 0
    first = anomalies[0]
    assert first["issue_type"] == "RETURN_BEFORE_DISPATCH"
    assert first["expected_decision"] == "INVALID_LIFECYCLE_TRANSITION"
    assert first["severity"] == "CRITICAL"

def test_anomaly_scenario_3_duplicate_refund(db_session):
    anomalies = FinancialValidator.detect_duplicate_refunds(db_session)
    assert len(anomalies) > 0
    first = anomalies[0]
    assert first["issue_type"] == "DUPLICATE_REFUND"
    assert first["expected_decision"] == "DUPLICATE_REFUND"
    assert first["severity"] == "HIGH"

def test_anomaly_scenario_4_repair_without_inspection(db_session):
    anomalies = LifecycleValidator.detect_repairs_without_inspection(db_session)
    assert len(anomalies) > 0
    first = anomalies[0]
    assert first["issue_type"] == "REPAIR_WITHOUT_INSPECTION"
    assert first["expected_decision"] == "REPAIR_WITHOUT_INSPECTION"
    assert first["severity"] == "HIGH"

def test_anomaly_scenario_5_missing_custody_actor(db_session):
    anomalies = CustodyValidator.detect_missing_custody_actors(db_session)
    assert len(anomalies) > 0
    first = anomalies[0]
    assert first["issue_type"] == "MISSING_CUSTODY_ACTOR"
    assert first["expected_decision"] == "MISSING_CUSTODY_ACTOR"
    assert first["severity"] == "MEDIUM"

def test_ground_truth_independent_evaluation(db_session):
    results = AnomalyDetectionEngine.run_detection(db_session)
    metrics = results["evaluation_metrics"]
    assert metrics["precision_pct"] == 100.0
    assert metrics["recall_pct"] == 100.0
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0

def test_evaluation_calculates_confusion_matrix_with_labelled_negatives():
    truth = [
        {"issue_type": "A", "record_id": "1", "expected_decision": "ANOMALY"},
        {"issue_type": "A", "record_id": "2", "expected_decision": "ANOMALY"},
        {"issue_type": "A", "record_id": "3", "expected_decision": "NORMAL"},
        {"issue_type": "A", "record_id": "4", "expected_decision": "NORMAL"},
    ]
    detected = [
        {"issue_type": "A", "record_id": "1", "asset_id": None},
        {"issue_type": "A", "record_id": "3", "asset_id": None},
        {"issue_type": "A", "record_id": "3", "asset_id": None},  # duplicate result is counted once
    ]
    metrics = AnomalyDetectionEngine.evaluate_against_ground_truth(detected, truth)
    assert (metrics["true_positives"], metrics["false_positives"], metrics["false_negatives"], metrics["true_negatives"]) == (1, 1, 1, 1)
    assert metrics["precision"] == metrics["recall"] == metrics["f1_score"] == 0.5
    assert metrics["false_positive_rate"] == 0.5

def test_evaluation_zero_denominators_are_safe():
    metrics = AnomalyDetectionEngine.evaluate_against_ground_truth([], [])
    assert metrics["precision"] == metrics["recall"] == metrics["f1_score"] == 0.0
    assert metrics["true_negatives"] is None
    assert metrics["false_positive_rate"] is None
