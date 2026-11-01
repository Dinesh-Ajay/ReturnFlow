from collections import defaultdict
from app.services.lifecycle_service import utc_naive
from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.deposit_ledger import DepositLedger
from app.models.return_authorization_asset import ReturnAuthorizationAsset

ZERO = Decimal("0.00")
DEDUCTIONS = {"DAMAGE_CHARGE", "LOSS_CHARGE"}


class FinancialValidator:
    """Read-only, fact-based financial audit. No labels/reference naming rules.

    Damage/loss consume security deposits; repair charges are separately billed.
    Explicit related_ledger_id wins. Legacy rows are matched by asset, payer,
    shipment and chronological charge. Ambiguous obligations are exceptions,
    never silently assigned to a different cycle to hide an over-refund.
    """

    @classmethod
    def audit_obligations(cls, db: Session, asset_id=None) -> Dict[str, Any]:
        query = db.query(DepositLedger)
        if asset_id is not None:
            query = query.filter_by(asset_id=asset_id)
        rows = query.order_by(DepositLedger.transaction_date, DepositLedger.ledger_id).all()
        by_id = {r.ledger_id: r for r in rows}
        charges = defaultdict(list)
        for r in rows:
            if r.transaction_type == "DEPOSIT_CHARGE":
                charges[r.asset_id].append(r)
        links = set(db.query(ReturnAuthorizationAsset.rma_id, ReturnAuthorizationAsset.asset_id).all())
        balances = {r.ledger_id: Decimal(r.transaction_amount) for rs in charges.values() for r in rs}
        asset_net = defaultdict(lambda: ZERO)
        totals = defaultdict(lambda: ZERO)
        counts = defaultdict(int)
        seen_refs = set()
        refund_history = defaultdict(list)
        rma_charge = defaultdict(set)
        duplicates, over_refunds, invalid, exceptions = [], [], [], []
        def finding(r, reason):
            return {"asset_id": r.asset_id, "ledger_id": r.ledger_id,
                    "reference": r.transaction_reference, "reason": reason}
        for r in rows:
            amount = Decimal(r.transaction_amount)
            kind = r.transaction_type
            totals[kind] += amount
            counts[kind] += 1
            ref = (r.transaction_reference or "").strip()
            repeated_ref = bool(ref and ref in seen_refs)
            if not ref or repeated_ref:
                invalid.append(finding(r, "Empty or reused transaction reference"))
            seen_refs.add(ref)
            if kind not in {"DEPOSIT_CHARGE", "DEPOSIT_REFUND", "DAMAGE_CHARGE", "LOSS_CHARGE", "REPAIR_CHARGE", "ADJUSTMENT"}:
                exceptions.append(finding(r, "Unknown transaction type"))
            if (kind == "DEPOSIT_REFUND" and amount >= 0) or (kind in {"DEPOSIT_CHARGE", "DAMAGE_CHARGE", "LOSS_CHARGE", "REPAIR_CHARGE"} and amount <= 0):
                exceptions.append(finding(r, "Invalid transaction sign"))
            signed = -amount if kind in DEDUCTIONS else amount if kind != "REPAIR_CHARGE" else ZERO
            asset_net[r.asset_id] += signed
            if kind in {"DEPOSIT_CHARGE", "REPAIR_CHARGE"}:
                continue
            if kind == "DEPOSIT_REFUND" and r.rma_id and (r.rma_id, r.asset_id) not in links:
                invalid.append(finding(r, "RMA does not contain asset"))
            if r.related_ledger_id:
                original = by_id.get(r.related_ledger_id)
                candidates = [original] if original and original.transaction_type == "DEPOSIT_CHARGE" and original.asset_id == r.asset_id and original.owner_id == r.owner_id and utc_naive(original.transaction_date) <= utc_naive(r.transaction_date) and (not r.shipment_id or original.shipment_id == r.shipment_id) else []
            else:
                candidates = [c for c in charges[r.asset_id] if c.owner_id == r.owner_id and utc_naive(c.transaction_date) <= utc_naive(r.transaction_date) and (not r.shipment_id or c.shipment_id == r.shipment_id)]
                # A reused RMA must remain linked to its original charge even
                # after the balance has been exhausted.
                prior = list(rma_charge[(r.asset_id, r.rma_id)]) if r.rma_id else []
                if len(prior) == 1:
                    candidates = [c for c in candidates if c.ledger_id == prior[0]]
                elif len(candidates) > 1:
                    candidates = [c for c in candidates if balances[c.ledger_id] > ZERO]
            if len(candidates) != 1:
                entry = finding(r, "Missing, invalid or ambiguous original deposit obligation")
                (invalid if kind == "DEPOSIT_REFUND" else exceptions).append(entry)
                continue
            original = candidates[0]
            key = original.ledger_id
            before = balances[key]
            balances[key] += signed
            if kind == "DEPOSIT_REFUND":
                hist = refund_history[key]
                exceeds = -amount > max(ZERO, before)
                if exceeds:
                    over_refunds.append(finding(r, "Refund exceeds remaining cycle obligation"))
                # Equal legitimate partial refunds are not duplicates while
                # there is still an obligation to discharge.
                duplicate = repeated_ref or (exceeds and any(h.transaction_amount == amount and h.rma_id == r.rma_id for h in hist))
                if duplicate:
                    duplicates.append({"issue_type": "DUPLICATE_REFUND", "severity": "HIGH",
                        "asset_id": r.asset_id, "record_id": r.transaction_reference,
                        "ledger_id": r.ledger_id, "entity_name": "deposit_ledger",
                        "expected_decision": "DUPLICATE_REFUND",
                        "description": "Repeated refund exceeds its original deposit obligation"})
                hist.append(r)
                if r.rma_id:
                    rma_charge[(r.asset_id, r.rma_id)].add(key)
        negative_assets = [{"asset_id": a, "liability": float(v)} for a,v in sorted(asset_net.items()) if v < ZERO]
        negative_cycles = [{"original_ledger_id": k, "liability": float(v)} for k,v in balances.items() if v < ZERO]
        net = totals["DEPOSIT_CHARGE"] + totals["DEPOSIT_REFUND"] - totals["DAMAGE_CHARGE"] - totals["LOSS_CHARGE"] + totals["ADJUSTMENT"]
        arithmetic = sum(asset_net.values(), ZERO) == net
        exception_count = len(exceptions) + len(invalid) + len(over_refunds) + len(negative_cycles)
        valid = not (exception_count or negative_assets or duplicates)
        return {
            "summary": {k: {"amount": float(v), "count": counts[k]} for k,v in totals.items()},
            "total_collected": float(totals["DEPOSIT_CHARGE"]),
            "total_refunded": float(-totals["DEPOSIT_REFUND"]),
            "total_damage": float(totals["DAMAGE_CHARGE"]), "total_loss": float(totals["LOSS_CHARGE"]),
            "total_adjustments": float(totals["ADJUSTMENT"]), "net_liability": float(net),
            "portfolio_arithmetic_balanced": arithmetic, "individual_obligations_valid": valid,
            "negative_asset_liabilities": negative_assets, "negative_cycle_liabilities": negative_cycles,
            "duplicate_refund_findings": len(duplicates), "duplicate_refund_details": duplicates,
            "over_refund_findings": len(over_refunds), "over_refund_details": over_refunds,
            "invalid_refund_references": invalid, "financial_exception_details": exceptions,
            "unresolved_financial_exceptions": exception_count,
            "unreconciled_transactions": exception_count,
            "is_reconciled": arithmetic and valid,
        }

    @classmethod
    def detect_duplicate_refunds(cls, db: Session) -> List[Dict[str, Any]]:
        return cls.audit_obligations(db)["duplicate_refund_details"]

    @classmethod
    def reconcile_ledger_totals(cls, db: Session) -> Dict[str, Any]:
        return cls.audit_obligations(db)
