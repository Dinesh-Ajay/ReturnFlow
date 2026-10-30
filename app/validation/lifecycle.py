from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.repair import Repair
from app.models.custody_event import CustodyEvent

class LifecycleValidator:
    """
    Validates lifecycle progression, order of operations, and mandatory prerequisites.
    """

    @classmethod
    def detect_return_before_dispatch(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Anomaly 2: Detects return events whose timestamp precedes the corresponding dispatch.
        Expected decision: INVALID_LIFECYCLE_TRANSITION
        """
        query = text("""
            SELECT 
                ret.custody_event_id AS return_event_id,
                ret.asset_id,
                ret.event_timestamp AS return_time,
                disp.custody_event_id AS dispatch_event_id,
                disp.event_timestamp AS dispatch_time
            FROM custody_events ret
            JOIN custody_events disp ON ret.asset_id = disp.asset_id
            WHERE ret.event_type = 'RETURNED'
              AND disp.event_type = 'DISPATCHED'
              AND ret.event_timestamp < disp.event_timestamp
        """)
        rows = db.execute(query).fetchall()

        anomalies = []
        for r in rows:
            anomalies.append({
                "issue_type": "RETURN_BEFORE_DISPATCH",
                "severity": "CRITICAL",
                "asset_id": r[1],
                "record_id": r[0],
                "entity_name": "custody_events",
                "expected_decision": "INVALID_LIFECYCLE_TRANSITION",
                "description": f"Return event {r[0]} at {r[2]} precedes dispatch event {r[3]} at {r[4]}"
            })
        return anomalies

    @classmethod
    def detect_repairs_without_inspection(cls, db: Session) -> List[Dict[str, Any]]:
        """
        Anomaly 4: Detects completed repairs that lack an originating inspection.
        Expected decision: REPAIR_WITHOUT_INSPECTION
        """
        query = text("""
            SELECT 
                repair_id,
                asset_id,
                repair_status,
                repair_start_date,
                repair_completion_date
            FROM repairs
            WHERE repair_status = 'COMPLETED'
              AND (inspection_id IS NULL OR inspection_id = '')
        """)
        rows = db.execute(query).fetchall()

        anomalies = []
        for r in rows:
            anomalies.append({
                "issue_type": "REPAIR_WITHOUT_INSPECTION",
                "severity": "HIGH",
                "asset_id": r[1],
                "record_id": r[0],
                "entity_name": "repairs",
                "expected_decision": "REPAIR_WITHOUT_INSPECTION",
                "description": f"Completed repair {r[0]} for asset {r[1]} lacks required inspection link."
            })
        return anomalies
