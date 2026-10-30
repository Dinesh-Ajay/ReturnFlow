import os
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.config import settings
from app.validation.anomaly_detection import AnomalyDetectionEngine
from app.validation.__main__ import run_all_validation
from app.models.anomaly_record import AnomalyRecord
from app.schemas.entities import AnomalyRecordResponse

router = APIRouter(tags=["Validation & Anomalies"])

@router.post("/api/validation/run")
def trigger_validation(db: Session = Depends(get_db)):
    summary = run_all_validation()
    return {
        "status": "COMPLETED",
        "timestamp": summary["timestamp"],
        "total_duration_seconds": summary["total_duration_seconds"],
        "evaluation_metrics": summary["anomaly_detection"]["evaluation_metrics"]
    }

@router.get("/api/validation/results")
def get_validation_results():
    summary_path = os.path.join(settings.EXPORTS_DIR, "validation_summary.json")
    if not os.path.exists(summary_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Validation summary not yet generated. Trigger POST /api/validation/run first."
        )
    with open(summary_path, "r", encoding="utf-8") as f:
        return json.load(f)

@router.get("/api/anomalies", response_model=List[AnomalyRecordResponse])
def list_anomalies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    severity: Optional[str] = Query(None),
    issue_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(AnomalyRecord)
    if severity and severity != "All":
        query = query.filter(AnomalyRecord.severity == severity)
    if issue_type and issue_type != "All":
        query = query.filter(AnomalyRecord.issue_type == issue_type)
    if status and status != "All":
        query = query.filter(AnomalyRecord.detection_status == status)

    offset = (page - 1) * page_size
    return query.order_by(AnomalyRecord.created_at.desc()).offset(offset).limit(page_size).all()

@router.get("/api/anomalies/{issue_id}", response_model=AnomalyRecordResponse)
def get_anomaly_detail(issue_id: str, db: Session = Depends(get_db)):
    record = db.query(AnomalyRecord).filter(AnomalyRecord.issue_id == issue_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Anomaly issue {issue_id} not found.")
    return record
