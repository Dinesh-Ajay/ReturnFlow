from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.inspection import Inspection
from app.models.asset import ReusableAsset
from app.models.return_authorization import ReturnAuthorization
from app.services.lifecycle_service import LifecycleService
from app.utils.id_generator import IDGenerator, PersistentIDGenerator

def utc_now():
    return datetime.now(timezone.utc)

class InspectionService:
    """
    Manages asset inspections after return, evaluates damage severity,
    and transitions asset lifecycle state.
    """

    @classmethod
    def record_inspection(
        cls,
        db: Session,
        asset_id: str,
        inspector_owner_id: int,
        condition_status: str,  # GOOD, DAMAGED, CRITICAL, UNUSABLE
        rma_id: Optional[str] = None,
        damage_severity: Optional[str] = None,  # NONE, MINOR, MODERATE, SEVERE
        requires_repair: bool = False,
        inspection_notes: Optional[str] = None,
        inspection_date: Optional[datetime] = None,
        custom_id: Optional[str] = None
    ) -> Inspection:
        asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found.")

        if asset.asset_status == "RETIRED":
            raise ValueError(f"Asset {asset_id} is RETIRED and cannot be inspected.")

        # Determine next lifecycle status
        if condition_status == "GOOD":
            next_status = "AVAILABLE"
            requires_repair = False
        else:
            next_status = "DAMAGED"
            requires_repair = True

        valid, err = LifecycleService.validate_transition(asset.asset_status, next_status)
        if not valid and asset.asset_status not in ("INSPECTION_PENDING", "RETURNED", "UNDER_REPAIR"):
            raise ValueError(f"Invalid transition for asset {asset_id} from {asset.asset_status} to {next_status}: {err}")

        insp_dt = inspection_date or utc_now()
        insp_id = custom_id or PersistentIDGenerator.next_inspection_id(db, year=insp_dt.year)

        inspection = Inspection(
            inspection_id=insp_id,
            asset_id=asset_id,
            rma_id=rma_id,
            inspector_owner_id=inspector_owner_id,
            inspection_date=insp_dt,
            condition_status=condition_status,
            damage_severity=damage_severity or ("NONE" if condition_status == "GOOD" else "MODERATE"),
            requires_repair=requires_repair,
            inspection_notes=inspection_notes or f"Asset condition evaluated as {condition_status}"
        )

        # Update asset status
        asset.asset_status = next_status
        asset.last_event_at = insp_dt
        asset.updated_at = utc_now()

        db.add(inspection)
        db.flush()
        return inspection
