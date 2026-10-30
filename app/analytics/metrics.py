from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date, timedelta, time
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.config import settings
from app.models.asset import ReusableAsset
from app.models.shipment import Shipment
from app.models.custody_event import CustodyEvent
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.deposit_ledger import DepositLedger
from app.models.return_authorization import ReturnAuthorization
from app.services.lifecycle_service import LifecycleService
from app.services.deposit_service import DepositService

class AnalyticsService:
    """
    Computes business analytics, operational KPIs, and data quality metrics
    with dynamic reporting period date-range filtering.
    """

    @classmethod
    def get_dataset_date_bounds(cls, db: Session) -> Dict[str, date]:
        """
        Determines the earliest and latest actual event/transaction dates in the database.
        """
        max_custody = db.execute(text("SELECT MAX(event_timestamp) FROM custody_events")).scalar()
        max_deposit = db.execute(text("SELECT MAX(transaction_date) FROM deposit_ledger")).scalar()
        min_custody = db.execute(text("SELECT MIN(event_timestamp) FROM custody_events")).scalar()

        valid_maxes = [d for d in [max_custody, max_deposit] if d is not None]
        if valid_maxes:
            max_dt = max(valid_maxes)
        else:
            max_dt = datetime.now()

        min_dt = min_custody if min_custody else (max_dt - timedelta(days=180))

        max_d = max_dt.date() if isinstance(max_dt, datetime) else max_dt
        min_d = min_dt.date() if isinstance(min_dt, datetime) else min_dt

        return {"min_date": min_d, "max_date": max_d}

    @classmethod
    def get_overview_kpis(
        cls,
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        bounds = cls.get_dataset_date_bounds(db)
        dataset_max = bounds["max_date"]
        dataset_min = bounds["min_date"]

        # Default end date is latest available business date
        if end_date is None:
            end_date = dataset_max
        if start_date is None:
            start_date = end_date - timedelta(days=30)

        # Handle inversion
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        # Current Asset Portfolio Lifetime Totals (not artificially truncated)
        total_assets = db.query(ReusableAsset).count()
        total_shipments = db.query(Shipment).count()
        total_events = db.query(CustodyEvent).count()

        # Current Status counts across entire portfolio
        status_counts_raw = db.query(
            ReusableAsset.asset_status, 
            func.count(ReusableAsset.asset_id)
        ).group_by(ReusableAsset.asset_status).all()
        status_counts = {r[0]: int(r[1]) for r in status_counts_raw}

        in_transit = status_counts.get("IN_TRANSIT", 0)
        in_custody = status_counts.get("IN_CUSTODY", 0)
        return_pending = status_counts.get("RETURN_PENDING", 0)
        available = status_counts.get("AVAILABLE", 0)
        damaged = status_counts.get("DAMAGED", 0)
        under_repair = status_counts.get("UNDER_REPAIR", 0)
        lost = status_counts.get("LOST", 0)

        # Total outstanding assets in active circulation
        total_outstanding = in_transit + in_custody + return_pending

        # Overdue calculation as of the selected end_date
        overdue_query = text("""
            SELECT COUNT(*) 
            FROM reusable_assets a
            JOIN asset_types t ON a.asset_type_id = t.asset_type_id
            WHERE a.asset_status IN ('IN_TRANSIT', 'IN_CUSTODY', 'RETURN_PENDING')
              AND DATEDIFF(:as_of_date, a.last_event_at) > t.return_due_days
        """)
        overdue_count = db.execute(overdue_query, {"as_of_date": end_date}).scalar() or 0

        # Period-Specific Dispatched & Returned Metrics (activity within the selected range)
        period_dispatched = db.query(CustodyEvent).filter(
            CustodyEvent.event_type == "DISPATCHED",
            CustodyEvent.event_timestamp >= start_dt,
            CustodyEvent.event_timestamp <= end_dt
        ).count()

        period_returned = db.query(CustodyEvent).filter(
            CustodyEvent.event_type == "RETURNED",
            CustodyEvent.event_timestamp >= start_dt,
            CustodyEvent.event_timestamp <= end_dt
        ).count()

        period_shipments = db.query(Shipment).filter(
            Shipment.dispatch_date >= start_dt,
            Shipment.dispatch_date <= end_dt
        ).count()

        # Lifetime Dispatched & Returned (for cumulative fallback)
        total_dispatched = db.query(CustodyEvent).filter(CustodyEvent.event_type == "DISPATCHED").count()
        total_returned = db.query(CustodyEvent).filter(CustodyEvent.event_type == "RETURNED").count()

        # Dynamic rates based on the reporting period
        if period_dispatched > 0:
            return_rate = (period_returned / period_dispatched * 100.0)
        elif total_dispatched > 0:
            return_rate = (total_returned / total_dispatched * 100.0)
        else:
            return_rate = 0.0

        overdue_rate = (overdue_count / total_outstanding * 100.0) if total_outstanding > 0 else 0.0
        loss_rate = (lost / total_assets * 100.0) if total_assets > 0 else 0.0

        total_inspections = db.query(Inspection).count()
        total_rmas = db.query(ReturnAuthorization).count()
        damage_count = db.query(Inspection).filter(Inspection.condition_status.in_(["DAMAGED", "CRITICAL"])).count()
        damage_rate = (damage_count / total_inspections * 100.0) if total_inspections > 0 else 0.0

        # Average outstanding days as of selected end_date
        avg_days_query = text("""
            SELECT AVG(DATEDIFF(:as_of_date, a.last_event_at))
            FROM reusable_assets a
            WHERE a.asset_status IN ('IN_TRANSIT', 'IN_CUSTODY', 'RETURN_PENDING')
              AND a.last_event_at IS NOT NULL
        """)
        avg_days = db.execute(avg_days_query, {"as_of_date": end_date}).scalar() or 0.0

        # Financial summary
        fin_summary = DepositService.get_portfolio_financial_summary(db)

        # Anomaly counts
        open_anomalies_query = text("SELECT COUNT(*) FROM anomaly_records WHERE detection_status = 'OPEN' OR detection_status = 'DETECTED'")
        open_anomalies = db.execute(open_anomalies_query).scalar() or 0

        return {
            "start_date": str(start_date),
            "end_date": str(end_date),
            "max_dataset_date": str(dataset_max),
            "min_dataset_date": str(dataset_min),
            "total_assets": total_assets,
            "total_shipments": total_shipments,
            "total_rmas": total_rmas,
            "period_shipments": period_shipments,
            "total_custody_events": total_events,
            "active_in_transit": in_transit,
            "in_custody": in_custody,
            "total_outstanding": total_outstanding,
            "overdue_count": overdue_count,
            "lost_count": lost,
            "damaged_count": damaged,
            "in_repair_count": under_repair,
            "available_count": available,
            "total_returned": total_returned,
            "period_dispatched": period_dispatched,
            "period_returned": period_returned,
            "return_rate_pct": round(return_rate, 1),
            "overdue_rate_pct": round(overdue_rate, 1),
            "loss_rate_pct": round(loss_rate, 2),
            "damage_rate_pct": round(damage_rate, 1),
            "avg_outstanding_days": round(float(avg_days), 1),
            "open_anomalies": open_anomalies,
            "deposit_liability": fin_summary["outstanding_deposit_liability"],
            "financial_summary": fin_summary,
            "status_distribution": status_counts
        }

    @classmethod
    def get_asset_movement_trends(
        cls,
        db: Session,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Aggregates daily dispatched vs returned vs in_transit counts for the requested date window.
        """
        bounds = cls.get_dataset_date_bounds(db)
        if end_date is None:
            end_date = bounds["max_date"]
        if start_date is None:
            span_days = days if days is not None else 30
            start_date = end_date - timedelta(days=span_days)

        if start_date > end_date:
            start_date, end_date = end_date, start_date

        start_dt = datetime.combine(start_date, time.min)
        end_dt = datetime.combine(end_date, time.max)

        query = text("""
            SELECT 
                DATE(event_timestamp) as event_date,
                SUM(CASE WHEN event_type = 'DISPATCHED' THEN 1 ELSE 0 END) as dispatched,
                SUM(CASE WHEN event_type = 'RETURNED' THEN 1 ELSE 0 END) as returned,
                SUM(CASE WHEN event_type = 'IN_TRANSIT' THEN 1 ELSE 0 END) as in_transit
            FROM custody_events
            WHERE event_timestamp >= :start_dt
              AND event_timestamp <= :end_dt
            GROUP BY DATE(event_timestamp)
            ORDER BY DATE(event_timestamp) ASC
        """)
        rows = db.execute(query, {"start_dt": start_dt, "end_dt": end_dt}).fetchall()

        labels = [str(r[0]) for r in rows]
        dispatched_counts = [int(r[1]) for r in rows]
        returned_counts = [int(r[2]) for r in rows]
        in_transit_counts = [int(r[3]) for r in rows]

        return {
            "dates": labels,
            "dispatched": dispatched_counts,
            "returned": returned_counts,
            "in_transit": in_transit_counts
        }

    @classmethod
    def get_inspection_breakdown(cls, db: Session) -> Dict[str, Any]:
        rows = db.query(
            Inspection.condition_status,
            func.count(Inspection.inspection_id)
        ).group_by(Inspection.condition_status).all()

        total = sum(r[1] for r in rows) or 1
        data = {r[0]: int(r[1]) for r in rows}
        percentages = {k: round(v / total * 100.0, 1) for k, v in data.items()}

        return {
            "total_inspections": total,
            "counts": data,
            "percentages": percentages
        }

    @classmethod
    def get_top_locations_by_assets(cls, db: Session, limit: int = 5) -> List[Dict[str, Any]]:
        query = text("""
            SELECT 
                l.location_name,
                COUNT(a.asset_id) as asset_count
            FROM reusable_assets a
            JOIN locations l ON a.current_location_id = l.location_id
            GROUP BY l.location_id, l.location_name
            ORDER BY asset_count DESC
            LIMIT :limit
        """)
        rows = db.execute(query, {"limit": limit}).fetchall()
        return [{"location_name": r[0], "asset_count": int(r[1])} for r in rows]
