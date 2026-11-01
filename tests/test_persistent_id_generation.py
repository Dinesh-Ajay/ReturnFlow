import pytest
import concurrent.futures
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.utils.id_generator import PersistentIDGenerator, IDGenerator
from app.services.shipment_service import ShipmentService
from app.services.return_service import ReturnService
from app.services.inspection_service import InspectionService
from app.services.repair_service import RepairService
from app.models.shipment import Shipment
from app.models.return_authorization import ReturnAuthorization
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.asset import ReusableAsset

def utc_now():
    return datetime.now(timezone.utc)

def test_shipment_id_allocation_on_populated_db(db_session):
    """Verify creating a shipment on a populated database produces no duplicate-ID error."""
    # Find an asset to attach
    asset = db_session.query(ReusableAsset).filter(ReusableAsset.asset_status == "AVAILABLE").first()
    assert asset is not None, "At least one AVAILABLE asset required"

    now = utc_now()
    exp_deliv = now + timedelta(days=2)

    shipment = ShipmentService.create_shipment(
        db=db_session,
        origin_location_id=asset.current_location_id,
        destination_location_id=2,
        carrier_owner_id=3,
        dispatch_date=now,
        expected_delivery_date=exp_deliv,
        asset_ids=[asset.asset_id]
    )

    assert shipment.shipment_id.startswith("SHP-2026-")
    # Populated DB has 10,000 shipments, so new ID must be > 10,000
    suffix = int(shipment.shipment_id.split("-")[-1])
    assert suffix >= 10001
    assert db_session.query(Shipment).filter(Shipment.shipment_id == shipment.shipment_id).count() == 1

def test_rma_id_allocation_on_populated_db(db_session):
    """Verify creating an RMA on a populated database produces no duplicate-ID error."""
    asset = db_session.query(ReusableAsset).filter(ReusableAsset.asset_status == "IN_CUSTODY").first()
    if not asset:
        asset = db_session.query(ReusableAsset).first()

    now = utc_now()
    exp_ret = now + timedelta(days=5)

    rma = ReturnService.create_rma(
        db=db_session,
        requesting_owner_id=asset.owner_id,
        receiving_owner_id=1,
        return_location_id=1,
        requested_date=now,
        expected_return_date=exp_ret,
        asset_ids=[asset.asset_id]
    )

    assert rma.rma_id.startswith("RMA-2026-")
    # Populated DB has 12,400 RMAs, so new ID must be > 12,400
    suffix = int(rma.rma_id.split("-")[-1])
    assert suffix >= 12401
    assert db_session.query(ReturnAuthorization).filter(ReturnAuthorization.rma_id == rma.rma_id).count() == 1

def test_inspection_id_allocation_on_populated_db(db_session):
    """Verify creating an inspection on a populated database produces no duplicate-ID error."""
    asset = db_session.query(ReusableAsset).first()
    asset.asset_status = "INSPECTION_PENDING"
    insp = InspectionService.record_inspection(
        db=db_session,
        asset_id=asset.asset_id,
        inspector_owner_id=1,
        condition_status="GOOD"
    )

    assert insp.inspection_id.startswith("INSP-2026-")
    # Populated DB has 12,400 inspections, so new ID must be > 12,400
    suffix = int(insp.inspection_id.split("-")[-1])
    assert suffix >= 12401
    assert db_session.query(Inspection).filter(Inspection.inspection_id == insp.inspection_id).count() == 1

def test_repair_id_allocation_on_populated_db(db_session):
    """Verify creating a repair on a populated database produces no duplicate-ID error."""
    asset = db_session.query(ReusableAsset).first()
    asset.asset_status = "INSPECTION_PENDING"
    inspection = InspectionService.record_inspection(db_session, asset.asset_id, 1, "DAMAGED")
    rep = RepairService.initiate_repair(
        db=db_session,
        asset_id=asset.asset_id,
        repair_location_id=1,
        inspection_id=inspection.inspection_id
    )

    assert rep.repair_id.startswith("REP-2026-")
    # Populated DB has 1,348 repairs, so new ID must be > 1,348
    suffix = int(rep.repair_id.split("-")[-1])
    assert suffix >= 1349
    assert db_session.query(Repair).filter(Repair.repair_id == rep.repair_id).count() == 1

def test_sequential_allocations(db_session):
    """Verify sequential calls produce monotonically strictly increasing IDs."""
    id1 = PersistentIDGenerator.next_shipment_id(db_session, year=2026)
    id2 = PersistentIDGenerator.next_shipment_id(db_session, year=2026)
    id3 = PersistentIDGenerator.next_shipment_id(db_session, year=2026)

    val1 = int(id1.split("-")[-1])
    val2 = int(id2.split("-")[-1])
    val3 = int(id3.split("-")[-1])

    assert val2 == val1 + 1
    assert val3 == val2 + 1

def test_year_based_identifier_formats(db_session):
    """Verify that different years create distinct sequences without collision."""
    id_2026 = PersistentIDGenerator.next_shipment_id(db_session, year=2026)
    id_2027 = PersistentIDGenerator.next_shipment_id(db_session, year=2027)

    assert id_2026.startswith("SHP-2026-")
    assert id_2027.startswith("SHP-2027-")
    # For a new year (2027), sequence starts from 1 if no 2027 shipments exist
    assert id_2027 == "SHP-2027-000001"

def test_rollback_behavior(db_engine):
    """Verify that rolling back a transaction rolls back the allocated sequence counter."""
    Session = sessionmaker(bind=db_engine)
    session = Session()

    try:
        # Check current sequence value
        val_before = PersistentIDGenerator.allocate_next_sequence_val(session, "test_rollback_seq", "shipment")
        session.commit()

        # In a new transaction, allocate and rollback
        val_temp = PersistentIDGenerator.allocate_next_sequence_val(session, "test_rollback_seq", "shipment")
        assert val_temp == val_before + 1
        session.rollback()

        # Next allocation in new transaction gets val_before + 1 again because previous rolled back
        val_after = PersistentIDGenerator.allocate_next_sequence_val(session, "test_rollback_seq", "shipment")
        session.commit()
        assert val_after == val_before + 1

    finally:
        session.close()

def test_concurrent_id_allocation(db_engine):
    """Simulate concurrent threads allocating IDs simultaneously to verify no duplicate IDs."""
    num_threads = 8
    allocated_ids = []

    def allocate():
        Session = sessionmaker(bind=db_engine)
        session = Session()
        try:
            allocated = PersistentIDGenerator.next_shipment_id(session, year=2028)
            session.commit()
            return allocated
        finally:
            session.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(allocate) for _ in range(num_threads)]
        for f in concurrent.futures.as_completed(futures):
            allocated_ids.append(f.result())

    assert len(allocated_ids) == num_threads
    # Check 100% uniqueness - no duplicates
    assert len(set(allocated_ids)) == num_threads
    # Check all are SHP-2028-
    for a_id in allocated_ids:
        assert a_id.startswith("SHP-2028-")
