from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.repair import Repair
from app.services.repair_service import RepairService
from app.schemas.entities import RepairCreate, RepairCompleteRequest, RepairResponse

router = APIRouter(prefix="/api/repairs", tags=["Repairs"])

@router.get("", response_model=List[RepairResponse])
def list_repairs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Repair)
    if status and status != "All":
        query = query.filter(Repair.repair_status == status)
    if asset_id:
        query = query.filter(Repair.asset_id == asset_id)

    offset = (page - 1) * page_size
    return query.order_by(Repair.repair_start_date.desc()).offset(offset).limit(page_size).all()

@router.post("", response_model=RepairResponse, status_code=status.HTTP_201_CREATED)
def initiate_repair(payload: RepairCreate, db: Session = Depends(get_db)):
    try:
        repair = RepairService.initiate_repair(
            db=db,
            asset_id=payload.asset_id,
            repair_location_id=payload.repair_location_id,
            inspection_id=payload.inspection_id,
            notes=payload.repair_notes,
            start_date=payload.start_date
        )
        db.commit()
        db.refresh(repair)
        return repair
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.post("/{repair_id}/complete", response_model=RepairResponse)
def complete_repair(repair_id: str, payload: RepairCompleteRequest, db: Session = Depends(get_db)):
    try:
        repair = RepairService.complete_repair(
            db=db,
            repair_id=repair_id,
            cost=payload.repair_cost,
            completion_date=payload.completion_date,
            notes=payload.repair_notes
        )
        db.commit()
        db.refresh(repair)
        return repair
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
