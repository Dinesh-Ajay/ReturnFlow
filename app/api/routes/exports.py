from datetime import datetime, timedelta, time
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.asset import ReusableAsset
from app.models.deposit_ledger import DepositLedger
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.anomaly_record import AnomalyRecord
from app.models.shipment import Shipment
from app.models.custody_event import CustodyEvent
from app.models.return_authorization import ReturnAuthorization
from app.models.repair import Repair
from app.services.asset_service import AssetService
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/exports", tags=["Exports"])

def _export_rows(records, model, name: str, format: str):
    """Build a normal attachment response for a database-backed report."""
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    if format == "csv":
        body, mime, extension = ExportService.export_records_csv(records).getvalue(), "text/csv; charset=utf-8", "csv"
    elif format == "json":
        body, mime, extension = ExportService.export_records_json(records, name), "application/json", "json"
    else:
        body, mime, extension = ExportService.export_records_pdf(records, name).getvalue(), "application/pdf", "pdf"
    return Response(body, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="returnflow_{name}_{date_str}.{extension}"'})

def _date_filtered_query(db, model, date_column, start_date, end_date):
    query = db.query(model).order_by(date_column.desc())
    if start_date is not None:
        query = query.filter(date_column >= start_date)
    if end_date is not None:
        # A date-only upper bound means the whole requested calendar day;
        # explicit timestamps remain exclusive upper bounds.
        upper_bound = end_date + timedelta(days=1) if end_date.time() == time.min else end_date
        query = query.filter(date_column < upper_bound)
    return query.all()

@router.get("/shipments")
def export_shipments(format: str = Query("csv", pattern="^(csv|json|pdf)$"), start_date: Optional[datetime] = Query(None), end_date: Optional[datetime] = Query(None), db: Session = Depends(get_db)):
    records = _date_filtered_query(db, Shipment, Shipment.dispatch_date, start_date, end_date)
    return _export_rows(records, Shipment, "shipments", format)

@router.get("/custody-events")
def export_custody_events(format: str = Query("csv", pattern="^(csv|json|pdf)$"), start_date: Optional[datetime] = Query(None), end_date: Optional[datetime] = Query(None), db: Session = Depends(get_db)):
    records = _date_filtered_query(db, CustodyEvent, CustodyEvent.event_timestamp, start_date, end_date)
    return _export_rows(records, CustodyEvent, "custody_events", format)

@router.get("/returns")
def export_returns(format: str = Query("csv", pattern="^(csv|json|pdf)$"), start_date: Optional[datetime] = Query(None), end_date: Optional[datetime] = Query(None), db: Session = Depends(get_db)):
    records = _date_filtered_query(db, ReturnAuthorization, ReturnAuthorization.requested_date, start_date, end_date)
    return _export_rows(records, ReturnAuthorization, "return_authorizations", format)

@router.get("/repairs")
def export_repairs(format: str = Query("csv", pattern="^(csv|json|pdf)$"), start_date: Optional[datetime] = Query(None), end_date: Optional[datetime] = Query(None), db: Session = Depends(get_db)):
    records = _date_filtered_query(db, Repair, Repair.repair_start_date, start_date, end_date)
    return _export_rows(records, Repair, "repairs", format)

@router.get("/ground-truth")
def export_ground_truth(format: str = Query("json", pattern="^(csv|json)$")):
    """Ground truth is a separate evaluation artifact, never queried by detectors."""
    import csv
    import io
    import json
    import os
    from fastapi import HTTPException
    from app.config import settings
    path = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")
    try:
        with open(path, "r", encoding="utf-8") as source:
            rows = json.load(source)
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Ground-truth evaluation dataset is unavailable") from exc
    if format == "json":
        body, mime = json.dumps(rows, indent=2), "application/json"
    else:
        output = io.StringIO()
        fields = list(rows[0]) if rows else []
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
        body, mime = output.getvalue(), "text/csv; charset=utf-8"
    return Response(body, media_type=mime,
                    headers={"Content-Disposition": f'attachment; filename="returnflow_ground_truth_{datetime.now():%Y%m%d_%H%M%S}.{format}"'})

@router.get("/assets")
def export_assets(
    format: str = Query("csv", pattern="^(csv|pdf|json)$"),
    search: Optional[str] = Query(None),
    asset_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    overdue_only: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Downloads filtered asset registry in requested file format (CSV, PDF, or JSON).
    Properly triggers native browser file download with attachment headers.
    """
    assets, total = AssetService.list_assets(
        db=db,
        page=1,
        page_size=1000,
        search=search,
        asset_type_code=asset_type,
        status=status_filter,
        overdue_only=overdue_only
    )
    pages = [assets]
    for page in range(2, (total + 999) // 1000 + 1):
        page_assets, _ = AssetService.list_assets(
            db=db, page=page, page_size=1000, search=search,
            asset_type_code=asset_type, status=status_filter, overdue_only=overdue_only)
        pages.append(page_assets)
    assets = [asset for page_assets in pages for asset in page_assets]

    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        csv_buffer = ExportService.export_assets_csv(assets)
        filename = f"returnflow_assets_{date_str}.csv"
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    elif format == "pdf":
        filter_str = f"Status={status_filter or 'All'}, Type={asset_type or 'All'}"
        pdf_buffer = ExportService.export_assets_pdf(assets, filter_desc=filter_str)
        filename = f"returnflow_assets_report_{date_str}.pdf"
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    elif format == "json":
        json_content = ExportService.export_assets_json(assets)
        filename = f"returnflow_assets_{date_str}.json"
        return Response(
            content=json_content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

@router.get("/financial")
def export_financial(
    format: str = Query("csv", pattern="^(csv|pdf|json)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Downloads Financial Ledger & Deposit Reconciliation in CSV or PDF."""
    records = _date_filtered_query(db, DepositLedger, DepositLedger.transaction_date, start_date, end_date)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        csv_buffer = ExportService.export_financial_csv(records)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="returnflow_financial_ledger_{date_str}.csv"'}
        )
    elif format == "json":
        content = ExportService.export_records_json(records, "ReturnFlow Financial Ledger")
        return Response(content, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="returnflow_financial_ledger_{date_str}.json"'})
    else:
        pdf_buffer = ExportService.export_financial_pdf(records)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="returnflow_financial_report_{date_str}.pdf"'}
        )

@router.get("/inspections")
def export_inspections(
    format: str = Query("csv", pattern="^(csv|pdf|json)$"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """Downloads Quality Inspection records in CSV or PDF."""
    records = _date_filtered_query(db, Inspection, Inspection.inspection_date, start_date, end_date)
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        csv_buffer = ExportService.export_inspections_csv(records)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="returnflow_inspections_{date_str}.csv"'}
        )
    elif format == "json":
        content = ExportService.export_records_json(records, "ReturnFlow Inspections")
        return Response(content, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="returnflow_inspections_{date_str}.json"'})
    else:
        pdf_buffer = ExportService.export_inspections_pdf(records)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="returnflow_inspections_report_{date_str}.pdf"'}
        )

@router.get("/anomalies")
def export_anomalies(
    format: str = Query("csv", pattern="^(csv|pdf|json)$"),
    db: Session = Depends(get_db)
):
    """Downloads Detected Operational Invariants & Anomalies in CSV or PDF."""
    try:
        from app.validation.anomaly_detection import AnomalyDetectionEngine
        metrics = AnomalyDetectionEngine.evaluate_detection_metrics(db)
    except Exception:
        metrics = None

    records = db.query(AnomalyRecord).order_by(AnomalyRecord.created_at.desc()).all()
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv":
        csv_buffer = ExportService.export_anomalies_csv(records)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="returnflow_anomalies_{date_str}.csv"'}
        )
    elif format == "json":
        content = ExportService.export_records_json(records, "ReturnFlow Anomaly Audit")
        return Response(content, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="returnflow_anomalies_{date_str}.json"'})
    else:
        pdf_buffer = ExportService.export_anomalies_pdf(records, metrics=metrics)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="returnflow_anomalies_report_{date_str}.pdf"'}
        )

@router.get("/report")
def export_category_report(
    category: str = Query("assets"),
    format: str = Query("pdf", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db)
):
    """Downloads structured reports for Reports page categories."""
    if category in ("assets", "lifecycle"):
        return export_assets(format=format, db=db)
    elif category == "financial":
        return export_financial(format=format, db=db)
    elif category == "inspections":
        return export_inspections(format=format, db=db)
    elif category == "anomalies":
        return export_anomalies(format=format, db=db)
    else:
        return export_assets(format=format, db=db)
