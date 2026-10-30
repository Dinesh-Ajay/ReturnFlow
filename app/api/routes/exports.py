from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.asset import ReusableAsset
from app.models.deposit_ledger import DepositLedger
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.anomaly_record import AnomalyRecord
from app.services.asset_service import AssetService
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/exports", tags=["Exports"])

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

    date_str = datetime.now().strftime("%Y%m%d")

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
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db)
):
    """Downloads Financial Ledger & Deposit Reconciliation in CSV or PDF."""
    records = db.query(DepositLedger).order_by(DepositLedger.transaction_date.desc()).limit(1000).all()
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "csv":
        csv_buffer = ExportService.export_financial_csv(records)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="returnflow_financial_ledger_{date_str}.csv"'}
        )
    else:
        pdf_buffer = ExportService.export_financial_pdf(records)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="returnflow_financial_report_{date_str}.pdf"'}
        )

@router.get("/inspections")
def export_inspections(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db)
):
    """Downloads Quality Inspection records in CSV or PDF."""
    records = db.query(Inspection).order_by(Inspection.inspection_date.desc()).limit(1000).all()
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "csv":
        csv_buffer = ExportService.export_inspections_csv(records)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="returnflow_inspections_{date_str}.csv"'}
        )
    else:
        pdf_buffer = ExportService.export_inspections_pdf(records)
        return Response(
            content=pdf_buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="returnflow_inspections_report_{date_str}.pdf"'}
        )

@router.get("/anomalies")
def export_anomalies(
    format: str = Query("csv", pattern="^(csv|pdf)$"),
    db: Session = Depends(get_db)
):
    """Downloads Detected Operational Invariants & Anomalies in CSV or PDF."""
    try:
        from app.validation.anomaly_detection import AnomalyDetectionEngine
        metrics = AnomalyDetectionEngine.evaluate_detection_metrics(db)
    except Exception:
        metrics = None

    records = db.query(AnomalyRecord).order_by(AnomalyRecord.created_at.desc()).all()
    date_str = datetime.now().strftime("%Y%m%d")

    if format == "csv":
        csv_buffer = ExportService.export_anomalies_csv(records)
        return Response(
            content=csv_buffer.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="returnflow_anomalies_{date_str}.csv"'}
        )
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
