from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Inspection(Base):
    __tablename__ = "inspections"

    inspection_id = Column(String(32), primary_key=True)  # INSP-2026-000001
    asset_id = Column(String(32), ForeignKey("reusable_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    rma_id = Column(String(32), ForeignKey("return_authorizations.rma_id", ondelete="SET NULL"), nullable=True, index=True)
    inspector_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="RESTRICT"), nullable=False, index=True)
    inspection_date = Column(DateTime, nullable=False, index=True)
    condition_status = Column(String(32), nullable=False, index=True)  # GOOD, DAMAGED, CRITICAL, UNUSABLE
    damage_severity = Column(String(32), nullable=True)  # NONE, MINOR, MODERATE, SEVERE
    requires_repair = Column(Boolean, nullable=False, default=False)
    inspection_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    asset = relationship("ReusableAsset", back_populates="inspections")
    rma = relationship("ReturnAuthorization", back_populates="inspections")
    inspector = relationship("Owner", foreign_keys=[inspector_owner_id])
    repairs = relationship("Repair", back_populates="inspection")
