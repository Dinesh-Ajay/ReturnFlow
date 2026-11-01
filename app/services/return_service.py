from app.services.lifecycle_service import atomic_operation, record_transition, utc_naive
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.return_authorization import ReturnAuthorization
from app.models.return_authorization_asset import ReturnAuthorizationAsset
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.services.lifecycle_service import LifecycleService
from app.utils.id_generator import IDGenerator, PersistentIDGenerator

def utc_now():
    return datetime.now(timezone.utc)

class ReturnService:
    """
    Manages Return Authorizations (RMAs) and return processing.
    """

    @classmethod
    @atomic_operation
    def create_rma(
        cls,
        db: Session,
        requesting_owner_id: int,
        receiving_owner_id: int,
        return_location_id: int,
        requested_date: Optional[datetime] = None,
        expected_return_date: Optional[datetime] = None,
        asset_ids: Optional[List[str]] = None,
        reason: Optional[str] = None,
        custom_id: Optional[str] = None
    ) -> ReturnAuthorization:
        req_dt = utc_naive(requested_date or utc_now())
        exp_dt = utc_naive(expected_return_date) or (req_dt + timedelta(days=7))
        if req_dt > exp_dt:
            raise ValueError("Requested date cannot be later than expected return date.")
        if asset_ids and len(set(asset_ids)) != len(asset_ids):
            raise ValueError("Duplicate asset in manifest")
        if not asset_ids:
            raise ValueError("RMA must contain at least one asset.")

        yr = req_dt.year if req_dt else 2026
        rma_id = custom_id or PersistentIDGenerator.next_rma_id(db, year=yr)

        rma = ReturnAuthorization(
            rma_id=rma_id,
            requesting_owner_id=requesting_owner_id,
            receiving_owner_id=receiving_owner_id,
            return_location_id=return_location_id,
            requested_date=req_dt,
            approved_date=req_dt,
            expected_return_date=exp_dt,
            rma_status="APPROVED",
            reason=reason or "Scheduled reusable asset return"
        )
        db.add(rma)
        db.flush()

        for a_id in sorted(set(asset_ids)):
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == a_id).with_for_update().populate_existing().first()
            if not asset:
                raise ValueError(f"Asset {a_id} does not exist.")

            if asset.asset_status != "IN_CUSTODY":
                raise ValueError(f"Asset {a_id} in {asset.asset_status} is not eligible for return")

            link = ReturnAuthorizationAsset(
                rma_id=rma_id,
                asset_id=a_id
            )
            db.add(link)

            record_transition(db, asset, "RETURN_REQUESTED", req_dt, requesting_owner_id,
                              reference=rma_id)

        db.flush()
        return rma

    @classmethod
    @atomic_operation
    def receive_return(
        cls,
        db: Session,
        rma_id: str,
        actual_return_date: Optional[datetime] = None,
        default_condition: str = "GOOD"
    ) -> ReturnAuthorization:
        rma = db.query(ReturnAuthorization).filter(ReturnAuthorization.rma_id == rma_id).with_for_update().populate_existing().first()
        if not rma:
            raise ValueError(f"RMA {rma_id} not found.")

        if rma.rma_status != "APPROVED":
            raise ValueError("RMA is not awaiting receipt")
        ret_dt = utc_naive(actual_return_date or utc_now())
        if ret_dt < rma.requested_date:
            raise ValueError("Actual return date cannot precede requested date.")

        rma.rma_status = "RECEIVED"
        rma.actual_return_date = ret_dt

        # Update assets to RETURNED at receiving return_location and log return event
        for raa in rma.rma_assets:
            raa.received_at = ret_dt
            raa.return_condition = default_condition
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == raa.asset_id).with_for_update().populate_existing().first()
            if asset:
                record_transition(db, asset, "RETURNED", ret_dt, rma.receiving_owner_id,
                                  physical=True, location=rma.return_location_id,
                                  custodian=rma.receiving_owner_id, reference=rma.rma_id)

        db.flush()
        return rma
