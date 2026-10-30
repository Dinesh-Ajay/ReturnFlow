from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.repair import Repair
from app.models.inspection import Inspection
from app.models.asset import ReusableAsset
from app.models.location import Location
from app.utils.id_generator import IDGenerator

def utc_now():
    return datetime.now(timezone.utc)

class RepairService:
    """
    Manages asset maintenance, repair initiation, and completion.
    """

    @classmethod
    def initiate_repair(
        cls,
        db: Session,
        asset_id: str,
        repair_location_id: int,
        inspection_id: Optional[str] = None,
        notes: Optional[str] = None,
        start_date: Optional[datetime] = None,
        custom_id: Optional[str] = None
    ) -> Repair:
        asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == asset_id).first()
        if not asset:
            raise ValueError(f"Asset {asset_id} not found.")

        # Check inspection
        if inspection_id:
            insp = db.query(Inspection).filter(Inspection.inspection_id == inspection_id).first()
            if not insp:
                raise ValueError(f"Inspection {inspection_id} does not exist.")

        rep_id = custom_id or IDGenerator(year=2026).next_repair_id()

        repair = Repair(
            repair_id=rep_id,
            asset_id=asset_id,
            inspection_id=inspection_id,
            repair_location_id=repair_location_id,
            repair_status="IN_PROGRESS",
            repair_start_date=start_date or utc_now(),
            repair_cost=Decimal("0.00"),
            repair_notes=notes or f"Repair commenced at facility {repair_location_id}"
        )

        asset.asset_status = "UNDER_REPAIR"
        asset.current_location_id = repair_location_id
        asset.updated_at = utc_now()

        db.add(repair)
        db.flush()
        return repair

    @classmethod
    def complete_repair(
        cls,
        db: Session,
        repair_id: str,
        cost: Decimal,
        completion_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        allow_without_inspection: bool = False
    ) -> Repair:
        repair = db.query(Repair).filter(Repair.repair_id == repair_id).first()
        if not repair:
            raise ValueError(f"Repair record {repair_id} not found.")

        if not allow_without_inspection and not repair.inspection_id:
            raise ValueError(f"Repair {repair_id} cannot be completed without an originating inspection.")

        if cost < 0:
            raise ValueError("Repair cost cannot be negative.")

        comp_dt = completion_date or utc_now()
        if comp_dt < repair.repair_start_date:
            raise ValueError("Repair completion date cannot precede start date.")

        repair.repair_status = "COMPLETED"
        repair.repair_completion_date = comp_dt
        repair.repair_cost = cost
        if notes:
            repair.repair_notes = f"{repair.repair_notes or ''} | {notes}".strip()

        # Update asset status -> post-repair INSPECTION_PENDING
        asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == repair.asset_id).first()
        if asset:
            asset.asset_status = "INSPECTION_PENDING"
            asset.updated_at = utc_now()

        db.flush()
        return repair
