from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class DepositLedger(Base):
    __tablename__ = "deposit_ledger"

    ledger_id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(String(32), ForeignKey("reusable_assets.asset_id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id = Column(Integer, ForeignKey("owners.owner_id", ondelete="RESTRICT"), nullable=False, index=True)
    shipment_id = Column(String(32), ForeignKey("shipments.shipment_id", ondelete="SET NULL"), nullable=True, index=True)
    rma_id = Column(String(32), ForeignKey("return_authorizations.rma_id", ondelete="SET NULL"), nullable=True, index=True)
    transaction_type = Column(String(32), nullable=False, index=True)  # DEPOSIT_CHARGE, DEPOSIT_REFUND, DAMAGE_CHARGE, REPAIR_CHARGE, LOSS_CHARGE, ADJUSTMENT
    transaction_amount = Column(Numeric(12, 2), nullable=False)
    transaction_reference = Column(String(64), nullable=False, index=True)
    transaction_date = Column(DateTime, nullable=False, index=True)
    related_ledger_id = Column(Integer, ForeignKey("deposit_ledger.ledger_id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utc_now)

    # Relationships
    asset = relationship("ReusableAsset", back_populates="deposit_transactions")
    owner = relationship("Owner", back_populates="deposit_transactions")
    shipment = relationship("Shipment", back_populates="deposit_transactions")
    rma = relationship("ReturnAuthorization", back_populates="deposit_transactions")
    related_entry = relationship("DepositLedger", remote_side=[ledger_id])
