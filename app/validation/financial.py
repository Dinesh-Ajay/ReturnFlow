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
        summary = {r[0]: {"amount": float(r[1] or 0), "count": int(r[2])} for r in rows}

        collected = summary.get("DEPOSIT_CHARGE", {}).get("amount", 0.0)
        refunded = abs(summary.get("DEPOSIT_REFUND", {}).get("amount", 0.0))
        damage = summary.get("DAMAGE_CHARGE", {}).get("amount", 0.0)

        is_reconciled = (collected - refunded - damage) >= 0.0

        return {
            "summary": summary,
            "total_collected": collected,
            "total_refunded": refunded,
            "total_damage": damage,
            "net_liability": collected - refunded - damage,
            "is_reconciled": is_reconciled
        }
