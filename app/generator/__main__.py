import argparse
import random
import time
import sys
import hashlib
import json
from decimal import Decimal
from datetime import date, datetime, timezone
from sqlalchemy import text
from app.config import settings
from app.database.session import SessionLocal
from app.database.connection import engine
from app.utils.id_generator import IDGenerator
from app.utils.logging_config import setup_logging, logger
from app.generator.config import PROFILES
from app.generator.master_generator import MasterGenerator
from app.generator.transaction_generator import TransactionGenerator
from app.generator.anomaly_injector import AnomalyInjector
from app.generator.exporter import Exporter
from app.models import (
    Base, AssetType, Owner, Location, ReusableAsset, Shipment,
    ShipmentAsset, CustodyEvent, ReturnAuthorization,
    ReturnAuthorizationAsset, Inspection, Repair, DepositLedger, AnomalyRecord
)

def logical_checksums(data, ground_truth):
    """Hash generated business data while excluding database-managed timestamps."""
    def normalize(value):
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        if isinstance(value, Decimal):
            return str(value)
        return value

    checksums = {}
    excluded = {"created_at", "updated_at"}
    for name, rows in data.items():
        logical_rows = [{key: normalize(value) for key, value in row.items() if key not in excluded} for row in rows]
        payload = json.dumps(logical_rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        checksums[name] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    gt_payload = json.dumps(ground_truth, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=normalize)
    checksums["ground_truth"] = hashlib.sha256(gt_payload.encode("utf-8")).hexdigest()
    return checksums

def run_generator(profile_name: str = "starter", seed: int = 20261022, load_db: bool = True,
                  export: bool = True, replace_existing: bool = False):
    setup_logging()
    logger.info(f"Starting ReturnFlow Synthetic Data Generator with profile='{profile_name}', seed={seed}")

    if profile_name not in PROFILES:
        raise ValueError(f"Unknown profile: {profile_name}. Available: {list(PROFILES.keys())}")

    p_conf = PROFILES[profile_name]
    rng = random.Random(seed)
    id_gen = IDGenerator(year=2026)

    t0_gen = time.perf_counter()

    # Step 1: Master generation
    logger.info("Generating Master records (AssetTypes, Owners, Locations, ReusableAssets)...")
    m_gen = MasterGenerator(rng, id_gen)
    asset_types = m_gen.generate_asset_types(p_conf["num_asset_types"])
    owners = m_gen.generate_owners(p_conf["num_owners"])
    locations = m_gen.generate_locations(p_conf["num_locations"])
    assets = m_gen.generate_assets(p_conf["num_assets"], asset_types, owners, locations)

    asset_types_map = {at["asset_type_id"]: at for at in asset_types}

    # Step 2: Transaction generation
    logger.info("Generating Workflows (Shipments, CustodyEvents, RMAs, Inspections, Repairs, DepositLedger)...")
    tx_gen = TransactionGenerator(rng, id_gen, reference_date=settings.REFERENCE_DATE)
    workflows = tx_gen.generate_workflows(
        assets=assets,
        asset_types_map=asset_types_map,
        owners=owners,
        locations=locations,
        num_shipments=p_conf["num_shipments"],
        target_custody_events=p_conf["target_custody_events"]
    )

    # Step 3: Anomaly injection
    logger.info(f"Injecting 5 required anomaly scenarios ({p_conf['num_anomalies_each']} instances each)...")
    injector = AnomalyInjector(rng, id_gen)
    ground_truth = injector.inject_all_anomalies(
        assets=workflows["assets"],
        custody_events=workflows["custody_events"],
        deposit_ledger=workflows["deposit_ledger"],
        repairs=workflows["repairs"],
        locations=locations,
        owners=owners,
        count_per_scenario=p_conf["num_anomalies_each"]
    )

    t1_gen = time.perf_counter()
    gen_duration = t1_gen - t0_gen
    logger.info(f"Data Generation completed in {gen_duration:.2f} seconds.")

    all_data = {
        "asset_types": asset_types,
        "owners": owners,
        "locations": locations,
        "assets": workflows["assets"],
        "shipments": workflows["shipments"],
        "shipment_assets": workflows["shipment_assets"],
        "custody_events": workflows["custody_events"],
        "return_authorizations": workflows["return_authorizations"],
        "rma_assets": workflows["rma_assets"],
        "inspections": workflows["inspections"],
        "repairs": workflows["repairs"],
        "deposit_ledger": workflows["deposit_ledger"]
    }

    # Step 4: Export CSVs, JSON ground truth, and SQL seed
    logger.info("Exporting generated files to disk..." if export else "Skipping generated-file export for an in-memory run...")
    if export:
        Exporter.export_all(all_data, ground_truth)
    checksums = logical_checksums(all_data, ground_truth)

    # Step 5: Database Insertion
    db_duration = 0.0
    if load_db:
        logger.info("Loading records into MySQL database via batch operations...")
        t0_db = time.perf_counter()
        db = SessionLocal()
        try:
            target_tables = [
                "anomaly_records", "deposit_ledger", "repairs", "inspections",
                "return_authorization_assets", "return_authorizations",
                "custody_events", "shipment_assets", "shipments",
                "reusable_assets", "locations", "owners", "asset_types"
            ]
            populated = {
                table: int(db.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
                for table in target_tables
            }
            existing_rows = {table: count for table, count in populated.items() if count}
            if existing_rows and not replace_existing:
                raise RuntimeError(
                    "Refusing to replace populated database tables. Use a dedicated empty database, "
                    "or explicitly pass --replace-existing after backing up the target. "
                    f"Populated tables: {existing_rows}"
                )

            # Clear existing data in reverse dependency order
            db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
            for tbl in target_tables:
                db.execute(text(f"TRUNCATE TABLE {tbl};"))
            db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            db.commit()

            # Batch insert records
            batch_size = 1000

            def bulk_insert(model_cls, rows):
                for i in range(0, len(rows), batch_size):
                    chunk = rows[i:i + batch_size]
                    db.bulk_insert_mappings(model_cls, chunk)
                db.commit()

            bulk_insert(AssetType, asset_types)
            bulk_insert(Owner, owners)
            bulk_insert(Location, locations)
            bulk_insert(ReusableAsset, workflows["assets"])
            bulk_insert(Shipment, workflows["shipments"])
            bulk_insert(ShipmentAsset, workflows["shipment_assets"])
            bulk_insert(CustodyEvent, workflows["custody_events"])
            bulk_insert(ReturnAuthorization, workflows["return_authorizations"])
            bulk_insert(ReturnAuthorizationAsset, workflows["rma_assets"])
            bulk_insert(Inspection, workflows["inspections"])
            bulk_insert(Repair, workflows["repairs"])
            bulk_insert(DepositLedger, workflows["deposit_ledger"])

            # Bulk insert anomaly records as ground truth baselines
            ar_rows = [
                {
                    "issue_id": gt["issue_id"],
                    "affected_asset_id": gt["asset_id"],
                    "affected_record_id": gt["record_id"],
                    "entity_name": gt["entity_name"],
                    "issue_type": gt["issue_type"],
                    "severity": gt["severity"],
                    "description": gt["explanation"],
                    "ground_truth_label": gt["ground_truth_label"],
                    "expected_decision": gt["expected_decision"],
                    "detection_status": "OPEN",
                    "is_injected": True,
                    "created_at": datetime.now(timezone.utc)
                }
                for gt in ground_truth
            ]
            bulk_insert(AnomalyRecord, ar_rows)

            t1_db = time.perf_counter()
            db_duration = t1_db - t0_db
            logger.info(f"Database insertion completed in {db_duration:.2f} seconds.")

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to load into database: {e}")
            raise
        finally:
            db.close()

    logger.info("Summary of Generated Data:")
    logger.info(f"  Asset Types:               {len(asset_types)}")
    logger.info(f"  Owners:                    {len(owners)}")
    logger.info(f"  Locations:                 {len(locations)}")
    logger.info(f"  Reusable Assets:           {len(workflows['assets'])}")
    logger.info(f"  Shipments:                 {len(workflows['shipments'])}")
    logger.info(f"  Custody Events:            {len(workflows['custody_events'])}")
    logger.info(f"  Return Authorizations:     {len(workflows['return_authorizations'])}")
    logger.info(f"  Inspections:               {len(workflows['inspections'])}")
    logger.info(f"  Repairs:                   {len(workflows['repairs'])}")
    logger.info(f"  Deposit Ledger Entries:    {len(workflows['deposit_ledger'])}")
    logger.info(f"  Injected Anomalies:        {len(ground_truth)}")
    logger.info(f"  Data Gen Time:             {gen_duration:.3f}s")
    logger.info(f"  DB Load Time:              {db_duration:.3f}s")

    return {
        "profile": profile_name,
        "seed": seed,
        "gen_duration": gen_duration,
        "db_duration": db_duration,
        "counts": {k: len(v) for k, v in all_data.items()},
        "ground_truth_count": len(ground_truth),
        "ground_truth_records": ground_truth,
        "checksums": checksums
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ReturnFlow Synthetic Data Generator")
    parser.add_argument("--profile", choices=["starter", "full"], default="starter", help="Dataset volume profile")
    parser.add_argument("--seed", type=int, default=settings.RANDOM_SEED, help="Deterministic random seed")
    parser.add_argument("--no-db", action="store_true", help="Skip database insertion")
    parser.add_argument("--replace-existing", action="store_true", help="Explicitly truncate populated target tables before loading; use only for a disposable database")
    args = parser.parse_args()

    run_generator(profile_name=args.profile, seed=args.seed, load_db=not args.no_db,
                  replace_existing=args.replace_existing)
