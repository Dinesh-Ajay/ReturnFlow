from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.custody_event import CustodyEvent

class CustodyValidator:
    """
    Validates custody movement chronology, simultaneous location conflicts,
    and actor attribution integrity.
    """

    @classmethod
    def detect_simultaneous_locations(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Anomaly 1: Detects assets recorded in multiple distinct locations at overlapping timestamps.
        Expected decision: FLAG_FOR_INVESTIGATION
        """
        query = text("""
            SELECT 
                ce1.asset_id,
                ce1.custody_event_id AS record_id_1,
                ce2.custody_event_id AS record_id_2,
                ce1.event_timestamp,
                ce1.to_location_id AS loc_1,
                ce2.to_location_id AS loc_2
            FROM custody_events ce1
            JOIN custody_events ce2 
                ON ce1.asset_id = ce2.asset_id 
                AND ce1.event_timestamp = ce2.event_timestamp 
                AND ce1.custody_event_id < ce2.custody_event_id
                AND ce1.to_location_id != ce2.to_location_id
        """)
        rows = db.execute(query).fetchall()

        anomalies = []
        for r in rows:
            anomalies.append({
                "issue_type": "SIMULTANEOUS_LOCATIONS",
                "severity": "CRITICAL",
                "asset_id": r[0],
                "record_id": r[2],  # Conflicting event
                "entity_name": "custody_events",
                "expected_decision": "FLAG_FOR_INVESTIGATION",
                "description": f"Asset {r[0]} detected in conflicting locations (Location {r[4]} vs Location {r[5]}) at timestamp {r[3]}"
            })
        return anomalies

    @classmethod
    def detect_missing_custody_actors(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Anomaly 5: Detects custody events lacking responsible actor attribution.
        Expected decision: MISSING_CUSTODY_ACTOR
        """
        query = text("""
            SELECT 
                custody_event_id,
                asset_id,
                event_type,
                event_timestamp
            FROM custody_events
            WHERE actor_owner_id IS NULL
        """)
        rows = db.execute(query).fetchall()

        anomalies = []
        for r in rows:
            anomalies.append({
                "issue_type": "MISSING_CUSTODY_ACTOR",
                "severity": "MEDIUM",
                "asset_id": r[1],
                "record_id": r[0],
                "entity_name": "custody_events",
                "expected_decision": "MISSING_CUSTODY_ACTOR",
                "description": f"Custody event {r[0]} ({r[2]}) lacks required actor_owner_id."
            })
        return anomalies
