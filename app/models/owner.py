from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class Owner(Base):
    __tablename__ = "owners"

    owner_id = Column(Integer, primary_key=True, autoincrement=True)
    owner_code = Column(String(32), unique=True, nullable=False, index=True)
    owner_name = Column(String(150), nullable=False)
    owner_type = Column(String(50), nullable=False, index=True)  # SUPPLIER, CUSTOMER, CARRIER, WAREHOUSE_OPERATOR, INTERNAL_OPERATIONS
    contact_email = Column(String(150), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    owned_assets = relationship("ReusableAsset", foreign_keys="ReusableAsset.owner_id", back_populates="owner")
    custodian_assets = relationship("ReusableAsset", foreign_keys="ReusableAsset.current_custodian_owner_id", back_populates="current_custodian")
    carrier_shipments = relationship("Shipment", foreign_keys="Shipment.carrier_owner_id", back_populates="carrier")
    deposit_transactions = relationship("DepositLedger", foreign_keys="DepositLedger.owner_id", back_populates="owner")
