from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ShipmentAsset(Base):
    __tablename__ = "shipment_assets"

    shipment_asset_id = Column(Integer, primary_key=True, autoincrement=True)
    shipment_id = Column(String(32), ForeignKey("shipments.shipment_id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(32), ForeignKey("reusable_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime, nullable=False, default=utc_now)
    removed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("shipment_id", "asset_id", name="uq_shipment_asset"),
    )

    # Relationships
    shipment = relationship("Shipment", back_populates="shipment_assets")
    asset = relationship("ReusableAsset", back_populates="shipment_assets")
