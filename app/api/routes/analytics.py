from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.analytics.metrics import AnalyticsService
from app.services.deposit_service import DepositService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

def parse_iso_date(date_str: Optional[str]) -> Optional[date]:
    if not date_str:
        return None
    try:
        return date.fromisoformat(date_str.strip())
    except Exception:
        return None

@router.get("/overview")
def get_analytics_overview(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    s_date = parse_iso_date(start_date)
    e_date = parse_iso_date(end_date)
    return AnalyticsService.get_overview_kpis(db, start_date=s_date, end_date=e_date)

@router.get("/trends")
def get_analytics_movement_trends(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    days: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    s_date = parse_iso_date(start_date)
    e_date = parse_iso_date(end_date)
    return AnalyticsService.get_asset_movement_trends(db, start_date=s_date, end_date=e_date, days=days)

@router.get("/returns")
def get_returns_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    s_date = parse_iso_date(start_date)
    e_date = parse_iso_date(end_date)
    kpis = AnalyticsService.get_overview_kpis(db, start_date=s_date, end_date=e_date)
    trends = AnalyticsService.get_asset_movement_trends(db, start_date=s_date, end_date=e_date)
    return {
        "return_rate_pct": kpis["return_rate_pct"],
        "total_returned": kpis["period_returned"] if kpis["period_returned"] > 0 else kpis["total_returned"],
        "total_dispatched": kpis["period_dispatched"] if kpis["period_dispatched"] > 0 else kpis["total_custody_events"],
        "overdue_count": kpis["overdue_count"],
        "overdue_rate_pct": kpis["overdue_rate_pct"],
        "movement_trends": trends
    }

@router.get("/assets")
def get_assets_analytics(db: Session = Depends(get_db)):
    kpis = AnalyticsService.get_overview_kpis(db)
    top_locs = AnalyticsService.get_top_locations_by_assets(db, limit=5)
    inspections = AnalyticsService.get_inspection_breakdown(db)
    return {
        "total_assets": kpis["total_assets"],
        "status_distribution": kpis["status_distribution"],
        "top_locations": top_locs,
        "inspection_results": inspections,
        "loss_rate_pct": kpis["loss_rate_pct"],
        "damage_rate_pct": kpis["damage_rate_pct"]
    }

@router.get("/financials")
def get_financials_analytics(db: Session = Depends(get_db)):
    return DepositService.get_portfolio_financial_summary(db)
