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
        disp_dt = dispatch_date or utc_now()
        exp_dt = expected_delivery_date or (disp_dt + timedelta(days=3))
        if disp_dt > exp_dt:
            raise ValueError("Dispatch date cannot be later than expected delivery date.")
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

        for a_id in asset_ids:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == a_id).first()
            if not asset:
                raise ValueError(f"Asset {a_id} does not exist.")

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

            # Record immutable CustodyEvent for dispatch
            ce_id = PersistentIDGenerator.next_custody_event_id(db, a_id)
            cust_event = CustodyEvent(
                custody_event_id=ce_id,
                asset_id=a_id,
                shipment_id=shipment_id,
                from_owner_id=asset.current_custodian_owner_id or asset.owner_id,
                to_owner_id=carrier_owner_id,
                from_location_id=origin_location_id,
                to_location_id=None,
                actor_owner_id=carrier_owner_id,
                event_type="DISPATCHED",
                event_timestamp=disp_dt,
                event_reference=f"DISPATCH-{shipment_id}",
                notes=f"Dispatched via shipment {shipment_id} from location {origin_location_id} to carrier {carrier_owner_id}",
                created_at=utc_now()
            )
            db.add(cust_event)

            # Update asset status & location
            asset.asset_status = "IN_TRANSIT"
            asset.current_location_id = None
            asset.current_custodian_owner_id = carrier_owner_id
            asset.last_event_at = disp_dt
            asset.updated_at = utc_now()

        db.flush()
        return shipment

    @classmethod
    def deliver_shipment(
        cls,
        db: Session,
        shipment_id: str,
        actual_delivery_date: Optional[datetime] = None
    ) -> Shipment:
        shipment = db.query(Shipment).filter(Shipment.shipment_id == shipment_id).first()
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found.")

        deliv_dt = actual_delivery_date or utc_now()
        if deliv_dt < shipment.dispatch_date:
            raise ValueError("Delivery date cannot precede dispatch date.")

        shipment.shipment_status = "DELIVERED"
        shipment.actual_delivery_date = deliv_dt

        # Update assets to IN_CUSTODY at destination and log arrival event
        for sa in shipment.shipment_assets:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == sa.asset_id).first()
            if asset:
                if asset.asset_status == "RETIRED":
                    raise ValueError(f"Asset {asset.asset_id} is RETIRED.")
                valid, err = LifecycleService.validate_transition(asset.asset_status, "IN_CUSTODY")
                if not valid and asset.asset_status != "IN_TRANSIT":
                    raise ValueError(f"Invalid transition for asset {asset.asset_id} to IN_CUSTODY: {err}")

                # Record immutable CustodyEvent for delivery
                ce_id = PersistentIDGenerator.next_custody_event_id(db, asset.asset_id)
                dest_owner_id = asset.owner_id
                cust_event = CustodyEvent(
                    custody_event_id=ce_id,
                    asset_id=asset.asset_id,
                    shipment_id=shipment.shipment_id,
                    from_owner_id=shipment.carrier_owner_id,
                    to_owner_id=dest_owner_id,
                    from_location_id=None,
                    to_location_id=shipment.destination_location_id,
                    actor_owner_id=dest_owner_id or shipment.carrier_owner_id,
                    event_type="RECEIVED",
                    event_timestamp=deliv_dt,
                    event_reference=f"DELIVERY-{shipment.shipment_id}",
                    notes=f"Delivered via shipment {shipment.shipment_id} to location {shipment.destination_location_id}",
                    created_at=utc_now()
                )
                db.add(cust_event)

                asset.asset_status = "IN_CUSTODY"
                asset.current_location_id = shipment.destination_location_id
                asset.current_custodian_owner_id = dest_owner_id
                asset.last_event_at = deliv_dt
                asset.updated_at = utc_now()

        db.flush()
        return shipment
