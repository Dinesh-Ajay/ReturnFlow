from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.models.asset import ReusableAsset
from app.models.asset_type import AssetType
from app.models.owner import Owner
from app.models.location import Location
from app.models.custody_event import CustodyEvent
from app.services.lifecycle_service import LifecycleService
from app.config import settings

class AssetService:
    """
    Core asset retrieval and management queries.
    """

    @classmethod
    def list_assets(
        cls,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        asset_type_code: Optional[str] = None,
        status: Optional[str] = None,
        owner_id: Optional[int] = None,
        location_id: Optional[int] = None,
        overdue_only: bool = False
    ) -> Tuple[List[Dict[str, Any]], int]:
        query = db.query(ReusableAsset).join(ReusableAsset.asset_type)

        if search:
            s_clean = f"%{search.strip()}%"
            query = query.join(ReusableAsset.owner).outerjoin(ReusableAsset.current_location).filter(
                or_(
                    ReusableAsset.asset_id.ilike(s_clean),
                    ReusableAsset.serial_number.ilike(s_clean),
                    AssetType.type_name.ilike(s_clean),
                    Owner.owner_name.ilike(s_clean),
                    Location.location_name.ilike(s_clean),
                    ReusableAsset.asset_status.ilike(s_clean)
                )
            )

        if asset_type_code and asset_type_code != "All":
            query = query.filter(AssetType.type_code == asset_type_code)

        if status and status != "All":
            query = query.filter(ReusableAsset.asset_status == status)

        if owner_id:
            query = query.filter(ReusableAsset.owner_id == owner_id)

        if location_id:
            query = query.filter(ReusableAsset.current_location_id == location_id)

        total_count = query.count()
        offset = (page - 1) * page_size
        assets = query.order_by(ReusableAsset.asset_id.asc()).offset(offset).limit(page_size).all()

        results = []
        for a in assets:
            # Calculate standing & days outstanding
            standing = LifecycleService.classify_asset_standing(
                status=a.asset_status,
                dispatch_date=a.last_event_at,
                return_due_days=a.asset_type.return_due_days if a.asset_type else 30,
                loss_threshold_days=a.asset_type.loss_threshold_days if a.asset_type else 60
            )

            if overdue_only and not standing["is_overdue"]:
                continue

            results.append({
                "asset_id": a.asset_id,
                "serial_number": a.serial_number,
                "type_code": a.asset_type.type_code if a.asset_type else "",
                "type_name": a.asset_type.type_name if a.asset_type else "",
                "owner_id": a.owner_id,
                "owner_name": a.owner.owner_name if a.owner else "Unknown",
                "current_location_id": a.current_location_id,
                "current_location_name": a.current_location.location_name if a.current_location else "In Transit / Unknown",
                "current_custodian_id": a.current_custodian_owner_id,
                "current_custodian_name": a.current_custodian.owner_name if a.current_custodian else "None",
                "asset_status": a.asset_status,
                "acquisition_cost": float(a.acquisition_cost),
                "deposit_amount": float(a.deposit_amount),
                "last_event_at": a.last_event_at.strftime("%Y-%m-%d %H:%M") if a.last_event_at else "N/A",
                "days_outstanding": standing["days_outstanding"],
                "is_overdue": standing["is_overdue"],
                "is_lost_candidate": standing["is_lost_candidate"],
                "created_at": a.created_at.strftime("%Y-%m-%d")
            })

        return results, total_count
