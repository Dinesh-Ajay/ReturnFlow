from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class AssetType(Base):
    __tablename__ = "asset_types"

    asset_type_id = Column(Integer, primary_key=True, autoincrement=True)
    type_code = Column(String(32), unique=True, nullable=False, index=True)
    type_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    default_deposit_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    expected_lifecycle_days = Column(Integer, nullable=False, default=365)
    return_due_days = Column(Integer, nullable=False, default=30)
    loss_threshold_days = Column(Integer, nullable=False, default=60)
    requires_inspection = Column(Boolean, nullable=False, default=True)
    repairable = Column(Boolean, nullable=False, default=True)
    active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    assets = relationship("ReusableAsset", back_populates="asset_type")
