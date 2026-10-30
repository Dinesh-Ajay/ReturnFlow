from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ReturnAuthorization(Base):
    __tablename__ = "return_authorizations"

    rma_id = Column(String(32), primary_key=True)  # RMA-2026-000001
    requesting_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="RESTRICT"), nullable=False, index=True)
    receiving_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="RESTRICT"), nullable=False, index=True)
    return_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False, index=True)
    requested_date = Column(DateTime, nullable=False, index=True)
    approved_date = Column(DateTime, nullable=True)
    expected_return_date = Column(DateTime, nullable=False)
    actual_return_date = Column(DateTime, nullable=True)
    rma_status = Column(String(32), nullable=False, default="REQUESTED", index=True)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    requesting_owner = relationship("Owner", foreign_keys=[requesting_owner_id])
    receiving_owner = relationship("Owner", foreign_keys=[receiving_owner_id])
    return_location = relationship("Location", foreign_keys=[return_location_id])

    rma_assets = relationship("ReturnAuthorizationAsset", back_populates="rma", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="rma")
    deposit_transactions = relationship("DepositLedger", back_populates="rma")
