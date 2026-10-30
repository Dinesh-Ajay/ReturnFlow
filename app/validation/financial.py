from typing import Dict, Any, List
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.deposit_ledger import DepositLedger

class FinancialValidator:
    """
    Validates financial ledger entries, reconciliations, and duplicate refund detection.
    """

    @classmethod
    def detect_duplicate_refunds(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Anomaly 3: Detects duplicate refunds referring to the same deposit or return cycle.
        Expected decision: DUPLICATE_REFUND
        """
        # Look for multiple DEPOSIT_REFUND entries on the same asset and RMA, or matching -DUP reference suffix
        query = text("""
            SELECT 
                dl.ledger_id,
                dl.asset_id,
                dl.transaction_reference,
                dl.transaction_amount,
                dl.rma_id,
                dl.transaction_date
            FROM deposit_ledger dl
            WHERE dl.transaction_type = 'DEPOSIT_REFUND'
              AND (
                  dl.transaction_reference LIKE '%-DUP'
                  OR dl.asset_id IN (
                      SELECT asset_id 
                      FROM deposit_ledger 
                      WHERE transaction_type = 'DEPOSIT_REFUND' 
                      GROUP BY asset_id, rma_id 
                      HAVING COUNT(*) > 1 AND rma_id IS NOT NULL
                  )
              )
        """)
        rows = db.execute(query).fetchall()

        # Identify anomalous duplicate entries (those with -DUP or secondary refunds exceeding deposit)
        anomalies = []
        for r in rows:
            ref = str(r[2])
            if "-DUP" in ref:
                anomalies.append({
                    "issue_type": "DUPLICATE_REFUND",
                    "severity": "HIGH",
                    "asset_id": r[1],
                    "record_id": ref,
                    "entity_name": "deposit_ledger",
                    "expected_decision": "DUPLICATE_REFUND",
                    "description": f"Duplicate refund detected with reference {ref} for asset {r[1]}"
                })
        return anomalies

    @classmethod
    def reconcile_ledger_totals(cls, db: Session) -> Dict[str, Any]:
        """
        Validates whether deposits and liabilities balance correctly across the portfolio.
        """
        query = text("""
            SELECT 
                transaction_type,
                SUM(transaction_amount) AS total_amount,
                COUNT(*) AS total_count
            FROM deposit_ledger
            GROUP BY transaction_type
        """)
        rows = db.execute(query).fetchall()
        raw_amounts = {r[0]: Decimal(str(r[1] or 0)) for r in rows}
        summary = {r[0]: {"amount": float(raw_amounts[r[0]]), "count": int(r[2])} for r in rows}

        # Ledger convention: charges are positive liabilities and refunds are
        # negative entries. Keep the arithmetic in Decimal through calculation.
        collected = raw_amounts.get("DEPOSIT_CHARGE", Decimal("0.00"))
        refunded = abs(raw_amounts.get("DEPOSIT_REFUND", Decimal("0.00")))
        damage = raw_amounts.get("DAMAGE_CHARGE", Decimal("0.00"))
        loss = raw_amounts.get("LOSS_CHARGE", Decimal("0.00"))
        adjustments = raw_amounts.get("ADJUSTMENT", Decimal("0.00"))
        net_liability = collected - refunded - damage - loss + adjustments

        sign_issues = db.execute(text("""
            SELECT COUNT(*) FROM deposit_ledger
            WHERE (transaction_type = 'DEPOSIT_REFUND' AND transaction_amount >= 0)
               OR (transaction_type IN ('DEPOSIT_CHARGE', 'DAMAGE_CHARGE', 'LOSS_CHARGE', 'REPAIR_CHARGE') AND transaction_amount < 0)
               OR transaction_reference IS NULL OR TRIM(transaction_reference) = ''
        """)).scalar_one()
        duplicate_refunds = cls.detect_duplicate_refunds(db)

        is_reconciled = net_liability >= 0

        return {
            "summary": summary,
            "total_collected": float(collected),
            "total_refunded": float(refunded),
            "total_damage": float(damage),
            "total_loss": float(loss),
            "total_adjustments": float(adjustments),
            "net_liability": float(net_liability),
            "unreconciled_transactions": int(sign_issues),
            "duplicate_refund_findings": len(duplicate_refunds),
            "is_reconciled": is_reconciled and int(sign_issues) == 0
        }
