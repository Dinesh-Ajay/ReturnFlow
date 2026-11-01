from app.services.lifecycle_service import atomic_operation
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.deposit_ledger import DepositLedger
from app.models.asset import ReusableAsset
from app.models.owner import Owner

def utc_now():
    return datetime.now(timezone.utc)

class DepositService:
    """
    Dedicated financial reconciliation and deposit ledger management service.
    Accounting convention:
    - DEPOSIT_CHARGE: Positive (+) amount collected / held as security liability.
    - DEPOSIT_REFUND: Negative (-) amount returned to customer.
    - DAMAGE_CHARGE: Positive (+) amount assessed for damaged goods.
    - REPAIR_CHARGE: Positive (+) amount assessed for repair costs.
    - LOSS_CHARGE: Positive (+) amount assessed for lost items.
    - ADJUSTMENT: Positive (+) or Negative (-) ledger balancing entry.
    """

    @classmethod
    def get_asset_financial_balance(cls, db: Session, asset_id: str) -> Dict[str, Any]:
        entries = db.query(DepositLedger).filter(
            DepositLedger.asset_id == asset_id
        ).order_by(DepositLedger.transaction_date.asc()).all()

        total_charged = Decimal("0.00")
        total_refunded = Decimal("0.00")
        total_damage_charges = Decimal("0.00")
        total_repair_charges = Decimal("0.00")
        total_loss_charges = Decimal("0.00")
        total_adjustments = Decimal("0.00")

        for e in entries:
            amt = Decimal(str(e.transaction_amount))
            tt = e.transaction_type
            if tt == "DEPOSIT_CHARGE":
                total_charged += amt
            elif tt == "DEPOSIT_REFUND":
                total_refunded += abs(amt)
            elif tt == "DAMAGE_CHARGE":
                total_damage_charges += amt
            elif tt == "REPAIR_CHARGE":
                total_repair_charges += amt
            elif tt == "LOSS_CHARGE":
                total_loss_charges += amt
            elif tt == "ADJUSTMENT":
                total_adjustments += amt

        # Outstanding deposit liability currently held by the company for this asset
        # Net deposit liability = total_charged - total_refunded - (damage_charges + loss_charges settled against deposit)
        net_deposit_liability = total_charged - total_refunded - total_damage_charges - total_loss_charges + total_adjustments
        # Maximum refundable amount is net deposit liability (cannot refund negative or beyond what is held)
        refundable_balance = max(Decimal("0.00"), net_deposit_liability)

        return {
            "asset_id": asset_id,
            "total_deposit_charged": float(total_charged),
            "total_deposit_refunded": float(total_refunded),
            "total_damage_charges": float(total_damage_charges),
            "total_repair_charges": float(total_repair_charges),
            "total_loss_charges": float(total_loss_charges),
            "total_adjustments": float(total_adjustments),
            "net_deposit_liability": float(net_deposit_liability),
            "refundable_balance": float(refundable_balance),
            "transaction_count": len(entries),
            "is_reconciled": cls._asset_obligations_valid(db, asset_id)
        }

    @classmethod
    @atomic_operation
    def record_deposit_charge(
        cls,
        db: Session,
        asset_id: str,
        owner_id: int,
        amount: Decimal,
        reference: str,
        shipment_id: Optional[str] = None,
        description: Optional[str] = None,
        tx_date: Optional[datetime] = None
    ) -> DepositLedger:
        if amount <= 0:
            raise ValueError("Deposit charge amount must be strictly positive.")

        db.query(ReusableAsset).filter_by(asset_id=asset_id).with_for_update().one()
        if not reference or not reference.strip():
            raise ValueError("Transaction reference required")
        existing = db.query(DepositLedger).filter_by(transaction_reference=reference).first()
        if existing:
            if existing.asset_id == asset_id and existing.owner_id == owner_id and existing.shipment_id == shipment_id and existing.transaction_type == "DEPOSIT_CHARGE" and existing.transaction_amount == amount:
                return existing
            raise ValueError("Transaction reference reused with different financial facts")

        entry = DepositLedger(
            asset_id=asset_id,
            owner_id=owner_id,
            shipment_id=shipment_id,
            transaction_type="DEPOSIT_CHARGE",
            transaction_amount=amount,
            transaction_reference=reference,
            transaction_date=tx_date or utc_now(),
            description=description or f"Initial deposit charge for asset {asset_id}"
        )
        db.add(entry)
        db.flush()
        return entry

    @classmethod
    @atomic_operation
    def record_deposit_refund(
        cls,
        db: Session,
        asset_id: str,
        owner_id: int,
        amount: Decimal,
        reference: str,
        rma_id: Optional[str] = None,
        related_ledger_id: Optional[int] = None,
        description: Optional[str] = None,
        tx_date: Optional[datetime] = None,
        allow_over_refund: bool = False
    ) -> DepositLedger:
        if amount <= 0:
            raise ValueError("Deposit refund amount must be positive.")

        asset = db.query(ReusableAsset).filter_by(asset_id=asset_id).with_for_update().one()
        if not reference or not reference.strip():
            raise ValueError("Transaction reference required")
        existing = db.query(DepositLedger).filter_by(transaction_reference=reference).first()
        if existing:
            if existing.asset_id == asset_id and existing.owner_id == owner_id and existing.rma_id == rma_id and existing.transaction_type == "DEPOSIT_REFUND" and existing.transaction_amount == -amount:
                return existing  # idempotent retry of identical request
            raise ValueError("Transaction reference reused with different financial facts")
        query = db.query(DepositLedger).filter_by(asset_id=asset_id, owner_id=owner_id, transaction_type="DEPOSIT_CHARGE")
        if related_ledger_id:
            query = query.filter_by(ledger_id=related_ledger_id)
        candidates = query.all()
        if len(candidates) != 1:
            raise ValueError("Specify a unique original deposit using related_ledger_id")
        original = candidates[0]
        related_ledger_id = original.ledger_id
        if rma_id:
            from app.models.return_authorization_asset import ReturnAuthorizationAsset
            if not db.query(ReturnAuthorizationAsset).filter_by(rma_id=rma_id, asset_id=asset_id).first():
                raise ValueError("Refund RMA does not contain this asset")
        balance = cls.get_asset_financial_balance(db, asset_id)
        entries = db.query(DepositLedger).filter_by(asset_id=asset_id).all()
        cycle_balance = Decimal(original.transaction_amount)
        for row in entries:
            if row.ledger_id == original.ledger_id:
                continue
            if row.related_ledger_id == original.ledger_id or (row.shipment_id and row.shipment_id == original.shipment_id and row.owner_id == owner_id):
                if row.transaction_type == "DEPOSIT_REFUND":
                    cycle_balance += row.transaction_amount
                elif row.transaction_type in ("DAMAGE_CHARGE", "LOSS_CHARGE"):
                    cycle_balance -= row.transaction_amount
                elif row.transaction_type == "ADJUSTMENT":
                    cycle_balance += row.transaction_amount
        current_refundable = min(Decimal(str(balance["refundable_balance"])), max(Decimal("0.00"), cycle_balance))

        if amount > current_refundable:
            raise ValueError(
                f"Requested refund of {amount} exceeds eligible refundable balance {current_refundable} for asset {asset_id}."
            )

        # In our accounting convention, refunds are recorded as negative values
        entry = DepositLedger(
            asset_id=asset_id,
            owner_id=owner_id,
            rma_id=rma_id,
            related_ledger_id=related_ledger_id,
            transaction_type="DEPOSIT_REFUND",
            transaction_amount=-abs(amount),
            transaction_reference=reference,
            transaction_date=tx_date or utc_now(),
            description=description or f"Deposit refund for returned asset {asset_id}"
        )
        db.add(entry)
        db.flush()
        return entry

    @classmethod
    def get_portfolio_financial_summary(cls, db: Session) -> Dict[str, Any]:
        """
        Calculates aggregate portfolio financials across all assets.
        """
        rows = db.query(
            DepositLedger.transaction_type,
            func.sum(DepositLedger.transaction_amount).label("total_amount"),
            func.count(DepositLedger.ledger_id).label("total_count")
        ).group_by(DepositLedger.transaction_type).all()

        type_sums = {r[0]: Decimal(str(r[1] or 0)) for r in rows}
        type_counts = {r[0]: int(r[2] or 0) for r in rows}

        total_collected = type_sums.get("DEPOSIT_CHARGE", Decimal("0.00"))
        # Refund amounts stored as negative, so taking absolute value:
        total_refunded = abs(type_sums.get("DEPOSIT_REFUND", Decimal("0.00")))
        damage_charges = type_sums.get("DAMAGE_CHARGE", Decimal("0.00"))
        repair_charges = type_sums.get("REPAIR_CHARGE", Decimal("0.00"))
        loss_charges = type_sums.get("LOSS_CHARGE", Decimal("0.00"))
        adjustments = type_sums.get("ADJUSTMENT", Decimal("0.00"))

        net_deposit_liability = total_collected - total_refunded - damage_charges - loss_charges + adjustments

        return {
            "total_deposits_collected": float(total_collected),
            "total_refunds_processed": float(total_refunded),
            "total_damage_charges": float(damage_charges),
            "total_repair_charges": float(repair_charges),
            "total_loss_charges": float(loss_charges),
            "total_adjustments": float(adjustments),
            "outstanding_deposit_liability": float(net_deposit_liability),
            "transaction_type_breakdown": {k: float(v) for k, v in type_sums.items()},
            "transaction_counts": type_counts,
            "reconciliation_status": "RECONCILED" if cls._obligations_valid(db) else "DISCREPANCY_DETECTED"
        }

    @staticmethod
    def _obligations_valid(db):
        from app.validation.financial import FinancialValidator
        return FinancialValidator.reconcile_ledger_totals(db)["is_reconciled"]

    @staticmethod
    def _asset_obligations_valid(db, asset_id):
        from app.validation.financial import FinancialValidator
        return FinancialValidator.audit_obligations(db, asset_id=asset_id)["is_reconciled"]
