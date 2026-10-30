from datetime import date, datetime
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
        disp_d = dispatch_datetime.date() if isinstance(dispatch_datetime, datetime) else dispatch_datetime
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
            disp_d = dispatch_date.date() if isinstance(dispatch_date, datetime) else dispatch_date
            days_outstanding = max(0, (ref_d - disp_d).days)
        elif status == "LOST" and dispatch_date:
            disp_d = dispatch_date.date() if isinstance(dispatch_date, datetime) else dispatch_date
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
