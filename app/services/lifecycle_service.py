from datetime import date, datetime, timezone
from functools import wraps
from typing import Dict, Set, Optional, Tuple
from app.config import settings

class LifecycleService:
    """
    Manages and validates reusable asset lifecycle states and derived calculations.
    States:
      AVAILABLE, RESERVED, DISPATCHED, IN_TRANSIT, IN_CUSTODY,
      RETURN_PENDING, RETURNED, INSPECTION_PENDING, DAMAGED,
      UNDER_REPAIR, LOST, RETIRED
    """

    ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
        "AVAILABLE": {"RESERVED", "DISPATCHED", "RETIRED"},
        "RESERVED": {"DISPATCHED", "AVAILABLE"},
        "DISPATCHED": {"IN_TRANSIT", "LOST"},
        "IN_TRANSIT": {"IN_CUSTODY", "RETURNED", "LOST"},
        "IN_CUSTODY": {"RETURN_PENDING", "RETURNED", "LOST"},
        "RETURN_PENDING": {"IN_TRANSIT", "RETURNED", "LOST"},
        "RETURNED": {"INSPECTION_PENDING", "AVAILABLE"},
        "INSPECTION_PENDING": {"AVAILABLE", "DAMAGED", "RETIRED"},
        "DAMAGED": {"UNDER_REPAIR", "RETIRED"},
        "UNDER_REPAIR": {"INSPECTION_PENDING", "AVAILABLE", "RETIRED"},
        "LOST": {"INSPECTION_PENDING", "AVAILABLE"},  # Recovery transition
        "RETIRED": set(),
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status == to_status:
            return True
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, set())

    @classmethod
    def validate_transition(cls, from_status: str, to_status: str) -> Tuple[bool, Optional[str]]:
        if from_status == to_status:
            return True, None
        allowed = cls.ALLOWED_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            return False, f"Invalid lifecycle transition from {from_status} to {to_status}. Allowed: {sorted(list(allowed))}"
        return True, None

    @classmethod
    def calculate_outstanding_days(
        cls, 
        dispatch_datetime: Optional[datetime], 
        reference_date: Optional[date] = None
    ) -> int:
        if not dispatch_datetime:
            return 0
        ref_d = reference_date or settings.REFERENCE_DATE
        disp_d = utc_naive(dispatch_datetime).date() if isinstance(dispatch_datetime, datetime) else dispatch_datetime
        delta = (ref_d - disp_d).days
        return max(0, delta)

    @classmethod
    def classify_asset_standing(
        cls,
        status: str,
        dispatch_date: Optional[datetime],
        return_due_days: int = 30,
        loss_threshold_days: int = 60,
        reference_date: Optional[date] = None
    ) -> Dict[str, any]:
        """
        Calculates:
        - days_outstanding
        - is_outstanding: asset is actively dispatched/in-transit/in-custody/return-pending
        - is_overdue: days_outstanding > return_due_days and not returned
        - is_lost: days_outstanding > loss_threshold_days and not returned
        """
        ref_d = reference_date or settings.REFERENCE_DATE
        active_statuses = {"DISPATCHED", "IN_TRANSIT", "IN_CUSTODY", "RETURN_PENDING"}
        
        is_outstanding = status in active_statuses
        days_outstanding = 0
        if is_outstanding and dispatch_date:
            disp_d = utc_naive(dispatch_date).date() if isinstance(dispatch_date, datetime) else dispatch_date
            days_outstanding = max(0, (ref_d - disp_d).days)
        elif status == "LOST" and dispatch_date:
            disp_d = utc_naive(dispatch_date).date() if isinstance(dispatch_date, datetime) else dispatch_date
            days_outstanding = max(0, (ref_d - disp_d).days)

        is_overdue = is_outstanding and (days_outstanding > return_due_days)
        is_lost_candidate = (days_outstanding > loss_threshold_days) and (status != "RETURNED")

        return {
            "days_outstanding": days_outstanding,
            "is_outstanding": is_outstanding,
            "is_overdue": is_overdue,
            "is_lost_candidate": is_lost_candidate,
            "current_status": status
        }

    @staticmethod
    def dispatch_subquery(db):
        from sqlalchemy import func, case
        from app.models.custody_event import CustodyEvent
        return db.query(CustodyEvent.asset_id.label("asset_id"),
            func.max(case((CustodyEvent.event_type == "DISPATCHED", CustodyEvent.event_timestamp))).label("dispatch_at"),
            func.max(case((CustodyEvent.event_type == "RETURNED", CustodyEvent.event_timestamp))).label("returned_at")
        ).group_by(CustodyEvent.asset_id).subquery()

    @classmethod
    def active_dispatch(cls, db, asset_id):
        from sqlalchemy import func
        from app.models.custody_event import CustodyEvent
        dispatch = db.query(func.max(CustodyEvent.event_timestamp)).filter_by(asset_id=asset_id, event_type="DISPATCHED").scalar()
        returned = db.query(func.max(CustodyEvent.event_timestamp)).filter_by(asset_id=asset_id, event_type="RETURNED").scalar()
        return dispatch if dispatch and (not returned or dispatch > returned) else None

    @classmethod
    def standing_for_asset(cls, db, asset, reference_date=None):
        return cls.classify_asset_standing(asset.asset_status, cls.active_dispatch(db, asset.asset_id),
            asset.asset_type.return_due_days, asset.asset_type.loss_threshold_days, reference_date)

    @staticmethod
    def age_sql(dispatch_column, reference_date, dialect):
        from sqlalchemy import func, literal, cast, Integer
        if dialect == "sqlite":
            return func.max(0, cast(func.julianday(str(reference_date)) - func.julianday(func.date(dispatch_column)), Integer))
        if dialect == "postgresql":
            from sqlalchemy import Date
            return func.greatest(0, cast(literal(reference_date), Date) - cast(dispatch_column, Date))
        return func.greatest(0, func.datediff(reference_date, dispatch_column))


# A service failure rolls back its own writes even when the caller catches it.
# Outer commit remains the caller's responsibility.
def atomic_operation(method):
    @wraps(method)
    def wrapped(cls, db, *args, **kwargs):
        with db.begin_nested():
            return method(cls, db, *args, **kwargs)
    return wrapped


def utc_naive(value):
    if value is None:
        return None
    val = value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value
    return val.replace(microsecond=0)


def record_transition(db, asset, event_type, timestamp, actor_id, *, location=None,
                      custodian=None, physical=False, reference=None, shipment_id=None, notes=None):
    """Validate and append a domain fact and its projection in one transaction.

    Non-physical events preserve location/custodian; physical nulls clear them.
    No commits here. The caller owns its transaction/savepoint.
    """
    from app.models.custody_event import CustodyEvent
    from app.utils.id_generator import PersistentIDGenerator
    paths = {
        "DISPATCHED": ("DISPATCHED", "IN_TRANSIT"),
        "RECEIVED": ("IN_CUSTODY",), "TRANSFERRED": ("IN_CUSTODY",),
        "RETURN_REQUESTED": ("RETURN_PENDING",),
        "RETURNED": ("RETURNED", "INSPECTION_PENDING"),
        "INSPECTED_GOOD": ("AVAILABLE",), "INSPECTED_DAMAGED": ("DAMAGED",),
        "INSPECTED_UNUSABLE": ("RETIRED",), "REPAIR_STARTED": ("UNDER_REPAIR",),
        "REPAIR_COMPLETED": ("INSPECTION_PENDING",), "LOST_REPORTED": ("LOST",),
        "RETIRED": ("RETIRED",), "RECOVERED": ("INSPECTION_PENDING",),
    }
    if event_type not in paths:
        raise ValueError("Unsupported live lifecycle event")
    target = asset.asset_status
    for state in paths[event_type]:
        valid, err = LifecycleService.validate_transition(target, state)
        if not valid:
            raise ValueError(err)
        target = state
    if target == asset.asset_status and not (event_type == "TRANSFERRED" and physical and (location != asset.current_location_id or custodian != asset.current_custodian_owner_id)):
        raise ValueError("Duplicate lifecycle transition")
    when = utc_naive(timestamp)
    if asset.last_event_at and when < utc_naive(asset.last_event_at):
        raise ValueError("Event timestamp precedes the current projection")
    evt = CustodyEvent(
        custody_event_id=PersistentIDGenerator.next_custody_event_id(db, asset.asset_id),
        asset_id=asset.asset_id, event_type=event_type, event_timestamp=when,
        actor_owner_id=actor_id, event_reference=reference, shipment_id=shipment_id,
        from_location_id=asset.current_location_id,
        to_location_id=location if physical else asset.current_location_id,
        from_owner_id=asset.current_custodian_owner_id,
        to_owner_id=custodian if physical else asset.current_custodian_owner_id,
        notes=notes,
    )
    db.add(evt)
    asset.asset_status = target
    if physical:
        asset.current_location_id = location
        asset.current_custodian_owner_id = custodian
    asset.last_event_at = when
    asset.updated_at = datetime.now(timezone.utc)
    db.flush()
    return evt
