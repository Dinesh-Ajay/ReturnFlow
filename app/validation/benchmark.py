"""Read-only benchmark for ReturnFlow operations; see docs/performance_report.md."""
import json
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from app.config import settings
from app.database.session import SessionLocal
from app.generator.__main__ import run_generator
from app.models import CustodyEvent, ReusableAsset
from app.services.asset_service import AssetService
from app.analytics.metrics import AnalyticsService
from app.validation.integrity import IntegrityValidator
from app.validation.anomaly_detection import AnomalyDetectionEngine


def measure(operation, repeats=3):
    operation()  # warm-up
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        operation()
        times.append(time.perf_counter() - start)
    return {"repeats": repeats, "median_seconds": round(statistics.median(times), 6),
            "min_seconds": round(min(times), 6), "max_seconds": round(max(times), 6)}


def run():
    generation = run_generator("full", settings.RANDOM_SEED, load_db=False, export=False)
    db = SessionLocal()
    try:
        counts = {table: int(db.execute(text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
                  for table in ("reusable_assets", "shipments", "custody_events", "deposit_ledger")}
        sample_asset = db.query(ReusableAsset.asset_id).order_by(ReusableAsset.asset_id).first()[0]
        version = db.execute(text("SELECT VERSION()")).scalar_one()
        operations = {
            "database_validation": lambda: IntegrityValidator.validate_all(db),
            "custody_history": lambda: db.query(CustodyEvent).filter(CustodyEvent.asset_id == sample_asset).order_by(CustodyEvent.event_timestamp).all(),
            "asset_search": lambda: AssetService.list_assets(db, page=1, page_size=20, search=sample_asset),
            "anomaly_detection_and_evaluation": lambda: AnomalyDetectionEngine.evaluate_detection_metrics(db),
            "analytics_overview": lambda: AnalyticsService.get_overview_kpis(db),
        }
        database_timings = {name: measure(operation) for name, operation in operations.items()}
    finally:
        db.close()
    generated_events = generation["counts"]["custody_events"]
    result = {
        "measured_at": datetime.now(timezone.utc).isoformat(),
        "environment": {"python": platform.python_version(), "platform": platform.platform(),
                        "database_server_version": version, "database_dialect": "MySQL"},
        "dataset_counts_in_database": counts,
        "generation": {"profile": "full", "seed": settings.RANDOM_SEED,
                       "generated_counts": generation["counts"],
                       "elapsed_seconds": generation["gen_duration"],
                       "custody_events_per_generation_second": round(generated_events / generation["gen_duration"], 2)},
        "database_operation_method": "One warm-up, then 3 perf_counter measurements; median reported.",
        "database_operations": database_timings,
        "database_insertion": {"status": "NOT MEASURED", "reason": "Insertion is not timed by this read-only benchmark. See clean_full_load.log for the separate one-off disposable-database load measurement."},
        "query_plan_review": "Use EXPLAIN ANALYZE on the target MySQL version for production query plans; this report records execution timings only.",
    }
    path = Path(settings.EXPORTS_DIR) / "performance_results.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    run()
