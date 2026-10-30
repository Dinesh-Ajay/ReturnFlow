from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.deposit_ledger import DepositLedger
from app.services.deposit_service import DepositService
from app.schemas.entities import DepositChargeRequest, DepositRefundRequest, DepositLedgerResponse

router = APIRouter(prefix="/api/deposits", tags=["Deposits & Financials"])

@router.get("", response_model=List[DepositLedgerResponse])
def list_deposit_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    tx_type: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(DepositLedger)
    if tx_type and tx_type != "All":
        query = query.filter(DepositLedger.transaction_type == tx_type)
    if asset_id:
        query = query.filter(DepositLedger.asset_id == asset_id)

    offset = (page - 1) * page_size
    return query.order_by(DepositLedger.transaction_date.desc()).offset(offset).limit(page_size).all()

@router.post("/charge", response_model=DepositLedgerResponse, status_code=status.HTTP_201_CREATED)
def record_charge(payload: DepositChargeRequest, db: Session = Depends(get_db)):
    try:
        entry = DepositService.record_deposit_charge(
            db=db,
            asset_id=payload.asset_id,
            owner_id=payload.owner_id,
            amount=payload.amount,
            reference=payload.reference,
            shipment_id=payload.shipment_id,
            description=payload.description
        )
        db.commit()
        db.refresh(entry)
        return entry
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/refund", response_model=DepositLedgerResponse, status_code=status.HTTP_201_CREATED)
def record_refund(payload: DepositRefundRequest, db: Session = Depends(get_db)):
    try:
        entry = DepositService.record_deposit_refund(
            db=db,
            asset_id=payload.asset_id,
            owner_id=payload.owner_id,
            amount=payload.amount,
            reference=payload.reference,
            rma_id=payload.rma_id,
            related_ledger_id=payload.related_ledger_id,
            description=payload.description
        )
        db.commit()
        db.refresh(entry)
        return entry
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/reconciliation")
def get_financial_reconciliation(db: Session = Depends(get_db)):
    return DepositService.get_portfolio_financial_summary(db)
