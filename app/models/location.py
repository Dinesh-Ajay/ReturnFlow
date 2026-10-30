from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Location(Base):
    __tablename__ = "locations"

    location_id = Column(Integer, primary_key=True, autoincrement=True)
    location_code = Column(String(32), unique=True, nullable=False, index=True)
    location_name = Column(String(150), nullable=False)
    location_type = Column(String(50), nullable=False, index=True)  # SUPPLIER, WAREHOUSE, DISTRIBUTION_CENTER, CUSTOMER_SITE, REPAIR_CENTER, TRANSIT_HUB
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    country = Column(String(100), nullable=False, default="USA")
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    assets_here = relationship("ReusableAsset", foreign_keys="ReusableAsset.current_location_id", back_populates="current_location")
    origin_shipments = relationship("Shipment", foreign_keys="Shipment.origin_location_id", back_populates="origin_location")
    destination_shipments = relationship("Shipment", foreign_keys="Shipment.destination_location_id", back_populates="destination_location")
    repair_operations = relationship("Repair", foreign_keys="Repair.repair_location_id", back_populates="repair_location")
