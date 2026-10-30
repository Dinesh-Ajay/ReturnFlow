"""Read-only database row-count audit: ``python -m app.validation.counts``."""
from app.database.session import SessionLocal
from app.models import (
    AssetType, Owner, Location, ReusableAsset, Shipment, ShipmentAsset,
    CustodyEvent, ReturnAuthorization, ReturnAuthorizationAsset,
    Inspection, Repair, DepositLedger, AnomalyRecord,
)

EXPECTED_MINIMUMS = {
    "reusable_assets": 20_000,
    "shipments": 10_000,
    "custody_events": 100_000,
}
MODELS = [
    AssetType, Owner, Location, ReusableAsset, Shipment, ShipmentAsset,
    CustodyEvent, ReturnAuthorization, ReturnAuthorizationAsset,
    Inspection, Repair, DepositLedger, AnomalyRecord,
]


def get_counts(db):
    return {model.__tablename__: db.query(model).count() for model in MODELS}


def main():
    db = SessionLocal()
    try:
        counts = get_counts(db)
    finally:
        db.close()
    print(f"{'Entity':34} {'Expected minimum':>18} {'Actual':>12} {'Status':>10}")
    failed = False
    for table, actual in counts.items():
        expected = EXPECTED_MINIMUMS.get(table)
        status = "PASS" if expected is None or actual >= expected else "FAIL"
        failed |= status == "FAIL"
        print(f"{table:34} {str(expected if expected is not None else 'inspect'):>18} {actual:12,d} {status:>10}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
