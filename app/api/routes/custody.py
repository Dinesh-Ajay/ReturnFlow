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
    from app.services.lifecycle_service import record_transition
    try:
        with db.begin_nested():
            asset = db.query(ReusableAsset).filter_by(asset_id=payload.asset_id).with_for_update().one_or_none()
            if not asset:
                raise HTTPException(404, "Asset not found")
            if not payload.actor_owner_id:
                raise ValueError("A live event requires an actor")
            if payload.event_type not in {"TRANSFERRED", "LOST_REPORTED", "RETIRED", "RECOVERED"}:
                raise ValueError("Workflow events must be recorded through their shipment, return, inspection or repair operation")
            physical = payload.event_type in {"DISPATCHED", "RECEIVED", "TRANSFERRED", "RETURNED", "REPAIR_STARTED", "LOST_REPORTED", "RECOVERED"}
            event = record_transition(db, asset, payload.event_type, payload.event_timestamp,
                payload.actor_owner_id, physical=physical,
                location=payload.to_location_id, custodian=payload.to_owner_id,
                reference=payload.event_reference, shipment_id=payload.shipment_id,
                notes=payload.notes)
        db.commit()
        db.refresh(event)
        return event
    except ValueError as exc:
        db.rollback()
        raise HTTPException(400, str(exc))

@router.get("/assets/{asset_id}/custody-history")
def get_asset_custody_history(asset_id: str, db: Session = Depends(get_db)):
    data = CustodyService.get_asset_full_traceability(db, asset_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")
    return data
