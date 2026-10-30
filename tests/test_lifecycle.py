from datetime import date, datetime, timedelta, timezone
from app.services.lifecycle_service import LifecycleService

def test_lifecycle_allowed_transitions():
    # Valid transitions
    assert LifecycleService.can_transition("AVAILABLE", "DISPATCHED")
    assert LifecycleService.can_transition("DISPATCHED", "IN_TRANSIT")
    assert LifecycleService.can_transition("IN_TRANSIT", "IN_CUSTODY")
    assert LifecycleService.can_transition("IN_CUSTODY", "RETURN_PENDING")
    assert LifecycleService.can_transition("RETURN_PENDING", "RETURNED")
    assert LifecycleService.can_transition("RETURNED", "INSPECTION_PENDING")
    assert LifecycleService.can_transition("INSPECTION_PENDING", "AVAILABLE")
    assert LifecycleService.can_transition("INSPECTION_PENDING", "DAMAGED")
    assert LifecycleService.can_transition("DAMAGED", "UNDER_REPAIR")
    assert LifecycleService.can_transition("UNDER_REPAIR", "INSPECTION_PENDING")
    assert LifecycleService.can_transition("LOST", "AVAILABLE")  # Recovery

    # Invalid transitions
    assert not LifecycleService.can_transition("AVAILABLE", "RETURNED")
    assert not LifecycleService.can_transition("AVAILABLE", "DAMAGED")
    assert not LifecycleService.can_transition("DAMAGED", "AVAILABLE")  # Must be repaired first

def test_outstanding_age_and_overdue():
    ref_date = date(2026, 10, 22)
    
    # 10 days outstanding -> Not overdue for 30-day limit
    disp_10d = datetime(2026, 10, 12, tzinfo=timezone.utc)
    res_10d = LifecycleService.classify_asset_standing(
        status="IN_CUSTODY",
        dispatch_date=disp_10d,
        return_due_days=30,
        loss_threshold_days=60,
        reference_date=ref_date
    )
    assert res_10d["days_outstanding"] == 10
    assert not res_10d["is_overdue"]
    assert not res_10d["is_lost_candidate"]

    # 40 days outstanding -> Overdue
    disp_40d = datetime(2026, 9, 12, tzinfo=timezone.utc)
    res_40d = LifecycleService.classify_asset_standing(
        status="IN_CUSTODY",
        dispatch_date=disp_40d,
        return_due_days=30,
        loss_threshold_days=60,
        reference_date=ref_date
    )
    assert res_40d["days_outstanding"] == 40
    assert res_40d["is_overdue"]
    assert not res_40d["is_lost_candidate"]

    # 70 days outstanding -> Lost candidate
    disp_70d = datetime(2026, 8, 13, tzinfo=timezone.utc)
    res_70d = LifecycleService.classify_asset_standing(
        status="IN_CUSTODY",
        dispatch_date=disp_70d,
        return_due_days=30,
        loss_threshold_days=60,
        reference_date=ref_date
    )
    assert res_70d["days_outstanding"] == 70
    assert res_70d["is_overdue"]
    assert res_70d["is_lost_candidate"]
