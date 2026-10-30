from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.shipment import Shipment
from app.models.shipment_asset import ShipmentAsset
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.utils.id_generator import IDGenerator

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
        dispatch_date: datetime,
        expected_delivery_date: datetime,
        asset_ids: List[str],
        tracking_reference: Optional[str] = None,
        custom_id: Optional[str] = None
    ) -> Shipment:
        if dispatch_date > expected_delivery_date:
            raise ValueError("Dispatch date cannot be later than expected delivery date.")
        if not asset_ids:
            raise ValueError("Shipment must contain at least one asset.")

        shipment_id = custom_id or IDGenerator(year=2026).next_shipment_id()

        shipment = Shipment(
            shipment_id=shipment_id,
            origin_location_id=origin_location_id,
            destination_location_id=destination_location_id,
            carrier_owner_id=carrier_owner_id,
            dispatch_date=dispatch_date,
            expected_delivery_date=expected_delivery_date,
            shipment_status="DISPATCHED",
            tracking_reference=tracking_reference or f"TRK-{shipment_id}"
        )
        db.add(shipment)
        db.flush()

        for a_id in asset_ids:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == a_id).first()
            if not asset:
                raise ValueError(f"Asset {a_id} does not exist.")

            link = ShipmentAsset(
                shipment_id=shipment_id,
                asset_id=a_id,
                assigned_at=dispatch_date
            )
            db.add(link)

            # Update asset status & location
            asset.asset_status = "IN_TRANSIT"
            asset.current_custodian_owner_id = carrier_owner_id
            asset.last_event_at = dispatch_date
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

        # Update assets to IN_CUSTODY at destination
        for sa in shipment.shipment_assets:
            asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == sa.asset_id).first()
            if asset:
                asset.asset_status = "IN_CUSTODY"
                asset.current_location_id = shipment.destination_location_id
                asset.last_event_at = deliv_dt
                asset.updated_at = utc_now()

        db.flush()
        return shipment
