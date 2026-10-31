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
        req_dt = requested_date or utc_now()
        exp_dt = expected_return_date or (req_dt + timedelta(days=7))
        if req_dt > exp_dt:
            raise ValueError("Requested date cannot be later than expected return date.")
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

        for a_id in asset_ids:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == a_id).first()
            if not asset:
                raise ValueError(f"Asset {a_id} does not exist.")

            # Validate lifecycle eligibility
            if asset.asset_status == "RETIRED":
                raise ValueError(f"Asset {a_id} is RETIRED and cannot be returned.")
            if asset.asset_status == "LOST":
                raise ValueError(f"Asset {a_id} is LOST and cannot be returned without recovery.")
            if asset.asset_status not in ("IN_CUSTODY", "AVAILABLE", "DISPATCHED", "RETURN_PENDING"):
                valid, err = LifecycleService.validate_transition(asset.asset_status, "RETURN_PENDING")
                if not valid:
                    raise ValueError(f"Asset {a_id} in status '{asset.asset_status}' is not eligible for RMA: {err}")

            link = ReturnAuthorizationAsset(
                rma_id=rma_id,
                asset_id=a_id
            )
            db.add(link)

            # Update asset status
            asset.asset_status = "RETURN_PENDING"
            asset.updated_at = utc_now()

        db.flush()
        return rma

    @classmethod
    def receive_return(
        cls,
        db: Session,
        rma_id: str,
        actual_return_date: Optional[datetime] = None,
        default_condition: str = "GOOD"
    ) -> ReturnAuthorization:
        rma = db.query(ReturnAuthorization).filter(ReturnAuthorization.rma_id == rma_id).first()
        if not rma:
            raise ValueError(f"RMA {rma_id} not found.")

        ret_dt = actual_return_date or utc_now()
        if ret_dt < rma.requested_date:
            raise ValueError("Actual return date cannot precede requested date.")

        rma.rma_status = "RECEIVED"
        rma.actual_return_date = ret_dt

        # Update assets to RETURNED at receiving return_location and log return event
        for raa in rma.rma_assets:
            raa.received_at = ret_dt
            raa.return_condition = default_condition
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == raa.asset_id).first()
            if asset:
                if asset.asset_status == "RETIRED":
                    raise ValueError(f"Asset {asset.asset_id} is RETIRED and cannot be received.")

                # Record immutable CustodyEvent for return receipt
                ce_id = PersistentIDGenerator.next_custody_event_id(db, asset.asset_id)
                cust_event = CustodyEvent(
                    custody_event_id=ce_id,
                    asset_id=asset.asset_id,
                    shipment_id=None,
                    from_owner_id=rma.requesting_owner_id,
                    to_owner_id=rma.receiving_owner_id,
                    from_location_id=None,
                    to_location_id=rma.return_location_id,
                    actor_owner_id=rma.receiving_owner_id,
                    event_type="RETURNED",
                    event_timestamp=ret_dt,
                    event_reference=f"RMA-{rma.rma_id}",
                    notes=f"Returned under RMA {rma.rma_id} to facility {rma.return_location_id}",
                    created_at=utc_now()
                )
                db.add(cust_event)

                asset.asset_status = "INSPECTION_PENDING"
                asset.current_location_id = rma.return_location_id
                asset.current_custodian_owner_id = rma.receiving_owner_id
                asset.last_event_at = ret_dt
                asset.updated_at = utc_now()

        db.flush()
        return rma
