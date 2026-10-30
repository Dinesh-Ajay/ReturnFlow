from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Shipment(Base):
    __tablename__ = "shipments"

    shipment_id = Column(String(32), primary_key=True)  # SHP-2026-000001
    origin_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False, index=True)
    destination_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="RESTRICT"), nullable=False, index=True)
    carrier_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="RESTRICT"), nullable=False, index=True)
    dispatch_date = Column(DateTime, nullable=False, index=True)
    expected_delivery_date = Column(DateTime, nullable=False)
    actual_delivery_date = Column(DateTime, nullable=True)
    shipment_status = Column(String(32), nullable=False, default="PLANNED", index=True)
    tracking_reference = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    origin_location = relationship("Location", foreign_keys=[origin_location_id], back_populates="origin_shipments")
    destination_location = relationship("Location", foreign_keys=[destination_location_id], back_populates="destination_shipments")
    carrier = relationship("Owner", foreign_keys=[carrier_owner_id], back_populates="carrier_shipments")

    shipment_assets = relationship("ShipmentAsset", back_populates="shipment", cascade="all, delete-orphan")
    custody_events = relationship("CustodyEvent", back_populates="shipment")
    deposit_transactions = relationship("DepositLedger", back_populates="shipment")
