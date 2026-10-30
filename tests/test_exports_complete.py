import csv
import io
import json

import pytest


EXPORT_CASES = [
    ("/api/exports/financial", "json"),
    ("/api/exports/financial", "pdf"),
    ("/api/exports/inspections", "csv"),
    ("/api/exports/inspections", "json"),
    ("/api/exports/anomalies", "csv"),
    ("/api/exports/anomalies", "json"),
    *[(f"/api/exports/{entity}", fmt)
      for entity in ("shipments", "custody-events", "returns", "repairs")
      for fmt in ("csv", "json", "pdf")],
]


@pytest.mark.parametrize(("path", "file_format"), EXPORT_CASES)
def test_database_export_downloads(api_client, path, file_format):
    response = api_client.get(f"{path}?format={file_format}")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert f".{file_format}" in response.headers["content-disposition"]

    if file_format == "csv":
        assert "text/csv" in response.headers["content-type"]
        rows = list(csv.reader(io.StringIO(response.text)))
        assert rows and rows[0]
    elif file_format == "json":
        assert "application/json" in response.headers["content-type"]
        assert json.loads(response.content)
    else:
        assert response.headers["content-type"].startswith("application/pdf")
        assert response.content.startswith(b"%PDF-")
        assert b"startxref" in response.content[-100:]
        assert response.content.rstrip().endswith(b"%%EOF")


@pytest.mark.parametrize("file_format", ["csv", "json"])
def test_separate_ground_truth_download(api_client, file_format):
    response = api_client.get(f"/api/exports/ground-truth?format={file_format}")
    assert response.status_code == 200
    assert "attachment" in response.headers["content-disposition"]
    assert "text/csv" in response.headers["content-type"] if file_format == "csv" else "application/json" in response.headers["content-type"]
    if file_format == "csv":
        assert len(response.text.splitlines()) > 1
    else:
        assert isinstance(json.loads(response.content), list)
