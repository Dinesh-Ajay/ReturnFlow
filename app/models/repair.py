from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Repair(Base):
    __tablename__ = "repairs"

    repair_id = Column(String(32), primary_key=True)  # REP-2026-000001
    asset_id = Column(String(32), ForeignKey("reusable_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    inspection_id = Column(String(32), ForeignKey("inspections.inspection_id", ondelete="SET NULL"), nullable=True, index=True)
    repair_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False, index=True)
    repair_status = Column(String(32), nullable=False, default="REQUESTED", index=True)  # REQUESTED, IN_PROGRESS, COMPLETED, FAILED, CANCELLED
    repair_start_date = Column(DateTime, nullable=False, index=True)
    repair_completion_date = Column(DateTime, nullable=True)
    repair_cost = Column(Numeric(12, 2), nullable=False, default=0.00)
    repair_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    asset = relationship("ReusableAsset", back_populates="repairs")
    inspection = relationship("Inspection", back_populates="repairs")
    repair_location = relationship("Location", foreign_keys=[repair_location_id], back_populates="repair_operations")
