from app.services.lifecycle_service import atomic_operation, record_transition, utc_naive
from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.shipment import Shipment
from app.models.shipment_asset import ShipmentAsset
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.services.lifecycle_service import LifecycleService
from app.utils.id_generator import IDGenerator, PersistentIDGenerator

def utc_now():
    return datetime.now(timezone.utc)

class ShipmentService:
    """
    Manages shipments, asset assignment, dispatch, and delivery.
    """

    @classmethod
    @atomic_operation
    def create_shipment(
        cls,
        db: Session,
        origin_location_id: int,
        destination_location_id: int,
        carrier_owner_id: int,
        dispatch_date: Optional[datetime] = None,
        expected_delivery_date: Optional[datetime] = None,
        asset_ids: Optional[List[str]] = None,
        tracking_reference: Optional[str] = None,
        custom_id: Optional[str] = None
    ) -> Shipment:
        disp_dt = utc_naive(dispatch_date or utc_now())
        exp_dt = utc_naive(expected_delivery_date) or (disp_dt + timedelta(days=3))
        if disp_dt > exp_dt:
            raise ValueError("Dispatch date cannot be later than expected delivery date.")
        if asset_ids and len(set(asset_ids)) != len(asset_ids):
            raise ValueError("Duplicate asset in manifest")
        if not asset_ids:
            raise ValueError("Shipment must contain at least one asset.")

        yr = disp_dt.year if disp_dt else 2026
        shipment_id = custom_id or PersistentIDGenerator.next_shipment_id(db, year=yr)

        shipment = Shipment(
            shipment_id=shipment_id,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            carrier_owner_id=carrier_owner_id,
            dispatch_date=disp_dt,
            expected_delivery_date=exp_dt,
            shipment_status="DISPATCHED",
            tracking_reference=tracking_reference or f"TRK-{shipment_id}"
        )
        db.add(shipment)
        db.flush()

        for a_id in sorted(set(asset_ids)):
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == a_id).with_for_update().populate_existing().first()
            if not asset:
                raise ValueError(f"Asset {a_id} does not exist.")

            if asset.current_location_id != origin_location_id and asset.asset_status in ("AVAILABLE", "RESERVED"):
                raise ValueError("Dispatch origin must match the current asset location")

            # Validate lifecycle eligibility
            if asset.asset_status == "RETIRED":
                raise ValueError(f"Asset {a_id} is RETIRED and cannot be dispatched.")
            if asset.asset_status == "LOST":
                raise ValueError(f"Asset {a_id} is LOST and cannot be dispatched without prior recovery.")
            if asset.asset_status in ("IN_TRANSIT", "DISPATCHED"):
                raise ValueError(f"Asset {a_id} is currently in transit / dispatched and cannot be dispatched again.")
            if asset.asset_status not in ("AVAILABLE", "RESERVED"):
                valid, err = LifecycleService.validate_transition(asset.asset_status, "DISPATCHED")
                if not valid:
                    raise ValueError(f"Asset {a_id} in status '{asset.asset_status}' is not eligible for dispatch: {err}")

            link = ShipmentAsset(
                shipment_id=shipment_id,
                asset_id=a_id,
                assigned_at=disp_dt
            )
            db.add(link)

            record_transition(db, asset, "DISPATCHED", disp_dt, carrier_owner_id,
                              physical=True, location=None, custodian=carrier_owner_id,
                              shipment_id=shipment_id, reference=shipment_id)

        db.flush()
        return shipment

    @classmethod
    @atomic_operation
    def deliver_shipment(
        cls,
        db: Session,
        shipment_id: str,
        actual_delivery_date: Optional[datetime] = None,
        receiving_owner_id: Optional[int] = None
    ) -> Shipment:
        shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).with_for_update().populate_existing().first()
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found.")

        if shipment.shipment_status == "DELIVERED":
            raise ValueError("Shipment already delivered")
        deliv_dt = utc_naive(actual_delivery_date or utc_now())
        if deliv_dt < shipment.dispatch_date:
            raise ValueError("Delivery date cannot precede dispatch date.")

        shipment.shipment_status = "DELIVERED"
        shipment.actual_delivery_date = deliv_dt

        # Update assets to IN_CUSTODY at destination and log arrival event
        for sa in shipment.shipment_assets:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == sa.asset_id).with_for_update().populate_existing().first()
            if asset:
                if asset.asset_status == "RETIRED":
                    raise ValueError(f"Asset {asset.asset_id} is RETIRED.")
                valid, err = LifecycleService.validate_transition(asset.asset_status, "IN_CUSTODY")
                if not valid and asset.asset_status != "IN_TRANSIT":
                    raise ValueError(f"Invalid transition for asset {asset.asset_id} to IN_CUSTODY: {err}")

                record_transition(db, asset, "RECEIVED", deliv_dt, receiving_owner_id or asset.owner_id,
                                  physical=True, location=shipment.destination_location_id,
                                  custodian=receiving_owner_id or asset.owner_id, shipment_id=shipment.shipment_id,
                                  reference=shipment.shipment_id)

        db.flush()
        return shipment
