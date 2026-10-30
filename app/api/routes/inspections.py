from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.inspection import Inspection
from app.services.inspection_service import InspectionService
from app.schemas.entities import InspectionCreate, InspectionResponse

router = APIRouter(prefix="/api/inspections", tags=["Inspections"])

@router.get("", response_model=List[InspectionResponse])
def list_inspections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    condition: Optional[str] = Query(None),
    asset_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Inspection)
    if condition and condition != "All":
        query = query.filter(Inspection.condition_status == condition)
    if asset_id:
        query = query.filter(Inspection.asset_id == asset_id)

    offset = (page - 1) * page_size
    return query.order_by(Inspection.inspection_date.desc()).offset(offset).limit(page_size).all()

@router.post("", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def record_inspection(payload: InspectionCreate, db: Session = Depends(get_db)):
    try:
        inspection = InspectionService.record_inspection(
            db=db,
            asset_id=payload.asset_id,
            inspector_owner_id=payload.inspector_owner_id,
            condition_status=payload.condition_status,
            rma_id=payload.rma_id,
            damage_severity=payload.damage_severity,
            requires_repair=payload.requires_repair,
            inspection_notes=payload.inspection_notes,
            inspection_date=payload.inspection_date
        )
        db.commit()
        db.refresh(inspection)
        return inspection
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
