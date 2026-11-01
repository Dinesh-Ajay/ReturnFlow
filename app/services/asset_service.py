from app.services.lifecycle_service import atomic_operation
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, date
from decimal import Decimal
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, func
from app.models.asset import ReusableAsset
from app.models.asset_type import AssetType
from app.models.owner import Owner
from app.models.location import Location
from app.models.custody_event import CustodyEvent
from app.services.lifecycle_service import LifecycleService
from app.utils.id_generator import PersistentIDGenerator
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
        overdue_only: bool = False,
        reference_date: Optional[date] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        dispatches = LifecycleService.dispatch_subquery(db)
        active_dispatch = and_(dispatches.c.dispatch_at.isnot(None), or_(dispatches.c.returned_at.is_(None), dispatches.c.dispatch_at > dispatches.c.returned_at))
        query = db.query(ReusableAsset).join(ReusableAsset.asset_type).outerjoin(dispatches, dispatches.c.asset_id == ReusableAsset.asset_id)
        aliases = {"at location": "AVAILABLE", "in transit": "IN_TRANSIT", "in custody": "IN_CUSTODY", "in repair": "UNDER_REPAIR", "under inspection": "INSPECTION_PENDING", "in_repair": "UNDER_REPAIR"}
        if status:
            status = aliases.get(status.strip().lower(), status)
        if search and search.strip().lower() in aliases:
            query = query.filter(ReusableAsset.asset_status == aliases[search.strip().lower()])
            search = None

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

        if overdue_only:
            age = LifecycleService.age_sql(dispatches.c.dispatch_at, reference_date or settings.REFERENCE_DATE, db.get_bind().dialect.name)
            query = query.filter(ReusableAsset.asset_status.in_(["DISPATCHED", "IN_TRANSIT", "IN_CUSTODY", "RETURN_PENDING"]), active_dispatch, age > AssetType.return_due_days)
        total_count = query.count()
        offset = (page - 1) * page_size
        assets = query.add_columns(dispatches.c.dispatch_at, dispatches.c.returned_at).options(joinedload(ReusableAsset.asset_type), joinedload(ReusableAsset.owner), joinedload(ReusableAsset.current_location), joinedload(ReusableAsset.current_custodian)).order_by(ReusableAsset.asset_id.asc()).offset(offset).limit(page_size).all()

        results = []
        for a, dispatch_at, returned_at in assets:
            # Calculate standing & days outstanding
            standing = LifecycleService.classify_asset_standing(
                status=a.asset_status,
                dispatch_date=dispatch_at if dispatch_at and (not returned_at or dispatch_at > returned_at) else None,
                reference_date=reference_date,
                return_due_days=a.asset_type.return_due_days if a.asset_type else 30,
                loss_threshold_days=a.asset_type.loss_threshold_days if a.asset_type else 60
            )


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

    @classmethod
    @atomic_operation
    def create_asset(
        cls,
        db: Session,
        payload_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Registers a new reusable asset in the database.
        Validates references, generates sequential ASSET-XXXXXXX ID,
        creates initial CustodyEvent, and returns comprehensive asset detail.
        """
        # 1. Validate Asset Type
        asset_type = None
        if payload_data.get("asset_type_id"):
            asset_type = db.query(AssetType).filter(AssetType.asset_type_id == payload_data["asset_type_id"]).first()
        elif payload_data.get("asset_type_code"):
            asset_type = db.query(AssetType).filter(AssetType.type_code == payload_data["asset_type_code"]).first()
        
        if not asset_type:
            raise ValueError("Valid Asset Type is required.")

        # 2. Validate Owner
        owner_id = payload_data.get("owner_id")
        if not owner_id:
            raise ValueError("Owner is required.")
        owner = db.query(Owner).filter(Owner.owner_id == owner_id).first()
        if not owner:
            raise ValueError(f"Owner with ID {owner_id} does not exist.")

        # 3. Validate Location
        location_id = payload_data.get("current_location_id")
        if not location_id:
            raise ValueError("Current Location is required.")
        location = db.query(Location).filter(Location.location_id == location_id).first()
        if not location:
            raise ValueError(f"Location with ID {location_id} does not exist.")

        # 4. Validate Deposit Amount
        deposit_val = payload_data.get("deposit_amount")
        if deposit_val is None:
            deposit_val = asset_type.default_deposit_amount
        try:
            deposit_amount = Decimal(str(deposit_val))
        except Exception:
            raise ValueError("Deposit amount must be a valid number.")

        if deposit_amount <= 0:
            raise ValueError("Deposit amount must be strictly greater than 0.")

        # 5. Purchase and Manufacture Dates
        p_date = payload_data.get("purchase_date")
        if isinstance(p_date, str):
            p_date = date.fromisoformat(p_date)
        elif not p_date:
            p_date = date.today()

        m_date = payload_data.get("manufacture_date")
        if isinstance(m_date, str):
            m_date = date.fromisoformat(m_date)
        elif not m_date:
            m_date = p_date

        # Acquisition cost
        acq_val = payload_data.get("acquisition_cost")
        if acq_val is not None:
            acquisition_cost = Decimal(str(acq_val))
        else:
            acquisition_cost = Decimal(str(asset_type.default_deposit_amount * Decimal("2.0")))

        # 6. Generate sequential unique Asset ID following ASSET-XXXXXXX convention
        new_asset_id = payload_data.get("asset_id") or PersistentIDGenerator.next_asset_id(db)

        # 7. Serial number
        serial = payload_data.get("serial_number")
        if serial:
            serial = serial.strip()
            existing_sn = db.query(ReusableAsset).filter(ReusableAsset.serial_number == serial).first()
            if existing_sn:
                raise ValueError(f"Serial number '{serial}' is already registered.")
        else:
            serial = f"SN-{asset_type.type_code}-{new_asset_id.replace('ASSET-', '')}"
            # Ensure uniqueness
            s_idx = 1
            base_serial = serial
            while db.query(ReusableAsset).filter(ReusableAsset.serial_number == serial).first():
                serial = f"{base_serial}-{s_idx}"
                s_idx += 1

        initial_status = payload_data.get("asset_status") or "AVAILABLE"
        if initial_status != "AVAILABLE":
            raise ValueError("New assets must be commissioned as AVAILABLE")
        now_dt = datetime.now(timezone.utc)
        commission_ts = datetime.combine(p_date, datetime.min.time().replace(hour=8, minute=30))

        # 8. Create ReusableAsset record
        new_asset = ReusableAsset(
            asset_id=new_asset_id,
            asset_type_id=asset_type.asset_type_id,
            owner_id=owner.owner_id,
            serial_number=serial,
            asset_status=initial_status,
            manufacture_date=m_date,
            purchase_date=p_date,
            current_location_id=location.location_id,
            current_custodian_owner_id=owner.owner_id,
            acquisition_cost=acquisition_cost,
            deposit_amount=deposit_amount,
            last_event_at=commission_ts,
            created_at=now_dt,
            updated_at=now_dt
        )
        db.add(new_asset)
        db.flush()

        # 9. Create initial CustodyEvent
        notes = payload_data.get("notes") or "Internal asset provisioning and initial commissioning."
        cust_event = CustodyEvent(
            custody_event_id=f"CUST-{new_asset_id}-000001",
            asset_id=new_asset_id,
            shipment_id=None,
            from_owner_id=None,
            to_owner_id=owner.owner_id,
            from_location_id=None,
            to_location_id=location.location_id,
            actor_owner_id=owner.owner_id,
            event_type="COMMISSIONED",
            event_timestamp=commission_ts,
            event_reference="INITIAL-REGISTRATION",
            notes=f"Commissioned at {location.location_name} by {owner.owner_name}. {notes}",
            created_at=now_dt
        )
        db.add(cust_event)
        db.flush()
        db.refresh(new_asset)

        return {
            "asset_id": new_asset.asset_id,
            "serial_number": new_asset.serial_number,
            "type_code": asset_type.type_code,
            "type_name": asset_type.type_name,
            "owner_id": owner.owner_id,
            "owner_name": owner.owner_name,
            "current_location_id": location.location_id,
            "current_location_name": location.location_name,
            "asset_status": new_asset.asset_status,
            "deposit_amount": float(new_asset.deposit_amount),
            "acquisition_cost": float(new_asset.acquisition_cost),
            "purchase_date": str(new_asset.purchase_date),
            "created_at": new_asset.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
