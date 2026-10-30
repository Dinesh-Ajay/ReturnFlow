from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class ReturnAuthorizationAsset(Base):
    __tablename__ = "return_authorization_assets"

    rma_asset_id = Column(Integer, primary_key=True, autoincrement=True)
    rma_id = Column(String(32), ForeignKey("return_authorizations.rma_id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(String(32), ForeignKey("reusable_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    return_condition = Column(String(32), nullable=True)  # GOOD, DAMAGED, CRITICAL, UNUSABLE
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    __table_args__ = (
        UniqueConstraint("rma_id", "asset_id", name="uq_rma_asset"),
    )

    # Relationships
    rma = relationship("ReturnAuthorization", back_populates="rma_assets")
    asset = relationship("ReusableAsset", back_populates="rma_assets")
