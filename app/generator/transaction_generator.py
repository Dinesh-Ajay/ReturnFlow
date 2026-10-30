import random
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from app.utils.id_generator import IDGenerator

def make_utc_dt(d: date, hour: int = 10, minute: int = 0) -> datetime:
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=timezone.utc)

class TransactionGenerator:
    """
    Generates realistic, chronologically consistent transaction workflows:
    - Shipments & ShipmentAsset links
    - Immutable CustodyEvents
    - ReturnAuthorizations & RMAAsset links
    - Post-return Inspections
    - Repairs & Repair completion
    - DepositLedger transactions
    - Materialized current asset state updates
    """

    def __init__(self, rng: random.Random, id_gen: IDGenerator, reference_date: date = date(2026, 10, 22)):
        self.rng = rng
        self.id_gen = id_gen
        self.ref_date = reference_date

    def generate_workflows(
        self,
        assets: List[Dict[str, Any]],
        asset_types_map: Dict[int, Dict[str, Any]],
        owners: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
        num_shipments: int,
        target_custody_events: int
    ) -> Dict[str, Any]:
        carriers = [o for o in owners if o["owner_type"] == "CARRIER"]
        if not carriers:
            carriers = owners[:2]
        customers = [o for o in owners if o["owner_type"] == "CUSTOMER"]
        if not customers:
            customers = owners[2:5]
        suppliers = [o for o in owners if o["owner_type"] in ("SUPPLIER", "INTERNAL_OPERATIONS")]
        if not suppliers:
            suppliers = [owners[0]]
        wh_operators = [o for o in owners if o["owner_type"] == "WAREHOUSE_OPERATOR"]
        if not wh_operators:
            wh_operators = suppliers

        origin_locs = [l for l in locations if l["location_type"] in ("DISTRIBUTION_CENTER", "WAREHOUSE", "SUPPLIER")]
        dest_locs = [l for l in locations if l["location_type"] in ("CUSTOMER_SITE", "DISTRIBUTION_CENTER", "WAREHOUSE")]
        repair_locs = [l for l in locations if l["location_type"] == "REPAIR_CENTER"]
        if not repair_locs:
            repair_locs = locations[:2]

        shipments = []
        shipment_assets = []
        custody_events = []
        return_authorizations = []
        rma_assets = []
        inspections = []
        repairs = []
        deposit_ledger = []

        total_assets = len(assets)
        # Partition assets into realistic operational cohorts:
        # 1. 60%: Completed lifecycle cycle (dispatched -> delivered -> returned -> inspected [good/damaged])
        # 2. 18%: Active In Transit / Recently Dispatched
        # 3. 12%: In Custody (Normal return pending)
        # 4. 6%: Overdue (Dispatched 35-55 days ago, return_due_days exceeded)
        # 5. 2%: Lost (Dispatched >60 days ago, past loss threshold)
        # 6. 2%: Under Repair / In Repair facility

        # Let's shuffle asset indices deterministically
        indices = list(range(total_assets))
        self.rng.shuffle(indices)

        c_completed = int(total_assets * 0.60)
        c_transit = int(total_assets * 0.18)
        c_custody = int(total_assets * 0.12)
        c_overdue = int(total_assets * 0.06)
        c_lost = int(total_assets * 0.02)
        # remainder goes to repair cohort

        cohorts = {
            "COMPLETED": indices[:c_completed],
            "IN_TRANSIT": indices[c_completed:c_completed + c_transit],
            "IN_CUSTODY": indices[c_completed + c_transit:c_completed + c_transit + c_custody],
            "OVERDUE": indices[c_completed + c_transit + c_custody:c_completed + c_transit + c_custody + c_overdue],
            "LOST": indices[c_completed + c_transit + c_custody + c_overdue:c_completed + c_transit + c_custody + c_overdue + c_lost],
            "REPAIR": indices[c_completed + c_transit + c_custody + c_overdue + c_lost:]
        }

        # Build shipments grouping assets together
        # Calculate assets per shipment to distribute across num_shipments
        all_assigned_assets = []
        for cohort_name, c_indices in cohorts.items():
            for idx in c_indices:
                all_assigned_assets.append((assets[idx], cohort_name))

        chunk_size = max(1, len(all_assigned_assets) // num_shipments) if num_shipments > 0 else 1

        shipment_index = 0
        current_asset_ptr = 0

        while current_asset_ptr < len(all_assigned_assets):
            shipment_index += 1
            shp_id = self.id_gen.next_shipment_id()
            batch = all_assigned_assets[current_asset_ptr:current_asset_ptr + chunk_size]
            current_asset_ptr += chunk_size

            carrier = self.rng.choice(carriers)
            origin = self.rng.choice(origin_locs)
            dest = self.rng.choice(dest_locs)
            while dest["location_id"] == origin["location_id"] and len(dest_locs) > 1:
                dest = self.rng.choice(dest_locs)

            # Determine dispatch date based on cohort of first asset in batch
            sample_asset, sample_cohort = batch[0]
            atype = asset_types_map[sample_asset["asset_type_id"]]

            if sample_cohort == "COMPLETED":
                days_ago = self.rng.randint(25, 90)
            elif sample_cohort == "IN_TRANSIT":
                days_ago = self.rng.randint(1, 4)
            elif sample_cohort == "IN_CUSTODY":
                days_ago = self.rng.randint(6, 18)
            elif sample_cohort == "OVERDUE":
                days_ago = self.rng.randint(atype["return_due_days"] + 5, atype["loss_threshold_days"] - 2)
            elif sample_cohort == "LOST":
                days_ago = self.rng.randint(atype["loss_threshold_days"] + 10, atype["loss_threshold_days"] + 60)
            else:  # REPAIR
                days_ago = self.rng.randint(20, 50)

            dispatch_d = self.ref_date - timedelta(days=days_ago)
            dispatch_dt = make_utc_dt(dispatch_d, hour=8, minute=30)
            exp_delivery_dt = dispatch_dt + timedelta(days=self.rng.randint(2, 4))

            # Shipment status
            if sample_cohort == "IN_TRANSIT":
                shipment_status = "IN_TRANSIT"
                actual_deliv_dt = None
            elif sample_cohort in ("COMPLETED", "IN_CUSTODY", "OVERDUE", "REPAIR"):
                shipment_status = "DELIVERED"
                actual_deliv_dt = exp_delivery_dt + timedelta(hours=self.rng.randint(-4, 12))
            else:  # LOST
                shipment_status = "DELIVERED" if self.rng.random() > 0.3 else "IN_TRANSIT"
                actual_deliv_dt = exp_delivery_dt if shipment_status == "DELIVERED" else None

            shipment = {
                "shipment_id": shp_id,
                "origin_location_id": origin["location_id"],
                "destination_location_id": dest["location_id"],
                "carrier_owner_id": carrier["owner_id"],
                "dispatch_date": dispatch_dt,
                "expected_delivery_date": exp_delivery_dt,
                "actual_delivery_date": actual_deliv_dt,
                "shipment_status": shipment_status,
                "tracking_reference": f"TRK-{shp_id}"
            }
            shipments.append(shipment)

            # Process each asset in this shipment batch
            for asset_item, cohort in batch:
                asset_id = asset_item["asset_id"]
                shipment_assets.append({
                    "shipment_id": shp_id,
                    "asset_id": asset_id,
                    "assigned_at": dispatch_dt
                })

                # Event 1: DISPATCHED
                ce_disp = {
                    "custody_event_id": self.id_gen.next_custody_event_id(asset_id),
                    "asset_id": asset_id,
                    "shipment_id": shp_id,
                    "from_owner_id": asset_item["owner_id"],
                    "to_owner_id": carrier["owner_id"],
                    "from_location_id": origin["location_id"],
                    "to_location_id": dest["location_id"],
                    "actor_owner_id": carrier["owner_id"],
                    "event_type": "DISPATCHED",
                    "event_timestamp": dispatch_dt,
                    "event_reference": shp_id,
                    "notes": f"Dispatched from {origin['location_name']} via {carrier['owner_name']}"
                }
                custody_events.append(ce_disp)

                # Deposit charge transaction on dispatch
                customer = self.rng.choice(customers)
                dep_amount = asset_item["deposit_amount"]
                deposit_ledger.append({
                    "asset_id": asset_id,
                    "owner_id": customer["owner_id"],
                    "shipment_id": shp_id,
                    "rma_id": None,
                    "transaction_type": "DEPOSIT_CHARGE",
                    "transaction_amount": dep_amount,
                    "transaction_reference": f"DEP-{shp_id}-{asset_id}",
                    "transaction_date": dispatch_dt,
                    "related_ledger_id": None,
                    "description": f"Initial deposit charge for asset {asset_id}"
                })

                if cohort == "IN_TRANSIT":
                    # Currently in transit
                    asset_item["asset_status"] = "IN_TRANSIT"
                    asset_item["current_location_id"] = None
                    asset_item["current_custodian_owner_id"] = carrier["owner_id"]
                    asset_item["last_event_at"] = dispatch_dt
                    continue

                # Event 2: RECEIVED by destination customer
                received_dt = actual_deliv_dt or (dispatch_dt + timedelta(days=2))
                ce_recv = {
                    "custody_event_id": self.id_gen.next_custody_event_id(asset_id),
                    "asset_id": asset_id,
                    "shipment_id": shp_id,
                    "from_owner_id": carrier["owner_id"],
                    "to_owner_id": customer["owner_id"],
                    "from_location_id": origin["location_id"],
                    "to_location_id": dest["location_id"],
                    "actor_owner_id": customer["owner_id"],
                    "event_type": "RECEIVED",
                    "event_timestamp": received_dt,
                    "event_reference": shp_id,
                    "notes": f"Delivered and received at {dest['location_name']}"
                }
                custody_events.append(ce_recv)

                if cohort == "IN_CUSTODY":
                    asset_item["asset_status"] = "IN_CUSTODY"
                    asset_item["current_location_id"] = dest["location_id"]
                    asset_item["current_custodian_owner_id"] = customer["owner_id"]
                    asset_item["last_event_at"] = received_dt
                    continue

                if cohort == "OVERDUE":
                    asset_item["asset_status"] = "IN_CUSTODY"
                    asset_item["current_location_id"] = dest["location_id"]
                    asset_item["current_custodian_owner_id"] = customer["owner_id"]
                    asset_item["last_event_at"] = received_dt
                    continue

                if cohort == "LOST":
                    # Mark as lost with event
                    lost_dt = dispatch_dt + timedelta(days=atype["loss_threshold_days"] + 5)
                    ce_lost = {
                        "custody_event_id": self.id_gen.next_custody_event_id(asset_id),
                        "asset_id": asset_id,
                        "shipment_id": shp_id,
                        "from_owner_id": customer["owner_id"],
                        "to_owner_id": None,
                        "from_location_id": dest["location_id"],
                        "to_location_id": None,
                        "actor_owner_id": customer["owner_id"],
                        "event_type": "LOST_REPORTED",
                        "event_timestamp": lost_dt,
                        "event_reference": f"LOST-{asset_id}",
                        "notes": "Asset overdue beyond loss threshold, declared lost"
                    }
                    custody_events.append(ce_lost)
                    # Loss charge in ledger
                    deposit_ledger.append({
                        "asset_id": asset_id,
                        "owner_id": customer["owner_id"],
                        "shipment_id": shp_id,
                        "rma_id": None,
                        "transaction_type": "LOSS_CHARGE",
                        "transaction_amount": dep_amount,
                        "transaction_reference": f"LOSS-{asset_id}",
                        "transaction_date": lost_dt,
                        "related_ledger_id": None,
                        "description": f"Loss charge for unreturned asset {asset_id}"
                    })
                    asset_item["asset_status"] = "LOST"
                    asset_item["current_location_id"] = None
                    asset_item["current_custodian_owner_id"] = None
                    asset_item["last_event_at"] = lost_dt
                    continue

                # For COMPLETED and REPAIR cohorts: Process Return (RMA)
                return_dt = received_dt + timedelta(days=self.rng.randint(7, 20))
                rma_id = self.id_gen.next_rma_id()
                ret_loc = origin  # returned back to original distribution center

                rma = {
                    "rma_id": rma_id,
                    "requesting_owner_id": customer["owner_id"],
                    "receiving_owner_id": asset_item["owner_id"],
                    "return_location_id": ret_loc["location_id"],
                    "requested_date": return_dt - timedelta(days=2),
                    "approved_date": return_dt - timedelta(days=1),
                    "expected_return_date": return_dt,
                    "actual_return_date": return_dt,
                    "rma_status": "COMPLETED",
                    "reason": "Scheduled reusable container return cycle"
                }
                return_authorizations.append(rma)

                rma_assets.append({
                    "rma_id": rma_id,
                    "asset_id": asset_id,
                    "return_condition": "GOOD" if cohort == "COMPLETED" else "DAMAGED",
                    "received_at": return_dt
                })

                # Event: RETURNED
                ce_ret = {
                    "custody_event_id": self.id_gen.next_custody_event_id(asset_id),
                    "asset_id": asset_id,
                    "shipment_id": None,
                    "from_owner_id": customer["owner_id"],
                    "to_owner_id": asset_item["owner_id"],
                    "from_location_id": dest["location_id"],
                    "to_location_id": ret_loc["location_id"],
                    "actor_owner_id": asset_item["owner_id"],
                    "event_type": "RETURNED",
                    "event_timestamp": return_dt,
                    "event_reference": rma_id,
                    "notes": f"Returned to {ret_loc['location_name']} via RMA {rma_id}"
                }
                custody_events.append(ce_ret)

                # Inspection
                insp_dt = return_dt + timedelta(hours=self.rng.randint(4, 24))
                insp_id = self.id_gen.next_inspection_id()
                is_damaged = (cohort == "REPAIR") or (cohort == "COMPLETED" and self.rng.random() < 0.08)

                condition = "DAMAGED" if is_damaged else "GOOD"
                severity = self.rng.choice(["MINOR", "MODERATE"]) if is_damaged else "NONE"

                inspections.append({
                    "inspection_id": insp_id,
                    "asset_id": asset_id,
                    "rma_id": rma_id,
                    "inspector_owner_id": asset_item["owner_id"],
                    "inspection_date": insp_dt,
                    "condition_status": condition,
                    "damage_severity": severity,
                    "requires_repair": is_damaged,
                    "inspection_notes": f"Inspection passed condition: {condition}"
                })

                if not is_damaged:
                    # Deposit refund for undamaged asset
                    deposit_ledger.append({
                        "asset_id": asset_id,
                        "owner_id": customer["owner_id"],
                        "shipment_id": shp_id,
                        "rma_id": rma_id,
                        "transaction_type": "DEPOSIT_REFUND",
                        "transaction_amount": -abs(dep_amount),
                        "transaction_reference": f"REF-{rma_id}-{asset_id}",
                        "transaction_date": insp_dt + timedelta(hours=2),
                        "related_ledger_id": None,
                        "description": f"Full deposit refund for asset {asset_id}"
                    })
                    asset_item["asset_status"] = "AVAILABLE"
                    asset_item["current_location_id"] = ret_loc["location_id"]
                    asset_item["current_custodian_owner_id"] = asset_item["owner_id"]
                    asset_item["last_event_at"] = insp_dt
                else:
                    # Damaged -> Damage charge + Repair initiation
                    damage_fee = (dep_amount * Decimal("0.35")).quantize(Decimal("0.01"))
                    deposit_ledger.append({
                        "asset_id": asset_id,
                        "owner_id": customer["owner_id"],
                        "shipment_id": shp_id,
                        "rma_id": rma_id,
                        "transaction_type": "DAMAGE_CHARGE",
                        "transaction_amount": damage_fee,
                        "transaction_reference": f"DMG-{rma_id}-{asset_id}",
                        "transaction_date": insp_dt + timedelta(hours=1),
                        "related_ledger_id": None,
                        "description": f"Damage assessment fee for asset {asset_id}"
                    })

                    # Refund remainder of deposit
                    remainder = dep_amount - damage_fee
                    if remainder > 0:
                        deposit_ledger.append({
                            "asset_id": asset_id,
                            "owner_id": customer["owner_id"],
                            "shipment_id": shp_id,
                            "rma_id": rma_id,
                            "transaction_type": "DEPOSIT_REFUND",
                            "transaction_amount": -abs(remainder),
                            "transaction_reference": f"REF-REM-{rma_id}-{asset_id}",
                            "transaction_date": insp_dt + timedelta(hours=2),
                            "related_ledger_id": None,
                            "description": f"Partial refund after damage deduction for {asset_id}"
                        })

                    # Repair
                    repair_loc = self.rng.choice(repair_locs)
                    rep_start = insp_dt + timedelta(days=1)
                    rep_id = self.id_gen.next_repair_id()
                    rep_completed = (cohort != "REPAIR") or (self.rng.random() < 0.5)

                    if rep_completed:
                        rep_cost = (damage_fee * Decimal("0.85")).quantize(Decimal("0.01"))
                        rep_end = rep_start + timedelta(days=self.rng.randint(2, 6))
                        rep_status = "COMPLETED"
                        asset_item["asset_status"] = "AVAILABLE"
                        asset_item["current_location_id"] = ret_loc["location_id"]
                        asset_item["current_custodian_owner_id"] = asset_item["owner_id"]
                        asset_item["last_event_at"] = rep_end
                    else:
                        rep_cost = Decimal("0.00")
                        rep_end = None
                        rep_status = "IN_PROGRESS"
                        asset_item["asset_status"] = "UNDER_REPAIR"
                        asset_item["current_location_id"] = repair_loc["location_id"]
                        asset_item["current_custodian_owner_id"] = asset_item["owner_id"]
                        asset_item["last_event_at"] = rep_start

                    repairs.append({
                        "repair_id": rep_id,
                        "asset_id": asset_id,
                        "inspection_id": insp_id,
                        "repair_location_id": repair_loc["location_id"],
                        "repair_status": rep_status,
                        "repair_start_date": rep_start,
                        "repair_completion_date": rep_end,
                        "repair_cost": rep_cost,
                        "repair_notes": f"Refurbishment and structural repair under {rep_status}"
                    })

        # If custody events are less than target_custody_events, add supplementary historical cycles
        # to ensure target event volume without violating integrity
        if len(custody_events) < target_custody_events:
            needed = target_custody_events - len(custody_events)
            # Add historical transit check-in events (e.g. TRANSFERRED / IN_TRANSIT checkpoints)
            available_events = [e for e in custody_events if e["event_type"] == "DISPATCHED"]
            cycle_tracker = {}
            idx = 0
            while needed > 0 and available_events:
                base_e = available_events[idx % len(available_events)]
                idx += 1
                a_id = base_e["asset_id"]
                cycle = cycle_tracker.get(a_id, 0)
                cycle_tracker[a_id] = cycle + 1

                mid_dt = base_e["event_timestamp"] + timedelta(hours=6 + (cycle * 8))
                trans_loc = self.rng.choice(locations)
                custody_events.append({
                    "custody_event_id": self.id_gen.next_custody_event_id(a_id),
                    "asset_id": a_id,
                    "shipment_id": base_e["shipment_id"],
                    "from_owner_id": base_e["from_owner_id"],
                    "to_owner_id": base_e["to_owner_id"],
                    "from_location_id": base_e["from_location_id"],
                    "to_location_id": trans_loc["location_id"],
                    "actor_owner_id": base_e["actor_owner_id"],
                    "event_type": "IN_TRANSIT",
                    "event_timestamp": mid_dt,
                    "event_reference": f"CHK-{base_e['shipment_id']}-{cycle+1}",
                    "notes": f"Mid-route transit scan checkpoint #{cycle+1} at {trans_loc['location_name']}"
                })
                needed -= 1

        return {
            "shipments": shipments,
            "shipment_assets": shipment_assets,
            "custody_events": custody_events,
            "return_authorizations": return_authorizations,
            "rma_assets": rma_assets,
            "inspections": inspections,
            "repairs": repairs,
            "deposit_ledger": deposit_ledger,
            "assets": assets
        }
