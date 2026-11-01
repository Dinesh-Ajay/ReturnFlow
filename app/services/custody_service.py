from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.models.shipment import Shipment
from app.models.shipment_asset import ShipmentAsset
from app.models.return_authorization import ReturnAuthorization
from app.models.return_authorization_asset import ReturnAuthorizationAsset
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.deposit_ledger import DepositLedger
from app.services.lifecycle_service import LifecycleService
from app.config import settings

class CustodyService:
    """
    Coordinates and reconstructs asset custody history, event timelines,
    and validates historical integrity.
    """

    @classmethod
    def get_asset_full_traceability(cls, db: Session, asset_id: str) -> Optional[Dict[str, Any]]:
        asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == asset_id).first()
        if not asset:
            return None

        # 1. Custody Events ordered chronologically
        events = db.query(CustodyEvent).filter(
            CustodyEvent.asset_id == asset_id
        ).order_by(CustodyEvent.event_timestamp.asc(), CustodyEvent.custody_event_id.asc()).all()

        # 2. Shipments associated with this asset
        shipment_links = db.query(ShipmentAsset).filter(ShipmentAsset.asset_id == asset_id).all()
        shipment_ids = [sl.shipment_id for sl in shipment_links]
        shipments = db.query(Shipment).filter(
            Shipment.shipment_id.in_(shipment_ids)
        ).order_by(Shipment.dispatch_date.desc()).all() if shipment_ids else []

        # 3. Return Authorizations (RMAs)
        rma_links = db.query(ReturnAuthorizationAsset).filter(ReturnAuthorizationAsset.asset_id == asset_id).all()
        rma_ids = [rl.rma_id for rl in rma_links]
        rmas = db.query(ReturnAuthorization).filter(
            ReturnAuthorization.rma_id.in_(rma_ids)
        ).order_by(ReturnAuthorization.requested_date.desc()).all() if rma_ids else []

        # 4. Inspections
        inspections = db.query(Inspection).filter(
            Inspection.asset_id == asset_id
        ).order_by(Inspection.inspection_date.asc()).all()

        # 5. Repairs
        repairs = db.query(Repair).filter(
            Repair.asset_id == asset_id
        ).order_by(Repair.repair_start_date.asc()).all()

        # 6. Financial Ledger
        ledger_entries = db.query(DepositLedger).filter(
            DepositLedger.asset_id == asset_id
        ).order_by(DepositLedger.transaction_date.asc()).all()

        standing = LifecycleService.standing_for_asset(db, asset)

        return {
            "asset_id": asset.asset_id,
            "serial_number": asset.serial_number,
            "type_code": asset.asset_type.type_code if asset.asset_type else None,
            "type_name": asset.asset_type.type_name if asset.asset_type else None,
            "owner_id": asset.owner_id,
            "owner_name": asset.owner.owner_name if asset.owner else None,
            "asset_status": asset.asset_status,
            "current_location_id": asset.current_location_id,
            "current_location_name": asset.current_location.location_name if asset.current_location else None,
            "current_custodian_id": asset.current_custodian_owner_id,
            "current_custodian_name": asset.current_custodian.owner_name if asset.current_custodian else None,
            "purchase_date": str(asset.purchase_date),
            "acquisition_cost": float(asset.acquisition_cost),
            "deposit_amount": float(asset.deposit_amount),
            "last_event_at": asset.last_event_at.isoformat() if asset.last_event_at else None,
            "days_outstanding": standing["days_outstanding"],
            "is_overdue": standing["is_overdue"],
            "is_lost_candidate": standing["is_lost_candidate"],
            "events_count": len(events),
            "events": [
                {
                    "custody_event_id": e.custody_event_id,
                    "asset_id": e.asset_id,
                    "event_type": e.event_type,
                    "event_timestamp": e.event_timestamp.isoformat(),
                    "from_owner_id": e.from_owner_id,
                    "to_owner_id": e.to_owner_id,
                    "from_location_id": e.from_location_id,
                    "to_location_id": e.to_location_id,
                    "actor_owner_id": e.actor_owner_id,
                    "actor_owner_name": e.actor_owner.owner_name if e.actor_owner else "MISSING_ACTOR",
                    "from_location_name": e.from_location.location_name if e.from_location else None,
                    "to_location_name": e.to_location.location_name if e.to_location else None,
                    "shipment_id": e.shipment_id,
                    "notes": e.notes,
                    "event_reference": e.event_reference,
                }
                for e in events
            ],
            "shipments": [
                {
                    "shipment_id": s.shipment_id,
                    "origin_location_id": s.origin_location_id,
                    "origin_location_name": s.origin_location.location_name if s.origin_location else None,
                    "destination_location_id": s.destination_location_id,
                    "destination_location_name": s.destination_location.location_name if s.destination_location else None,
                    "carrier_owner_id": s.carrier_owner_id,
                    "carrier_name": s.carrier.owner_name if s.carrier else None,
                    "dispatch_date": s.dispatch_date.isoformat(),
                    "expected_delivery_date": s.expected_delivery_date.isoformat(),
                    "actual_delivery_date": s.actual_delivery_date.isoformat() if s.actual_delivery_date else None,
                    "shipment_status": s.shipment_status,
                    "tracking_reference": s.tracking_reference,
                }
                for s in shipments
            ],
            "return_authorizations": [
                {
                    "rma_id": r.rma_id,
                    "requesting_owner_id": r.requesting_owner_id,
                    "requesting_owner_name": r.requesting_owner.owner_name if r.requesting_owner else None,
                    "receiving_owner_id": r.receiving_owner_id,
                    "return_location_id": r.return_location_id,
                    "requested_date": r.requested_date.isoformat(),
                    "expected_return_date": r.expected_return_date.isoformat(),
                    "actual_return_date": r.actual_return_date.isoformat() if r.actual_return_date else None,
                    "rma_status": r.rma_status,
                    "reason": r.reason,
                }
                for r in rmas
            ],
            "inspections": [
                {
                    "inspection_id": i.inspection_id,
                    "rma_id": i.rma_id,
                    "inspector_owner_id": i.inspector_owner_id,
                    "inspector_name": i.inspector.owner_name if i.inspector else None,
                    "inspection_date": i.inspection_date.isoformat(),
                    "condition_status": i.condition_status,
                    "damage_severity": i.damage_severity,
                    "requires_repair": i.requires_repair,
                    "notes": i.inspection_notes,
                }
                for i in inspections
            ],
            "repairs": [
                {
                    "repair_id": rep.repair_id,
                    "inspection_id": rep.inspection_id,
                    "repair_location_id": rep.repair_location_id,
                    "repair_location_name": rep.repair_location.location_name if rep.repair_location else None,
                    "repair_status": rep.repair_status,
                    "repair_start_date": rep.repair_start_date.isoformat(),
                    "repair_completion_date": rep.repair_completion_date.isoformat() if rep.repair_completion_date else None,
                    "repair_cost": float(rep.repair_cost),
                    "repair_notes": rep.repair_notes,
                }
                for rep in repairs
            ],
            "deposit_ledger": [
                {
                    "ledger_id": dl.ledger_id,
                    "transaction_type": dl.transaction_type,
                    "transaction_amount": float(dl.transaction_amount),
                    "transaction_reference": dl.transaction_reference,
                    "transaction_date": dl.transaction_date.isoformat(),
                    "owner_id": dl.owner_id,
                    "owner_name": dl.owner.owner_name if dl.owner else None,
                    "shipment_id": dl.shipment_id,
                    "rma_id": dl.rma_id,
                    "related_ledger_id": dl.related_ledger_id,
                    "description": dl.description,
                }
                for dl in ledger_entries
            ]
        }

    @classmethod
    def rebuild_asset_projection_from_events(cls, db: Session, asset_id: str) -> Dict[str, Any]:
        """
        Reconstructs the materialized projection (current_location_id,
        current_custodian_owner_id, asset_status, last_event_at)
        from raw immutable custody events.
        """
        from app.services.projection_service import replay
        events = db.query(CustodyEvent).filter_by(asset_id=asset_id).all()
        inspections = db.query(Inspection).filter_by(asset_id=asset_id).all()
        repairs = db.query(Repair).filter_by(asset_id=asset_id).all()
        return replay(asset_id, events, inspections, repairs)
