import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.models.asset import ReusableAsset
from app.models.asset_type import AssetType
from app.models.owner import Owner
from app.models.location import Location
from app.models.shipment import Shipment
from app.models.return_authorization import ReturnAuthorization
from app.models.custody_event import CustodyEvent
from app.services.shipment_service import ShipmentService
from app.services.return_service import ReturnService
from app.services.inspection_service import InspectionService
from app.services.repair_service import RepairService
from app.services.asset_service import AssetService

def get_or_create_fixtures(db_session):
    """Ensure baseline asset type, owners, and locations exist for testing."""
    asset_type = db_session.query(AssetType).first()
    if not asset_type:
        asset_type = AssetType(
            type_code="TEST-RPC",
            type_name="Test Reusable Plastic Crate",
            category="CONTAINER",
            default_deposit_amount=Decimal("50.00"),
            return_due_days=30,
            loss_threshold_days=60
        )
        db_session.add(asset_type)
        db_session.flush()

    owners = db_session.query(Owner).limit(3).all()
    if len(owners) < 3:
        owner_enterprise = Owner(owner_name="Test Enterprise Inc", owner_type="ENTERPRISE", contact_email="test_ent@returnflow.com")
        owner_carrier = Owner(owner_name="Test Fast Logistics", owner_type="CARRIER", contact_email="test_carrier@returnflow.com")
        owner_customer = Owner(owner_name="Test Customer Ltd", owner_type="CUSTOMER", contact_email="test_cust@returnflow.com")
        db_session.add_all([owner_enterprise, owner_carrier, owner_customer])
        db_session.flush()
        owners = [owner_enterprise, owner_carrier, owner_customer]

    locations = db_session.query(Location).limit(2).all()
    if len(locations) < 2:
        loc_dc = Location(location_name="Test Distribution Center", location_type="DC", owner_id=owners[0].owner_id)
        loc_cust = Location(location_name="Test Customer Hub", location_type="STORE", owner_id=owners[2].owner_id)
        db_session.add_all([loc_dc, loc_cust])
        db_session.flush()
        locations = [loc_dc, loc_cust]

    return asset_type, owners, locations

def create_test_asset(db_session, status="AVAILABLE"):
    asset_type, owners, locations = get_or_create_fixtures(db_session)
    res = AssetService.create_asset(
        db_session,
        {
            "asset_type_id": asset_type.asset_type_id,
            "owner_id": owners[0].owner_id,
            "current_location_id": locations[0].location_id,
            "deposit_amount": 50.0,
            "asset_status": status
        }
    )
    asset = db_session.query(ReusableAsset).filter(ReusableAsset.asset_id == res["asset_id"]).first()
    return asset, asset_type, owners, locations

def test_valid_lifecycle_dispatch_records_custody_event(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="AVAILABLE")
    carrier = owners[1]
    origin_loc = locations[0]
    dest_loc = locations[1]

    shipment = ShipmentService.create_shipment(
        db=db_session,
        origin_location_id=origin_loc.location_id,
        destination_location_id=dest_loc.location_id,
        carrier_owner_id=carrier.owner_id,
        asset_ids=[asset.asset_id],
        expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=2)
    )

    db_session.refresh(asset)
    assert asset.asset_status == "IN_TRANSIT"
    assert asset.current_location_id is None
    assert asset.current_custodian_owner_id == carrier.owner_id

    # Verify custody event was recorded
    events = db_session.query(CustodyEvent).filter(
        CustodyEvent.asset_id == asset.asset_id,
        CustodyEvent.event_type == "DISPATCHED"
    ).all()
    assert len(events) == 1
    event = events[0]
    assert event.shipment_id == shipment.shipment_id
    assert event.from_location_id == origin_loc.location_id
    assert event.to_location_id is None
    assert event.to_owner_id == carrier.owner_id

def test_valid_lifecycle_delivery_records_custody_event(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="AVAILABLE")
    carrier = owners[1]
    origin_loc = locations[0]
    dest_loc = locations[1]

    shipment = ShipmentService.create_shipment(
        db=db_session,
        origin_location_id=origin_loc.location_id,
        destination_location_id=dest_loc.location_id,
        carrier_owner_id=carrier.owner_id,
        asset_ids=[asset.asset_id],
        expected_delivery_date=datetime.now(timezone.utc) + timedelta(days=2)
    )

    deliv_dt = datetime.now(timezone.utc) + timedelta(days=1)
    ShipmentService.deliver_shipment(
        db=db_session,
        shipment_id=shipment.shipment_id,
        actual_delivery_date=deliv_dt
    )

    db_session.refresh(asset)
    assert asset.asset_status == "IN_CUSTODY"
    assert asset.current_location_id == dest_loc.location_id
    assert asset.current_custodian_owner_id == asset.owner_id

    # Verify custody event
    events = db_session.query(CustodyEvent).filter(
        CustodyEvent.asset_id == asset.asset_id,
        CustodyEvent.event_type == "RECEIVED"
    ).all()
    assert len(events) == 1
    evt = events[0]
    assert evt.from_owner_id == carrier.owner_id
    assert evt.to_location_id == dest_loc.location_id

def test_valid_lifecycle_return_receipt_records_custody_event(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="AVAILABLE")
    carrier = owners[1]
    origin_loc = locations[0]
    dest_loc = locations[1]

    shipment = ShipmentService.create_shipment(
        db=db_session,
        origin_location_id=origin_loc.location_id,
        destination_location_id=dest_loc.location_id,
        carrier_owner_id=carrier.owner_id,
        asset_ids=[asset.asset_id]
    )
    ShipmentService.deliver_shipment(db=db_session, shipment_id=shipment.shipment_id)

    # Customer requests return (RMA)
    rma = ReturnService.create_rma(
        db=db_session,
        requesting_owner_id=owners[2].owner_id,
        receiving_owner_id=owners[0].owner_id,
        return_location_id=origin_loc.location_id,
        asset_ids=[asset.asset_id]
    )
    db_session.refresh(asset)
    assert asset.asset_status == "RETURN_PENDING"

    # Facility receives return
    ReturnService.receive_return(db=db_session, rma_id=rma.rma_id)
    db_session.refresh(asset)
    assert asset.asset_status == "INSPECTION_PENDING"
    assert asset.current_location_id == origin_loc.location_id
    assert asset.current_custodian_owner_id == owners[0].owner_id

    # Verify custody event
    events = db_session.query(CustodyEvent).filter(
        CustodyEvent.asset_id == asset.asset_id,
        CustodyEvent.event_type == "RETURNED"
    ).all()
    assert len(events) == 1
    evt = events[0]
    assert evt.to_location_id == origin_loc.location_id
    assert evt.to_owner_id == owners[0].owner_id

def test_cannot_dispatch_retired_asset(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="RETIRED")
    with pytest.raises(ValueError, match="RETIRED"):
        ShipmentService.create_shipment(
            db=db_session,
            origin_location_id=locations[0].location_id,
            destination_location_id=locations[1].location_id,
            carrier_owner_id=owners[1].owner_id,
            asset_ids=[asset.asset_id]
        )

def test_cannot_dispatch_lost_asset(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="LOST")
    with pytest.raises(ValueError, match="LOST"):
        ShipmentService.create_shipment(
            db=db_session,
            origin_location_id=locations[0].location_id,
            destination_location_id=locations[1].location_id,
            carrier_owner_id=owners[1].owner_id,
            asset_ids=[asset.asset_id]
        )

def test_duplicate_dispatch_prevented(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="AVAILABLE")
    ShipmentService.create_shipment(
        db=db_session,
        origin_location_id=locations[0].location_id,
        destination_location_id=locations[1].location_id,
        carrier_owner_id=owners[1].owner_id,
        asset_ids=[asset.asset_id]
    )
    # Attempting to dispatch again while already IN_TRANSIT
    with pytest.raises(ValueError, match="in transit"):
        ShipmentService.create_shipment(
            db=db_session,
            origin_location_id=locations[0].location_id,
            destination_location_id=locations[1].location_id,
            carrier_owner_id=owners[1].owner_id,
            asset_ids=[asset.asset_id]
        )

def test_repair_lifecycle_enforcement(db_session):
    asset, _, owners, locations = create_test_asset(db_session, status="AVAILABLE")

    # Available asset cannot be repaired directly
    with pytest.raises(ValueError, match="AVAILABLE and does not require repair"):
        RepairService.initiate_repair(
            db=db_session,
            asset_id=asset.asset_id,
            repair_location_id=locations[0].location_id
        )

    # Set to INSPECTION_PENDING then DAMAGED via inspection
    asset.asset_status = "INSPECTION_PENDING"
    db_session.flush()

    insp = InspectionService.record_inspection(
        db=db_session,
        asset_id=asset.asset_id,
        inspector_owner_id=owners[0].owner_id,
        condition_status="DAMAGED",
        damage_severity="MAJOR"
    )
    db_session.refresh(asset)
    assert asset.asset_status == "DAMAGED"

    # Now initiate repair
    repair = RepairService.initiate_repair(
        db=db_session,
        asset_id=asset.asset_id,
        repair_location_id=locations[0].location_id,
        inspection_id=insp.inspection_id
    )
    db_session.refresh(asset)
    assert asset.asset_status == "UNDER_REPAIR"

    # Complete repair
    RepairService.complete_repair(
        db=db_session,
        repair_id=repair.repair_id,
        cost=Decimal("75.00")
    )
    db_session.refresh(asset)
    assert asset.asset_status == "INSPECTION_PENDING"

    # Re-inspect to AVAILABLE
    InspectionService.record_inspection(
        db=db_session,
        asset_id=asset.asset_id,
        inspector_owner_id=owners[0].owner_id,
        condition_status="GOOD"
    )
    db_session.refresh(asset)
    assert asset.asset_status == "AVAILABLE"

def test_transaction_rollback_leaves_no_orphan_events(db_session):
    asset1, _, owners, locations = create_test_asset(db_session, status="AVAILABLE")
    asset2, _, _, _ = create_test_asset(db_session, status="RETIRED")

    pre_events_count = db_session.query(CustodyEvent).filter(CustodyEvent.asset_id == asset1.asset_id).count()

    # Attempt multi-asset shipment where one asset is RETIRED -> entire transaction should fail
    try:
        with db_session.begin_nested():
            ShipmentService.create_shipment(
                db=db_session,
                origin_location_id=locations[0].location_id,
                destination_location_id=locations[1].location_id,
                carrier_owner_id=owners[1].owner_id,
                asset_ids=[asset1.asset_id, asset2.asset_id]
            )
    except ValueError:
        pass

    # Ensure asset1 has NO orphan DISPATCHED event
    post_events_count = db_session.query(CustodyEvent).filter(CustodyEvent.asset_id == asset1.asset_id).count()
    assert post_events_count == pre_events_count
    db_session.refresh(asset1)
    assert asset1.asset_status == "AVAILABLE"
