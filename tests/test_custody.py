from app.services.custody_service import CustodyService

def test_custody_reconstruction(db_session):
    # Test traceability retrieval for first asset
    trace = CustodyService.get_asset_full_traceability(db_session, "ASSET-0000001")
    assert trace is not None
    assert trace["asset_id"] == "ASSET-0000001"
    assert "events" in trace
    assert len(trace["events"]) > 0

    # Ensure chronological order of events
    timestamps = [e["event_timestamp"] for e in trace["events"]]
    # Verify events are ordered asc
    assert timestamps == sorted(timestamps)

def test_rebuild_projection_from_events(db_session):
    proj = CustodyService.rebuild_asset_projection_from_events(db_session, "ASSET-0000001")
    assert proj is not None
    assert proj["asset_id"] == "ASSET-0000001"
    assert proj["projected_status"] in [
        "AVAILABLE", "DISPATCHED", "IN_TRANSIT", "IN_CUSTODY", "RETURNED", "LOST"
    ]
