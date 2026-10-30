def test_health_endpoint(api_client):
    res = api_client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["database_connected"] is True

def test_api_assets_list_and_search(api_client):
    res = api_client.get("/api/assets?page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] > 0
    assert len(data["items"]) == 10

    # Search by asset_id
    res_search = api_client.get("/api/assets?search=ASSET-0000001")
    assert res_search.status_code == 200
    assert len(res_search.json()["items"]) >= 1

def test_api_asset_detail_and_history(api_client):
    res = api_client.get("/api/assets/ASSET-0000001")
    assert res.status_code == 200
    data = res.json()
    assert data["asset_id"] == "ASSET-0000001"
    assert "events" in data

    res_hist = api_client.get("/api/assets/ASSET-0000001/history")
    assert res_hist.status_code == 200
    assert res_hist.json()["events_count"] > 0

def test_api_shipments_list(api_client):
    res = api_client.get("/api/shipments?page=1&page_size=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] > 0
    assert len(data["items"]) == 5

def test_api_returns_list(api_client):
    res = api_client.get("/api/returns?page=1&page_size=5")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] > 0
    assert len(data["items"]) == 5

def test_api_analytics_overview(api_client):
    res = api_client.get("/api/analytics/overview")
    assert res.status_code == 200
    data = res.json()
    assert data["total_assets"] > 0
    assert "return_rate_pct" in data

def test_api_anomalies_list(api_client):
    res = api_client.get("/api/anomalies")
    assert res.status_code == 200
    data = res.json()
    assert len(data) > 0
