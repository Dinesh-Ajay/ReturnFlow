from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Date, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ReusableAsset(Base):
    __tablename__ = "reusable_assets"

    asset_id = Column(String(32), primary_key=True)  # ASSET-0000001
    asset_type_id = Column(Integer, ForeignKey("asset_types.asset_type_id", ondelete="RESTRICT"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="RESTRICT"), nullable=False, index=True)
    serial_number = Column(String(64), unique=True, nullable=False, index=True)
    asset_status = Column(String(32), nullable=False, default="AVAILABLE", index=True)
    manufacture_date = Column(Date, nullable=False)
    purchase_date = Column(Date, nullable=False)
    current_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="SET NULL"), nullable=True, index=True)
    current_custodian_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="SET NULL"), nullable=True, index=True)
    acquisition_cost = Column(Numeric(12, 2), nullable=False, default=0.00)
    deposit_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    last_event_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    # Relationships
    asset_type = relationship("AssetType", back_populates="assets")
    owner = relationship("Owner", foreign_keys=[owner_id], back_populates="owned_assets")
    current_location = relationship("Location", foreign_keys=[current_location_id], back_populates="assets_here")
    current_custodian = relationship("Owner", foreign_keys=[current_custodian_owner_id], back_populates="custodian_assets")

    custody_events = relationship("CustodyEvent", back_populates="asset", cascade="all, delete-orphan", order_by="CustodyEvent.event_timestamp")
    shipment_assets = relationship("ShipmentAsset", back_populates="asset", cascade="all, delete-orphan")
    rma_assets = relationship("ReturnAuthorizationAsset", back_populates="asset", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="asset", cascade="all, delete-orphan", order_by="Inspection.inspection_date")
    repairs = relationship("Repair", back_populates="asset", cascade="all, delete-orphan", order_by="Repair.repair_start_date")
    deposit_transactions = relationship("DepositLedger", back_populates="asset", cascade="all, delete-orphan", order_by="DepositLedger.transaction_date")
