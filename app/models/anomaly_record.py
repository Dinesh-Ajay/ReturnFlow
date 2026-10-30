from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Index
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class AnomalyRecord(Base):
    __tablename__ = "anomaly_records"

    issue_id = Column(String(64), primary_key=True)  # ANOM-000001
    affected_asset_id = Column(String(32), nullable=True, index=True)
    affected_record_id = Column(String(64), nullable=False, index=True)
    entity_name = Column(String(64), nullable=False, index=True)
    issue_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False, index=True)  # CRITICAL, HIGH, MEDIUM, LOW
    description = Column(Text, nullable=False)
    ground_truth_label = Column(String(64), nullable=True, index=True)
    expected_decision = Column(String(64), nullable=False)
    detected_decision = Column(String(64), nullable=True)
    detection_status = Column(String(32), nullable=False, default="OPEN", index=True)  # OPEN, RESOLVED, SUPPRESSED
    is_injected = Column(Boolean, nullable=False, default=False)
    detected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
