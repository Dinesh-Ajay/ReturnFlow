from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.custody_event import CustodyEvent
from app.models.asset import ReusableAsset
from app.services.custody_service import CustodyService
from app.schemas.entities import CustodyEventCreate, CustodyEventResponse
from app.utils.id_generator import IDGenerator

router = APIRouter(prefix="/api/custody-events", tags=["Custody"])

@router.get("", response_model=List[CustodyEventResponse])
def list_custody_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    asset_id: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(CustodyEvent)
    if asset_id:
        query = query.filter(CustodyEvent.asset_id == asset_id)
    if event_type:
        query = query.filter(CustodyEvent.event_type == event_type)

    offset = (page - 1) * page_size
    return query.order_by(CustodyEvent.event_timestamp.desc()).offset(offset).limit(page_size).all()

@router.post("", response_model=CustodyEventResponse, status_code=status.HTTP_201_CREATED)
def record_custody_event(payload: CustodyEventCreate, db: Session = Depends(get_db)):
    asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {payload.asset_id} not found.")

    evt_id = IDGenerator(year=2026).next_custody_event_id(payload.asset_id)
    event = CustodyEvent(
        custody_event_id=evt_id,
        **payload.model_dump()
    )
    db.add(event)

    # Materialize projection on ReusableAsset
    if payload.to_location_id:
        asset.current_location_id = payload.to_location_id
    if payload.to_owner_id:
        asset.current_custodian_owner_id = payload.to_owner_id
    asset.last_event_at = payload.event_timestamp
    db.commit()
    db.refresh(event)
    return event

@router.get("/assets/{asset_id}/custody-history")
def get_asset_custody_history(asset_id: str, db: Session = Depends(get_db)):
    data = CustodyService.get_asset_full_traceability(db, asset_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")
    return data
