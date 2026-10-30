from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database.session import get_db
from app.models.shipment import Shipment
from app.models.shipment_asset import ShipmentAsset
from app.models.location import Location
from app.models.owner import Owner
from app.services.shipment_service import ShipmentService
from app.schemas.entities import ShipmentCreate, ShipmentResponse

router = APIRouter(prefix="/api/shipments", tags=["Shipments"])

@router.get("")
def list_shipments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    origin_id: Optional[int] = Query(None),
    dest_id: Optional[int] = Query(None),
    carrier_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Shipment)

    if search:
        s_clean = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Shipment.shipment_id.ilike(s_clean),
                Shipment.tracking_reference.ilike(s_clean)
            )
        )

    if status and status != "All":
        query = query.filter(Shipment.shipment_status == status)
    if origin_id:
        query = query.filter(Shipment.origin_location_id == origin_id)
    if dest_id:
        query = query.filter(Shipment.destination_location_id == dest_id)
    if carrier_id:
        query = query.filter(Shipment.carrier_owner_id == carrier_id)

    total_count = query.count()
    offset = (page - 1) * page_size
    shipments = query.order_by(Shipment.dispatch_date.desc()).offset(offset).limit(page_size).all()

    items = []
    for s in shipments:
        items.append({
            "shipment_id": s.shipment_id,
            "origin_location_id": s.origin_location_id,
            "origin_location_name": s.origin_location.location_name,
            "destination_location_id": s.destination_location_id,
            "destination_location_name": s.destination_location.location_name,
            "carrier_owner_id": s.carrier_owner_id,
            "carrier_name": s.carrier.owner_name,
            "dispatch_date": s.dispatch_date.strftime("%Y-%m-%d"),
            "expected_delivery_date": s.expected_delivery_date.strftime("%Y-%m-%d"),
            "actual_delivery_date": s.actual_delivery_date.strftime("%Y-%m-%d") if s.actual_delivery_date else "-",
            "shipment_status": s.shipment_status,
            "tracking_reference": s.tracking_reference,
            "asset_count": len(s.shipment_assets)
        })

    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "items": items
    }

@router.post("", status_code=status.HTTP_201_CREATED)
def create_shipment(payload: ShipmentCreate, db: Session = Depends(get_db)):
    try:
        shipment = ShipmentService.create_shipment(
            db=db,
            origin_location_id=payload.origin_location_id,
            destination_location_id=payload.destination_location_id,
            carrier_owner_id=payload.carrier_owner_id,
            dispatch_date=payload.dispatch_date,
            expected_delivery_date=payload.expected_delivery_date,
            asset_ids=payload.asset_ids,
            tracking_reference=payload.tracking_reference
        )
        db.commit()
        return {
            "shipment_id": shipment.shipment_id,
            "status": shipment.shipment_status,
            "asset_count": len(payload.asset_ids),
            "message": "Shipment dispatched successfully."
        }
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{shipment_id}")
def get_shipment_detail(shipment_id: str, db: Session = Depends(get_db)):
    shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Shipment {shipment_id} not found.")

    assets = [sa.asset_id for sa in shipment.shipment_assets]
    return {
        "shipment_id": shipment.shipment_id,
        "origin_location": shipment.origin_location.location_name,
        "destination_location": shipment.destination_location.location_name,
        "carrier_name": shipment.carrier.owner_name,
        "dispatch_date": shipment.dispatch_date.isoformat(),
        "expected_delivery_date": shipment.expected_delivery_date.isoformat(),
        "actual_delivery_date": shipment.actual_delivery_date.isoformat() if shipment.actual_delivery_date else None,
        "shipment_status": shipment.shipment_status,
        "tracking_reference": shipment.tracking_reference,
        "asset_count": len(assets),
        "manifest_assets": assets
    }
