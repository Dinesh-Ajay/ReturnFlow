from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.asset_service import AssetService
from app.services.custody_service import CustodyService
from app.services.lifecycle_service import LifecycleService
from app.services.deposit_service import DepositService
from app.models.asset import ReusableAsset
from app.schemas.asset import AssetListResponse, AssetCreate

router = APIRouter(prefix="/api/assets", tags=["Assets"])

@router.post("", status_code=status.HTTP_201_CREATED)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    """
    Registers a new reusable asset in ReturnFlow.
    Generates sequential ASSET-XXXXXXX identifier, links owner and location,
    and logs initial commissioning custody event.
    """
    try:
        new_asset = AssetService.create_asset(db, payload.model_dump())
        return {
            "status": "success",
            "message": f"Asset {new_asset['asset_id']} successfully registered.",
            "asset": new_asset
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to register asset: {str(e)}")

@router.get("", response_model=AssetListResponse)
def list_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    owner_id: Optional[int] = Query(None),
    location_id: Optional[int] = Query(None),
    overdue_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    items, total_count = AssetService.list_assets(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        asset_type_code=asset_type,
        status=status,
        owner_id=owner_id,
        location_id=location_id,
        overdue_only=overdue_only
    )
    return {
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "items": items
    }

@router.get("/{asset_id}")
def get_asset_detail(asset_id: str, db: Session = Depends(get_db)):
    data = CustodyService.get_asset_full_traceability(db, asset_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")
    return data

@router.get("/{asset_id}/history")
@router.get("/{asset_id}/events")
def get_asset_history(asset_id: str, db: Session = Depends(get_db)):
    data = CustodyService.get_asset_full_traceability(db, asset_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")
    return {
        "asset_id": asset_id,
        "events_count": data["events_count"],
        "events": data["events"]
    }

@router.get("/{asset_id}/status")
def get_asset_status(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")

    standing = LifecycleService.classify_asset_standing(
        status=asset.asset_status,
        dispatch_date=asset.last_event_at,
        return_due_days=asset.asset_type.return_due_days if asset.asset_type else 30,
        loss_threshold_days=asset.asset_type.loss_threshold_days if asset.asset_type else 60
    )
    return {
        "asset_id": asset_id,
        "serial_number": asset.serial_number,
        "status": asset.asset_status,
        "days_outstanding": standing["days_outstanding"],
        "is_overdue": standing["is_overdue"],
        "is_lost_candidate": standing["is_lost_candidate"],
        "last_event_at": asset.last_event_at
    }

@router.get("/{asset_id}/financial-summary")
def get_asset_financial_summary(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {asset_id} not found.")
    return DepositService.get_asset_financial_balance(db, asset_id)
