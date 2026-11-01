import os
import csv
import json
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, List, Any
from app.config import settings

def json_serial(obj):
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

class Exporter:
    """
    Exports generated tables to CSV, JSON, and dependency-ordered SQL.
    """

    @classmethod
    def export_all(cls, data: Dict[str, List[Dict[str, Any]]], ground_truth: List[Dict[str, Any]]):
        os.makedirs(settings.GENERATED_DIR, exist_ok=True)
        os.makedirs(settings.GROUND_TRUTH_DIR, exist_ok=True)
        os.makedirs(settings.EXPORTS_DIR, exist_ok=True)

        # 1. Export CSVs for each entity
        for table_name, rows in data.items():
            if not rows:
                continue
            csv_path = os.path.join(settings.GENERATED_DIR, f"{table_name}.csv")
            fieldnames = list(rows[0].keys())
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for r in rows:
                    row_clean = {}
                    for k, v in r.items():
                        if isinstance(v, (datetime, date)):
                            row_clean[k] = v.isoformat()
                        elif isinstance(v, Decimal):
                            row_clean[k] = str(v)
                        else:
                            row_clean[k] = v
                    writer.writerow(row_clean)

        # 2. Export Ground Truth CSV & JSON
        gt_csv_path = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.csv")
        gt_json_path = os.path.join(settings.GROUND_TRUTH_DIR, "ground_truth.json")

        if ground_truth:
            gt_fields = list(ground_truth[0].keys())
            with open(gt_csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=gt_fields)
                writer.writeheader()
                writer.writerows(ground_truth)

            with open(gt_json_path, "w", encoding="utf-8") as f:
                json.dump(ground_truth, f, indent=2, default=json_serial)

        # 3. Export SQL Seed file
        sql_path = os.path.join(settings.EXPORTS_DIR, "returnflow_seed.sql")
        cls.generate_sql_seed(data, ground_truth, sql_path)

    @classmethod
    def generate_sql_seed(cls, data: Dict[str, List[Dict[str, Any]]], ground_truth: List[Dict[str, Any]], output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("-- ReturnFlow Synthetic Demonstration Seed Data\n")
            f.write("-- Generated with fixed seed\n")
            f.write("USE returnflow_db;\n\n")
            f.write("-- Foreign keys remain enabled. Import only into an empty target.\n\n")

            insertion_order = [
                ("asset_types", data.get("asset_types", [])),
                ("owners", data.get("owners", [])),
                ("locations", data.get("locations", [])),
                ("reusable_assets", data.get("assets", [])),
                ("shipments", data.get("shipments", [])),
                ("shipment_assets", data.get("shipment_assets", [])),
                ("custody_events", data.get("custody_events", [])),
                ("return_authorizations", data.get("return_authorizations", [])),
                ("return_authorization_assets", data.get("rma_assets", [])),
                ("inspections", data.get("inspections", [])),
                ("repairs", data.get("repairs", [])),
                ("deposit_ledger", data.get("deposit_ledger", []))
            ]

            for table_name, rows in insertion_order:
                if not rows:
                    continue
                f.write(f"-- Table: {table_name} ({len(rows)} rows)\n")
                cols = list(rows[0].keys())
                col_str = ", ".join(cols)
                batch_size = 500
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    val_strs = []
                    for r in batch:
                        row_vals = []
                        for col in cols:
                            val = r.get(col)
                            if val is None:
                                row_vals.append("NULL")
                            elif isinstance(val, (int, float, Decimal)):
                                row_vals.append(str(val))
                            elif isinstance(val, bool):
                                row_vals.append("1" if val else "0")
                            elif isinstance(val, (datetime, date)):
                                row_vals.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                            else:
                                esc_val = str(val).replace("'", "''").replace("\\", "\\\\")
                                row_vals.append(f"'{esc_val}'")
                        val_strs.append(f"({', '.join(row_vals)})")
                    f.write(f"INSERT INTO {table_name} ({col_str}) VALUES\n" + ",\n".join(val_strs) + ";\n\n")

            # Also seed anomaly records
            if ground_truth:
                f.write(f"-- Table: anomaly_records ({len(ground_truth)} rows)\n")
                ar_cols = ["issue_id", "affected_asset_id", "affected_record_id", "entity_name", "issue_type", "severity", "description", "ground_truth_label", "expected_decision", "is_injected"]
                col_str = ", ".join(ar_cols)
                val_strs = []
                for gt in ground_truth:
                    expl = gt["explanation"].replace("'", "''")
                    row_vals = [
                        f"'{gt['issue_id']}'",
                        f"'{gt['asset_id']}'" if gt['asset_id'] else "NULL",
                        f"'{gt['record_id']}'",
                        f"'{gt['entity_name']}'",
                        f"'{gt['issue_type']}'",
                        f"'{gt['severity']}'",
                        f"'{expl}'",
                        f"'{gt['ground_truth_label']}'",
                        f"'{gt['expected_decision']}'",
                        "1"
                    ]
                    val_strs.append(f"({', '.join(row_vals)})")
                f.write(f"INSERT INTO anomaly_records ({col_str}) VALUES\n" + ",\n".join(val_strs) + ";\n\n")

            f.write("-- End of synthetic seed.\n")
