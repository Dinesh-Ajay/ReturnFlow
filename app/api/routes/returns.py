from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.return_authorization import ReturnAuthorization
from app.services.return_service import ReturnService
from app.schemas.entities import ReturnCreate, ReturnResponse, ReturnReceiveRequest

router = APIRouter(prefix="/api/returns", tags=["Returns"])

@router.get("")
def list_returns(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ReturnAuthorization).join(
        ReturnAuthorization.requesting_owner
    ).join(
        ReturnAuthorization.return_location
    )

    if status and status != "All":
        query = query.filter(ReturnAuthorization.rma_status == status)

    total_count = query.count()
    offset = (page - 1) * page_size
    rmas = query.order_by(ReturnAuthorization.requested_date.desc()).offset(offset).limit(page_size).all()

    items = []
    for r in rmas:
        items.append({
            "rma_id": r.rma_id,
            "requesting_owner_id": r.requesting_owner_id,
            "requesting_owner_name": r.requesting_owner.owner_name,
            "receiving_owner_id": r.receiving_owner_id,
            "return_location_id": r.return_location_id,
            "return_location_name": r.return_location.location_name,
            "requested_date": r.requested_date.strftime("%Y-%m-%d"),
            "expected_return_date": r.expected_return_date.strftime("%Y-%m-%d"),
            "actual_return_date": r.actual_return_date.strftime("%Y-%m-%d") if r.actual_return_date else "-",
            "rma_status": r.rma_status,
            "reason": r.reason,
            "asset_count": len(r.rma_assets)
        })

    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "items": items
    }

@router.post("", status_code=status.HTTP_201_CREATED)
def create_return_authorization(payload: ReturnCreate, db: Session = Depends(get_db)):
    try:
        rma = ReturnService.create_rma(
            db=db,
            requesting_owner_id=payload.requesting_owner_id,
            receiving_owner_id=payload.receiving_owner_id,
            return_location_id=payload.return_location_id,
            requested_date=payload.requested_date,
            expected_return_date=payload.expected_return_date,
            asset_ids=payload.asset_ids,
            reason=payload.reason
        )
        db.commit()
        return {
            "rma_id": rma.rma_id,
            "status": rma.rma_status,
            "asset_count": len(payload.asset_ids),
            "message": "Return authorization created and approved."
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{rma_id}")
def get_return_detail(rma_id: str, db: Session = Depends(get_db)):
    rma = db.query(ReturnAuthorization).filter(ReturnAuthorization.rma_id == rma_id).first()
    if not rma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"RMA {rma_id} not found.")

    assets = [raa.asset_id for raa in rma.rma_assets]
    return {
        "rma_id": rma.rma_id,
        "requesting_owner": rma.requesting_owner.owner_name,
        "receiving_owner": rma.receiving_owner.owner_name,
        "return_location": rma.return_location.location_name,
        "requested_date": rma.requested_date.isoformat(),
        "expected_return_date": rma.expected_return_date.isoformat(),
        "actual_return_date": rma.actual_return_date.isoformat() if rma.actual_return_date else None,
        "rma_status": rma.rma_status,
        "reason": rma.reason,
        "manifest_assets": assets
    }

@router.post("/{rma_id}/receive")
def receive_return(rma_id: str, payload: ReturnReceiveRequest, db: Session = Depends(get_db)):
    try:
        rma = ReturnService.receive_return(
            db=db,
            rma_id=rma_id,
            actual_return_date=payload.actual_return_date,
            default_condition=payload.return_condition
        )
        db.commit()
        return {
            "rma_id": rma.rma_id,
            "status": rma.rma_status,
            "actual_return_date": rma.actual_return_date.isoformat(),
            "message": "Return successfully marked as received."
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
