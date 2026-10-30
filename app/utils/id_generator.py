from typing import Dict

class IDGenerator:
    """
    Deterministic identifier generator matching required patterns:
    - Asset: ASSET-0000001
    - Shipment: SHP-2026-000001
    - RMA: RMA-2026-000001
    - Custody Event: CUST-ASSET-0000001-000001
    - Inspection: INSP-2026-000001
    - Repair: REP-2026-000001
    - Anomaly: ANOM-000001
    """

    def __init__(self, year: int = 2026):
        self.year = year
        self.asset_counter = 0
        self.shipment_counter = 0
        self.rma_counter = 0
        self.inspection_counter = 0
        self.repair_counter = 0
        self.anomaly_counter = 0
        self.custody_counters: Dict[str, int] = {}

    def next_asset_id(self) -> str:
        self.asset_counter += 1
        return f"ASSET-{self.asset_counter:07d}"

    def next_shipment_id(self) -> str:
        self.shipment_counter += 1
        return f"SHP-{self.year}-{self.shipment_counter:06d}"

    def next_rma_id(self) -> str:
        self.rma_counter += 1
        return f"RMA-{self.year}-{self.rma_counter:06d}"

    def next_custody_event_id(self, asset_id: str) -> str:
        count = self.custody_counters.get(asset_id, 0) + 1
        self.custody_counters[asset_id] = count
        return f"CUST-{asset_id}-{count:06d}"

    def next_inspection_id(self) -> str:
        self.inspection_counter += 1
        return f"INSP-{self.year}-{self.inspection_counter:06d}"

    def next_repair_id(self) -> str:
        self.repair_counter += 1
        return f"REP-{self.year}-{self.repair_counter:06d}"

    def next_anomaly_id(self) -> str:
        self.anomaly_counter += 1
        return f"ANOM-{self.anomaly_counter:06d}"

    def reset(self):
        self.asset_counter = 0
        self.shipment_counter = 0
        self.rma_counter = 0
        self.inspection_counter = 0
        self.repair_counter = 0
        self.anomaly_counter = 0
        self.custody_counters.clear()
