from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.analytics.metrics import AnalyticsService
from app.services.deposit_service import DepositService

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/overview")
def get_analytics_overview(db: Session = Depends(get_db)):
    return AnalyticsService.get_overview_kpis(db)

@router.get("/returns")
def get_returns_analytics(db: Session = Depends(get_db)):
    kpis = AnalyticsService.get_overview_kpis(db)
    trends = AnalyticsService.get_asset_movement_trends(db, days=22)
    return {
        "return_rate_pct": kpis["return_rate_pct"],
        "total_returned": kpis["total_returned"],
        "total_dispatched": kpis["total_custody_events"],
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
