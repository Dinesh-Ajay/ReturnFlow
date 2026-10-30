from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class CustodyEvent(Base):
    __tablename__ = "custody_events"

    custody_event_id = Column(String(64), primary_key=True)  # CUST-ASSET-0000001-000001
    asset_id = Column(String(32), ForeignKey("reusable_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    shipment_id = Column(String(32), ForeignKey("shipments.shipment_id", ondelete="SET NULL"), nullable=True, index=True)
    from_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="SET NULL"), nullable=True, index=True)
    to_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="SET NULL"), nullable=True, index=True)
    from_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="SET NULL"), nullable=True, index=True)
    to_location_id = Column(Integer, ForeignKey("locations.location_id", ondelete="SET NULL"), nullable=True, index=True)
    actor_owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(32), nullable=False, index=True)
    event_timestamp = Column(DateTime, nullable=False, index=True)
    event_reference = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    asset = relationship("ReusableAsset", back_populates="custody_events")
    shipment = relationship("Shipment", back_populates="custody_events")
    from_owner = relationship("Owner", foreign_keys=[from_owner_id])
    to_owner = relationship("Owner", foreign_keys=[to_owner_id])
    from_location = relationship("Location", foreign_keys=[from_location_id])
    to_location = relationship("Location", foreign_keys=[to_location_id])
    actor_owner = relationship("Owner", foreign_keys=[actor_owner_id])
