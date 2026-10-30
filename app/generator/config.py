from typing import Dict, Any

PROFILES: Dict[str, Dict[str, Any]] = {
    "starter": {
        "num_asset_types": 5,
        "num_owners": 15,
        "num_locations": 12,
        "num_assets": 200,
        "num_shipments": 100,
        "target_custody_events": 1000,
        "num_anomalies_each": 2,  # 2 instances per required anomaly scenario
    },
    "full": {
        "num_asset_types": 8,
        "num_owners": 40,
        "num_locations": 30,
        "num_assets": 20000,
        "num_shipments": 10000,
        "target_custody_events": 100000,
        "num_anomalies_each": 10,  # 10 instances per required anomaly scenario
    }
}
