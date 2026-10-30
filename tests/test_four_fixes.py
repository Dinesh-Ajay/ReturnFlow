import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import SessionLocal
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.models.anomaly_record import AnomalyRecord
from app.services.export_service import ExportService
from app.services.asset_service import AssetService
from app.analytics.metrics import AnalyticsService

@pytest.fixture
def client():
    return TestClient(app)

# =========================================================================
# 1. FIX ADD ASSET FUNCTIONALITY TESTS
# =========================================================================

def test_add_asset_success(client):
    """Verify that registering a valid asset succeeds, inserts into DB, and logs initial custody event."""
    payload = {
        "asset_type_code": "PALLET",
        "owner_id": 1,
        "current_location_id": 1,
        "purchase_date": str(date.today()),
        "deposit_amount": 55.00,
        "asset_status": "AVAILABLE",
        "notes": "Unit test commissioned asset."
    }
    res = client.post("/api/assets", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["status"] == "success"
    assert "asset" in data

    asset_data = data["asset"]
    new_id = asset_data["asset_id"]
    assert new_id.startswith("ASSET-")
    assert asset_data["deposit_amount"] == 55.00
    assert asset_data["asset_status"] == "AVAILABLE"

    # Verify asset is queryable in DB
    db: Session = SessionLocal()
    try:
        db_asset = db.query(ReusableAsset).filter(ReusableAsset.asset_id == new_id).first()
        assert db_asset is not None
        assert db_asset.owner_id == 1
        assert db_asset.current_location_id == 1

        # Verify initial commissioning custody event exists
        initial_evt = db.query(CustodyEvent).filter(
            CustodyEvent.asset_id == new_id,
            CustodyEvent.event_type == "COMMISSIONED"
        ).first()
        assert initial_evt is not None
        assert initial_evt.to_location_id == 1
        assert initial_evt.actor_owner_id == 1
    finally:
        db.close()

    # Verify queryable via asset details API
    detail_res = client.get(f"/api/assets/{new_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["asset_id"] == new_id
    assert detail_res.json()["events_count"] >= 1

def test_add_asset_validation_failures(client):
    """Verify validation: negative deposit, invalid foreign keys, and duplicate serial number are rejected."""
    # 1. Negative deposit rejected
    res_neg = client.post("/api/assets", json={
        "asset_type_code": "PALLET",
        "owner_id": 1,
        "current_location_id": 1,
        "purchase_date": str(date.today()),
        "deposit_amount": -10.00
    })
    assert res_neg.status_code == 422

    # 2. Invalid owner ID rejected
    res_invalid_owner = client.post("/api/assets", json={
        "asset_type_code": "PALLET",
        "owner_id": 999999,
        "current_location_id": 1,
        "purchase_date": str(date.today()),
        "deposit_amount": 50.00
    })
    assert res_invalid_owner.status_code == 400
    assert "Owner with ID 999999 does not exist" in res_invalid_owner.json()["detail"]

    # 3. Invalid location ID rejected
    res_invalid_loc = client.post("/api/assets", json={
        "asset_type_code": "PALLET",
        "owner_id": 1,
        "current_location_id": 999999,
        "purchase_date": str(date.today()),
        "deposit_amount": 50.00
    })
    assert res_invalid_loc.status_code == 400
    assert "Location with ID 999999 does not exist" in res_invalid_loc.json()["detail"]

    # 4. Duplicate serial number rejected
    unique_sn = f"SN-UNIQUE-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    res_first = client.post("/api/assets", json={
        "asset_type_code": "PALLET",
        "owner_id": 1,
        "current_location_id": 1,
        "purchase_date": str(date.today()),
        "deposit_amount": 50.00,
        "serial_number": unique_sn
    })
    assert res_first.status_code == 201

    res_dup = client.post("/api/assets", json={
        "asset_type_code": "PALLET",
        "owner_id": 1,
        "current_location_id": 1,
        "purchase_date": str(date.today()),
        "deposit_amount": 50.00,
        "serial_number": unique_sn
    })
    assert res_dup.status_code == 400
    assert "already registered" in res_dup.json()["detail"]

# =========================================================================
# 2. FIX DASHBOARD DATE RANGE TESTS
# =========================================================================

def test_dashboard_date_range_dynamic_and_filtering(client):
    """Verify default date range is dynamic, custom ranges update period metrics, and empty ranges don't crash."""
    # 1. Default overview response
    res = client.get("/api/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert "start_date" in data
    assert "end_date" in data
    assert "max_dataset_date" in data
    assert "total_assets" in data
    assert data["total_assets"] >= 20000

    # End date should match or approximate the latest available event date
    end_date = date.fromisoformat(data["end_date"])
    start_date = date.fromisoformat(data["start_date"])
    assert end_date >= start_date

    # 2. Custom date range filtering
    c_start = "2026-10-01"
    c_end = "2026-10-25"
    res_custom = client.get(f"/api/analytics/overview?start_date={c_start}&end_date={c_end}")
    assert res_custom.status_code == 200
    c_data = res_custom.json()
    assert c_data["start_date"] == c_start
    assert c_data["end_date"] == c_end
    # Lifetime total assets is preserved
    assert c_data["total_assets"] == data["total_assets"]
    # Period dispatched is populated
    assert c_data["period_dispatched"] > 0
    assert c_data["return_rate_pct"] > 0

    # 3. Trends endpoint respects custom window
    res_trends = client.get(f"/api/analytics/trends?start_date={c_start}&end_date={c_end}")
    assert res_trends.status_code == 200
    t_data = res_trends.json()
    assert len(t_data["dates"]) > 0
    assert len(t_data["dispatched"]) == len(t_data["dates"])

    # 4. Empty range handling
    res_empty = client.get("/api/analytics/overview?start_date=2010-01-01&end_date=2010-01-10")
    assert res_empty.status_code == 200
    empty_data = res_empty.json()
    assert empty_data["period_dispatched"] == 0
    assert empty_data["period_returned"] == 0

    res_empty_trends = client.get("/api/analytics/trends?start_date=2010-01-01&end_date=2010-01-10")
    assert res_empty_trends.status_code == 200
    assert len(res_empty_trends.json()["dates"]) == 0

# =========================================================================
# 3. FIX ASSET VIEW ALL EVENTS TESTS
# =========================================================================

def test_asset_view_all_events(client):
    """Verify complete custody history retrieval for a specific asset with 9 required attributes."""
    target_asset = "ASSET-0000001"
    res = client.get(f"/api/assets/{target_asset}/history")
    assert res.status_code == 200
    data = res.json()
    assert data["asset_id"] == target_asset
    assert "events" in data
    assert data["events_count"] > 0

    # Alias /events route works identically
    res_alias = client.get(f"/api/assets/{target_asset}/events")
    assert res_alias.status_code == 200
    assert res_alias.json()["events_count"] == data["events_count"]

    events = data["events"]
    # Verify chronological ordering
    timestamps = [datetime.fromisoformat(e["event_timestamp"]) for e in events]
    assert timestamps == sorted(timestamps)

    # Verify event fields
    for e in events:
        assert "custody_event_id" in e
        assert e["asset_id"] == target_asset  # No cross-asset leakage
        assert "event_type" in e
        assert "from_location_name" in e
        assert "to_location_name" in e
        assert "actor_owner_name" in e
        assert "shipment_id" in e
        assert "event_timestamp" in e
        assert "notes" in e

    # Test non-existent asset returns 404
    res_404 = client.get("/api/assets/ASSET-NONEXISTENT/history")
    assert res_404.status_code == 404

# =========================================================================
# 4. FIX ANOMALY AUDIT REPORT PDF DOWNLOAD TESTS
# =========================================================================

def test_anomaly_pdf_download(client):
    """Verify that Anomaly Audit Report PDF download returns 200, application/pdf, and valid PDF bytes."""
    res = client.get("/api/exports/anomalies?format=pdf")
    assert res.status_code == 200
    assert res.headers.get("content-type") == "application/pdf"
    assert "attachment" in res.headers.get("content-disposition", "")
    assert "returnflow_anomalies_report_" in res.headers.get("content-disposition", "")
    assert res.content.startswith(b"%PDF-")
    assert len(res.content) > 1000

    # Verify category report route works identically
    res_cat = client.get("/api/exports/report?category=anomalies&format=pdf")
    assert res_cat.status_code == 200
    assert res_cat.content.startswith(b"%PDF-")

def test_anomaly_pdf_empty_records_handling():
    """Verify ExportService renders empty anomaly records cleanly without raising exceptions."""
    buf = ExportService.export_anomalies_pdf([], metrics={"total_injected": 0, "total_detected": 0})
    assert buf is not None
    pdf_bytes = buf.getvalue()
    assert pdf_bytes.startswith(b"%PDF-")
