import os
import json
import csv
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from app.utils.id_generator import IDGenerator

def utc_now():
    return datetime.now(timezone.utc)

class AnomalyInjector:
    """
    Deliberately injects 5 required anomaly scenarios into generated baseline data,
    recording explicit ground-truth labels without corrupting unrelated records.
    """

    def __init__(self, rng: random.Random, id_gen: IDGenerator):
        self.rng = rng
        self.id_gen = id_gen

    def inject_all_anomalies(
        self,
        assets: List[Dict[str, Any]],
        custody_events: List[Dict[str, Any]],
        deposit_ledger: List[Dict[str, Any]],
        repairs: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
        owners: List[Dict[str, Any]],
        count_per_scenario: int = 2
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        ground_truth_records = []
        injected_records = []

        # Target assets that have events
        eligible_asset_ids = list({e["asset_id"] for e in custody_events})
        self.rng.shuffle(eligible_asset_ids)

        ptr = 0

        # Scenario 1: Asset has two simultaneous locations (FLAG_FOR_INVESTIGATION)
        for _ in range(count_per_scenario):
            if ptr >= len(eligible_asset_ids):
                break
            a_id = eligible_asset_ids[ptr]
            ptr += 1

            # Find an existing event for this asset
            asset_evts = [e for e in custody_events if e["asset_id"] == a_id]
            if not asset_evts:
                continue
            base_evt = asset_evts[0]

            conflicting_loc = self.rng.choice(locations)
            while conflicting_loc["location_id"] == base_evt.get("to_location_id") and len(locations) > 1:
                conflicting_loc = self.rng.choice(locations)

            issue_id = self.id_gen.next_anomaly_id()
            conflicting_event_id = self.id_gen.next_custody_event_id(a_id)

            # Insert conflicting event at exact same timestamp
            simultaneous_event = {
                "custody_event_id": conflicting_event_id,
                "asset_id": a_id,
                "shipment_id": None,
                "from_owner_id": base_evt["from_owner_id"],
                "to_owner_id": base_evt["to_owner_id"],
                "from_location_id": base_evt["from_location_id"],
                "to_location_id": conflicting_loc["location_id"],
                "actor_owner_id": base_evt["actor_owner_id"],
                "event_type": "TRANSFERRED",
                "event_timestamp": base_evt["event_timestamp"],  # identical timestamp
                "event_reference": "INJECTED-CONFLICT-LOC",
                "notes": f"INJECTED ANOMALY: Simultaneous conflicting scan at {conflicting_loc['location_name']}"
            }
            custody_events.append(simultaneous_event)

            gt_item = {
                "issue_id": issue_id,
                "asset_id": a_id,
                "entity_name": "custody_events",
                "record_id": conflicting_event_id,
                "issue_type": "SIMULTANEOUS_LOCATIONS",
                "severity": "CRITICAL",
                "ground_truth_label": "ANOMALY_SIMULTANEOUS_LOCATIONS",
                "expected_decision": "FLAG_FOR_INVESTIGATION",
                "explanation": f"Asset {a_id} recorded in two distinct physical locations at identical timestamp {base_evt['event_timestamp']}."
            }
            ground_truth_records.append(gt_item)

        # Scenario 2: Return processed before dispatch (INVALID_LIFECYCLE_TRANSITION)
        for _ in range(count_per_scenario):
            if ptr >= len(eligible_asset_ids):
                break
            a_id = eligible_asset_ids[ptr]
            ptr += 1

            disp_evts = [e for e in custody_events if e["asset_id"] == a_id and e["event_type"] == "DISPATCHED"]
            if not disp_evts:
                continue
            disp_evt = disp_evts[0]

            issue_id = self.id_gen.next_anomaly_id()
            pre_event_id = self.id_gen.next_custody_event_id(a_id)
            premature_dt = disp_evt["event_timestamp"] - timedelta(days=5)

            premature_return = {
                "custody_event_id": pre_event_id,
                "asset_id": a_id,
                "shipment_id": None,
                "from_owner_id": disp_evt["to_owner_id"],
                "to_owner_id": disp_evt["from_owner_id"],
                "from_location_id": disp_evt["to_location_id"],
                "to_location_id": disp_evt["from_location_id"],
                "actor_owner_id": disp_evt["from_owner_id"],
                "event_type": "RETURNED",
                "event_timestamp": premature_dt,
                "event_reference": "INJECTED-EARLY-RETURN",
                "notes": "INJECTED ANOMALY: Return event timestamp precedes initial dispatch date."
            }
            custody_events.append(premature_return)

            gt_item = {
                "issue_id": issue_id,
                "asset_id": a_id,
                "entity_name": "custody_events",
                "record_id": pre_event_id,
                "issue_type": "RETURN_BEFORE_DISPATCH",
                "severity": "CRITICAL",
                "ground_truth_label": "ANOMALY_RETURN_BEFORE_DISPATCH",
                "expected_decision": "INVALID_LIFECYCLE_TRANSITION",
                "explanation": f"Return event {pre_event_id} at {premature_dt} precedes dispatch event {disp_evt['custody_event_id']} at {disp_evt['event_timestamp']}."
            }
            ground_truth_records.append(gt_item)

        # Scenario 3: Deposit refunded twice (DUPLICATE_REFUND)
        refund_entries = [e for e in deposit_ledger if e["transaction_type"] == "DEPOSIT_REFUND"]
        if refund_entries:
            for i in range(min(count_per_scenario, len(refund_entries))):
                orig_refund = refund_entries[i]
                issue_id = self.id_gen.next_anomaly_id()

                duplicate_refund = {
                    "asset_id": orig_refund["asset_id"],
                    "owner_id": orig_refund["owner_id"],
                    "shipment_id": orig_refund["shipment_id"],
                    "rma_id": orig_refund["rma_id"],
                    "transaction_type": "DEPOSIT_REFUND",
                    "transaction_amount": orig_refund["transaction_amount"],
                    "transaction_reference": f"{orig_refund['transaction_reference']}-DUP",
                    "transaction_date": orig_refund["transaction_date"] + timedelta(hours=1),
                    "related_ledger_id": None,
                    "description": "INJECTED ANOMALY: Erroneous duplicate deposit refund transaction"
                }
                deposit_ledger.append(duplicate_refund)

                gt_item = {
                    "issue_id": issue_id,
                    "asset_id": orig_refund["asset_id"],
                    "entity_name": "deposit_ledger",
                    "record_id": duplicate_refund["transaction_reference"],
                    "issue_type": "DUPLICATE_REFUND",
                    "severity": "HIGH",
                    "ground_truth_label": "ANOMALY_DUPLICATE_REFUND",
                    "expected_decision": "DUPLICATE_REFUND",
                    "explanation": f"Asset {orig_refund['asset_id']} received duplicate refund with reference {duplicate_refund['transaction_reference']}."
                }
                ground_truth_records.append(gt_item)

        # Scenario 4: Repair closes without inspection (REPAIR_WITHOUT_INSPECTION)
        repair_locs = [l["location_id"] for l in locations if l["location_type"] == "REPAIR_CENTER"]
        if not repair_locs:
            repair_locs = [locations[0]["location_id"]]

        for _ in range(count_per_scenario):
            if ptr >= len(eligible_asset_ids):
                break
            a_id = eligible_asset_ids[ptr]
            ptr += 1

            rep_id = self.id_gen.next_repair_id()
            issue_id = self.id_gen.next_anomaly_id()

            completed_uninspected_repair = {
                "repair_id": rep_id,
                "asset_id": a_id,
                "inspection_id": None,  # Missing inspection!
                "repair_location_id": self.rng.choice(repair_locs),
                "repair_status": "COMPLETED",
                "repair_start_date": datetime(2026, 9, 10, 9, 0, tzinfo=timezone.utc),
                "repair_completion_date": datetime(2026, 9, 15, 14, 0, tzinfo=timezone.utc),
                "repair_cost": Decimal("85.00"),
                "repair_notes": "INJECTED ANOMALY: Repair closed as completed without prior inspection evidence."
            }
            repairs.append(completed_uninspected_repair)

            gt_item = {
                "issue_id": issue_id,
                "asset_id": a_id,
                "entity_name": "repairs",
                "record_id": rep_id,
                "issue_type": "REPAIR_WITHOUT_INSPECTION",
                "severity": "HIGH",
                "ground_truth_label": "ANOMALY_REPAIR_WITHOUT_INSPECTION",
                "expected_decision": "REPAIR_WITHOUT_INSPECTION",
                "explanation": f"Repair {rep_id} for asset {a_id} completed without linking to an originating inspection."
            }
            ground_truth_records.append(gt_item)

        # Scenario 5: Custody event lacks actor (MISSING_CUSTODY_ACTOR)
        for _ in range(count_per_scenario):
            if ptr >= len(eligible_asset_ids):
                break
            a_id = eligible_asset_ids[ptr]
            ptr += 1

            issue_id = self.id_gen.next_anomaly_id()
            unattributed_evt_id = self.id_gen.next_custody_event_id(a_id)

            unattributed_event = {
                "custody_event_id": unattributed_evt_id,
                "asset_id": a_id,
                "shipment_id": None,
                "from_owner_id": None,
                "to_owner_id": None,
                "from_location_id": locations[0]["location_id"],
                "to_location_id": locations[1]["location_id"],
                "actor_owner_id": None,  # Deliberately missing actor!
                "event_type": "TRANSFERRED",
                "event_timestamp": datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc),
                "event_reference": "INJECTED-MISSING-ACTOR",
                "notes": "INJECTED ANOMALY: Custody event lacks responsible actor."
            }
            custody_events.append(unattributed_event)

            gt_item = {
                "issue_id": issue_id,
                "asset_id": a_id,
                "entity_name": "custody_events",
                "record_id": unattributed_evt_id,
                "issue_type": "MISSING_CUSTODY_ACTOR",
                "severity": "MEDIUM",
                "ground_truth_label": "ANOMALY_MISSING_CUSTODY_ACTOR",
                "expected_decision": "MISSING_CUSTODY_ACTOR",
                "explanation": f"Custody event {unattributed_evt_id} recorded with null actor_owner_id."
            }
            ground_truth_records.append(gt_item)

        return ground_truth_records
