import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func, and_, or_
from app.database.base import Base
from app.models.asset import ReusableAsset
from app.models.asset_type import AssetType
from app.models.owner import Owner
from app.models.location import Location
from app.models.shipment import Shipment
from app.models.custody_event import CustodyEvent
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.deposit_ledger import DepositLedger

class IntegrityValidator:
    """
    Validates Primary Keys, Foreign Keys, Unique constraints, and ID formatting.
    """

    ID_PATTERNS = {
        "asset_id": re.compile(r"^ASSET-\d{7}$"),
        "shipment_id": re.compile(r"^SHP-\d{4}-\d{6}$"),
        "rma_id": re.compile(r"^RMA-\d{4}-\d{6}$"),
        "custody_event_id": re.compile(r"^CUST-ASSET-\d{7}-\d{6}$"),
        "inspection_id": re.compile(r"^INSP-\d{4}-\d{6}$"),
        "repair_id": re.compile(r"^REP-\d{4}-\d{6}$"),
    }

    @classmethod
    def validate_all(cls, db: Session) -> Dict[str, Any]:
        results = {
            "name": "Referential & Structural Integrity Validation",
            "passed": True,
            "checks": []
        }

        # 1. Primary Key Format Validation for ReusableAsset
        assets = db.query(ReusableAsset.asset_id).all()
        invalid_asset_ids = [a[0] for a in assets if not cls.ID_PATTERNS["asset_id"].match(a[0])]
        results["checks"].append({
            "check": "Asset ID Pattern (ASSET-XXXXXXX)",
            "total_checked": len(assets),
            "passed": len(invalid_asset_ids) == 0,
            "failed_count": len(invalid_asset_ids),
            "affected_ids": invalid_asset_ids[:5]
        })

        # 2. Primary Key Format Validation for Shipment
        shipments = db.query(Shipment.shipment_id).all()
        invalid_shp_ids = [s[0] for s in shipments if not cls.ID_PATTERNS["shipment_id"].match(s[0])]
        results["checks"].append({
            "check": "Shipment ID Pattern (SHP-YYYY-XXXXXX)",
            "total_checked": len(shipments),
            "passed": len(invalid_shp_ids) == 0,
            "failed_count": len(invalid_shp_ids),
            "affected_ids": invalid_shp_ids[:5]
        })

        # 3. Foreign Key: Assets with missing AssetType
        orphaned_assets_type = db.execute(text(
            "SELECT a.asset_id FROM reusable_assets a LEFT JOIN asset_types t ON a.asset_type_id = t.asset_type_id WHERE t.asset_type_id IS NULL"
        )).fetchall()
        results["checks"].append({
            "check": "Asset -> AssetType Foreign Key Reference",
            "total_checked": len(assets),
            "passed": len(orphaned_assets_type) == 0,
            "failed_count": len(orphaned_assets_type),
            "affected_ids": [r[0] for r in orphaned_assets_type[:5]]
        })

        # 4. Foreign Key: Custody Events referencing missing Asset
        total_events = db.query(CustodyEvent).count()
        orphaned_events = db.execute(text(
            "SELECT ce.custody_event_id FROM custody_events ce LEFT JOIN reusable_assets a ON ce.asset_id = a.asset_id WHERE a.asset_id IS NULL"
        )).fetchall()
        results["checks"].append({
            "check": "CustodyEvent -> ReusableAsset Foreign Key Reference",
            "total_checked": total_events,
            "passed": len(orphaned_events) == 0,
            "failed_count": len(orphaned_events),
            "affected_ids": [r[0] for r in orphaned_events[:5]]
        })

        # 5. Foreign Key: Deposit Ledger referencing missing Asset
        total_ledger = db.query(DepositLedger).count()
        orphaned_ledger = db.execute(text(
            "SELECT dl.ledger_id FROM deposit_ledger dl LEFT JOIN reusable_assets a ON dl.asset_id = a.asset_id WHERE a.asset_id IS NULL"
        )).fetchall()
        results["checks"].append({
            "check": "DepositLedger -> ReusableAsset Foreign Key Reference",
            "total_checked": total_ledger,
            "passed": len(orphaned_ledger) == 0,
            "failed_count": len(orphaned_ledger),
            "affected_ids": [r[0] for r in orphaned_ledger[:5]]
        })

        # Inspect every mapped table for PK nulls/duplicates, required or
        # optional FK validity, and declared unique business identifiers.
        # Database constraints should prevent most of these; these checks
        # also detect legacy rows loaded with constraints disabled.
        table_counts = {}
        pk_violations = 0
        fk_violations = 0
        orphan_records = 0
        duplicate_identifiers = 0
        for table in Base.metadata.sorted_tables:
            count = int(db.execute(select(func.count()).select_from(table)).scalar_one())
            table_counts[table.name] = count
            pks = list(table.primary_key.columns)
            if pks:
                null_clause = or_(*(column.is_(None) for column in pks))
                null_count = int(db.execute(select(func.count()).select_from(table).where(null_clause)).scalar_one())
                duplicate_query = select(func.count()).select_from(
                    select(*pks).select_from(table).group_by(*pks).having(func.count() > 1).subquery()
                )
                duplicate_pk_count = int(db.execute(duplicate_query).scalar_one())
                pk_violations += null_count + duplicate_pk_count
                if null_count or duplicate_pk_count:
                    results["checks"].append({"check": f"{table.name} primary key validity", "total_checked": count,
                                              "passed": False, "failed_count": null_count + duplicate_pk_count})
            for fk in table.foreign_key_constraints:
                pairs = list(fk.elements)
                target = pairs[0].column.table
                target_alias = target.alias()
                conditions = [element.parent == target_alias.c[element.column.name] for element in pairs]
                required = and_(*(element.parent.is_not(None) for element in pairs))
                target_pk_name = list(target.primary_key.columns)[0].name
                missing = select(func.count()).select_from(table.outerjoin(target_alias, and_(*conditions))).where(
                    and_(required, target_alias.c[target_pk_name].is_(None))
                )
                failures = int(db.execute(missing).scalar_one())
                fk_violations += failures
                orphan_records += failures
                if failures:
                    results["checks"].append({"check": f"{table.name} foreign key {fk.name or 'reference'}",
                                              "total_checked": count, "passed": False, "failed_count": failures})
            for constraint in table.constraints:
                if constraint is table.primary_key or not getattr(constraint, "columns", None):
                    continue
                if constraint.__class__.__name__ not in {"UniqueConstraint"}:
                    continue
                columns = list(constraint.columns)
                duplicates = select(func.count()).select_from(
                    select(*columns).select_from(table).group_by(*columns).having(func.count() > 1).subquery()
                )
                found = int(db.execute(duplicates).scalar_one())
                duplicate_identifiers += found
                if found:
                    results["checks"].append({"check": f"{table.name} unique identifier {constraint.name or 'constraint'}",
                                              "total_checked": count, "passed": False, "failed_count": found})

        # Overall pass status
        results["total_records_checked"] = sum(table_counts.values())
        results["table_counts"] = table_counts
        results["primary_key_violations"] = pk_violations
        results["foreign_key_violations"] = fk_violations
        results["orphan_records"] = orphan_records
        results["duplicate_identifiers"] = duplicate_identifiers
        results["passed"] = all(c["passed"] for c in results["checks"])
        return results
