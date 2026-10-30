from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.return_authorization import ReturnAuthorization
from app.models.return_authorization_asset import ReturnAuthorizationAsset
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.utils.id_generator import IDGenerator

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
        requested_date: datetime,
        expected_return_date: datetime,
        asset_ids: List[str],
        reason: Optional[str] = None,
        custom_id: Optional[str] = None
    ) -> ReturnAuthorization:
        if requested_date > expected_return_date:
            raise ValueError("Requested date cannot be later than expected return date.")
        if not asset_ids:
            raise ValueError("RMA must contain at least one asset.")

        rma_id = custom_id or IDGenerator(year=2026).next_rma_id()

        rma = ReturnAuthorization(
            rma_id=rma_id,
            requesting_owner_id=requesting_owner_id,
            receiving_owner_id=receiving_owner_id,
            return_location_id=return_location_id,
            requested_date=requested_date,
            approved_date=requested_date,
            expected_return_date=expected_return_date,
            rma_status="APPROVED",
            reason=reason or "Scheduled reusable asset return"
        )
        db.add(rma)
        db.flush()

        for a_id in asset_ids:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == a_id).first()
            if not asset:
                raise ValueError(f"Asset {a_id} does not exist.")

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

        # Update assets to RETURNED at receiving return_location
        for raa in rma.rma_assets:
            raa.received_at = ret_dt
            raa.return_condition = default_condition
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == raa.asset_id).first()
            if asset:
                asset.asset_status = "INSPECTION_PENDING"
                asset.current_location_id = rma.return_location_id
                asset.current_custodian_owner_id = rma.receiving_owner_id
                asset.last_event_at = ret_dt
                asset.updated_at = utc_now()

        db.flush()
        return rma
