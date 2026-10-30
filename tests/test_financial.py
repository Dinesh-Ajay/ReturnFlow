import pytest
from decimal import Decimal
from app.services.deposit_service import DepositService
from app.models.deposit_ledger import DepositLedger

def test_financial_deposit_and_refund(db_session):
    asset_id = "ASSET-0000001"
    initial_balance = DepositService.get_asset_financial_balance(db_session, asset_id)
    
    # Test valid charge
    charge_amt = Decimal("100.00")
    tx_charge = DepositService.record_deposit_charge(
        db=db_session,
        asset_id=asset_id,
        owner_id=1,
        amount=charge_amt,
        reference="TEST-DEP-01"
    )
    assert tx_charge.transaction_amount == charge_amt

    new_balance = DepositService.get_asset_financial_balance(db_session, asset_id)
    assert new_balance["total_deposit_charged"] == pytest.approx(initial_balance["total_deposit_charged"] + 100.0)

    # Test valid partial refund
    refund_amt = Decimal("50.00")
    tx_refund = DepositService.record_deposit_refund(
        db=db_session,
        asset_id=asset_id,
        owner_id=1,
        amount=refund_amt,
        reference="TEST-REF-01"
    )
    assert tx_refund.transaction_amount == -refund_amt

    # Test refund exceeding eligible balance throws ValueError
    excess_amt = Decimal("9999999.00")
    with pytest.raises(ValueError, match="exceeds eligible refundable balance"):
        DepositService.record_deposit_refund(
            db=db_session,
            asset_id=asset_id,
            owner_id=1,
            amount=excess_amt,
            reference="TEST-FAIL-REF"
        )

def test_portfolio_reconciliation(db_session):
    summary = DepositService.get_portfolio_financial_summary(db_session)
    assert summary["total_deposits_collected"] > 0
    assert summary["total_refunds_processed"] > 0
    assert summary["reconciliation_status"] == "RECONCILED"
