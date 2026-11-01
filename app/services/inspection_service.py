from app.services.lifecycle_service import atomic_operation, record_transition, utc_naive
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
    @atomic_operation
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
        asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == asset_id).with_for_update().populate_existing().first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found.")

        if asset.asset_status == "RETIRED":
            raise ValueError(f"Asset {asset_id} is RETIRED and cannot be inspected.")

        if condition_status not in ("GOOD", "DAMAGED", "CRITICAL", "UNUSABLE"):
            raise ValueError("Invalid inspection condition")
        if asset.asset_status not in ("INSPECTION_PENDING", "RETURNED"):
            raise ValueError("Inspection requires a returned or inspection-pending asset")
        if asset.asset_status == "RETURNED":
            asset.asset_status = "INSPECTION_PENDING"  # compound inspection prerequisite
        if rma_id:
            from app.models.return_authorization_asset import ReturnAuthorizationAsset
            if not db.query(ReturnAuthorizationAsset).filter_by(rma_id=rma_id, asset_id=asset_id).first():
                raise ValueError("Inspection RMA does not contain this asset")
        requires_repair = condition_status in ("DAMAGED", "CRITICAL")

        insp_dt = utc_naive(inspection_date or utc_now())
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

        event_type = {"GOOD": "INSPECTED_GOOD", "UNUSABLE": "INSPECTED_UNUSABLE"}.get(condition_status, "INSPECTED_DAMAGED")
        record_transition(db, asset, event_type, insp_dt, inspector_owner_id, reference=insp_id)

        db.add(inspection)
        db.flush()
        return inspection
