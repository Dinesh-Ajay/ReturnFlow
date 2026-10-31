from typing import Dict, Optional, Any
from datetime import datetime, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.id_sequence import IDSequence
from app.models.shipment import Shipment
from app.models.return_authorization import ReturnAuthorization
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.models.asset import ReusableAsset
from app.models.custody_event import CustodyEvent
from app.models.anomaly_record import AnomalyRecord

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class PersistentIDGenerator:
    """
    Persistent, transaction-safe, concurrency-safe identifier allocation backed by
    the `id_sequences` table in the database with row-level locking (SELECT ... FOR UPDATE).

    Guarantees:
    - Thread-safe & multi-process safe via database row-level locks.
    - Transaction rollback safety: counter state is bound to the enclosing transaction.
    - Automatic initialization from existing populated tables without duplicate primary key collisions.
    - Preserves standard ReturnFlow identifier patterns:
        * Shipment:      SHP-{year}-{seq:06d}
        * RMA:           RMA-{year}-{seq:06d}
        * Inspection:    INSP-{year}-{seq:06d}
        * Repair:        REP-{year}-{seq:06d}
        * Asset:         ASSET-{seq:07d}
        * Custody Event: CUST-{asset_id}-{seq:06d}
        * Anomaly:       ANOM-{seq:06d}
    """

    @classmethod
    def _ensure_table(cls, db: Session) -> None:
        """Ensures the sequence table exists in the target database."""
        IDSequence.__table__.create(bind=db.get_bind(), checkfirst=True)

    @classmethod
    def _find_max_existing_id(
        cls,
        db: Session,
        entity_type: str,
        year: Optional[int] = None,
        asset_id: Optional[str] = None
    ) -> int:
        """
        Extracts the maximum existing numeric suffix from populated database tables.
        Uses length-aware ordering to avoid lexicographical suffix truncations.
        """
        yr = year or 2026

        if entity_type == "shipment":
            pattern = f"SHP-{yr}-%"
            row = db.query(Shipment.shipment_id).filter(
                Shipment.shipment_id.like(pattern)
            ).order_by(func.length(Shipment.shipment_id).desc(), Shipment.shipment_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        elif entity_type == "rma":
            pattern = f"RMA-{yr}-%"
            row = db.query(ReturnAuthorization.rma_id).filter(
                ReturnAuthorization.rma_id.like(pattern)
            ).order_by(func.length(ReturnAuthorization.rma_id).desc(), ReturnAuthorization.rma_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        elif entity_type == "inspection":
            pattern = f"INSP-{yr}-%"
            row = db.query(Inspection.inspection_id).filter(
                Inspection.inspection_id.like(pattern)
            ).order_by(func.length(Inspection.inspection_id).desc(), Inspection.inspection_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        elif entity_type == "repair":
            pattern = f"REP-{yr}-%"
            row = db.query(Repair.repair_id).filter(
                Repair.repair_id.like(pattern)
            ).order_by(func.length(Repair.repair_id).desc(), Repair.repair_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        elif entity_type == "asset":
            row = db.query(ReusableAsset.asset_id).filter(
                ReusableAsset.asset_id.like("ASSET-%")
            ).order_by(func.length(ReusableAsset.asset_id).desc(), ReusableAsset.asset_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        elif entity_type == "custody":
            if not asset_id:
                return 0
            row = db.query(CustodyEvent.custody_event_id).filter(
                CustodyEvent.asset_id == asset_id
            ).order_by(func.length(CustodyEvent.custody_event_id).desc(), CustodyEvent.custody_event_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        elif entity_type == "anomaly":
            row = db.query(AnomalyRecord.issue_id).filter(
                AnomalyRecord.issue_id.like("ANOM-%")
            ).order_by(func.length(AnomalyRecord.issue_id).desc(), AnomalyRecord.issue_id.desc()).first()
            if row and row[0]:
                try:
                    return int(row[0].split("-")[-1])
                except (ValueError, IndexError):
                    return 0
            return 0

        return 0

    @classmethod
    def allocate_next_sequence_val(
        cls,
        db: Session,
        sequence_name: str,
        entity_type: str,
        year: Optional[int] = None,
        asset_id: Optional[str] = None
    ) -> int:
        """
        Atomically locks, initializes if needed, and increments the database sequence.
        Returns the allocated sequential integer.
        """
        cls._ensure_table(db)

        # Attempt to lock existing row
        seq = db.query(IDSequence).filter(
            IDSequence.sequence_name == sequence_name
        ).with_for_update().first()

        if seq is None:
            # First allocation: determine baseline from existing data
            baseline_val = cls._find_max_existing_id(db, entity_type, year=year, asset_id=asset_id)
            try:
                with db.begin_nested():
                    new_seq = IDSequence(
                        sequence_name=sequence_name,
                        current_value=baseline_val,
                        updated_at=utc_now()
                    )
                    db.add(new_seq)
                    db.flush()
            except IntegrityError:
                # Concurrent worker created the sequence entry in parallel; proceed to acquire lock
                pass

            # Acquire exclusive row-level lock on the sequence record
            seq = db.query(IDSequence).filter(
                IDSequence.sequence_name == sequence_name
            ).with_for_update().first()

            if seq is None:
                raise RuntimeError(f"Could not acquire sequence lock for '{sequence_name}'.")

        # Concurrently safe increment
        seq.current_value += 1
        seq.updated_at = utc_now()
        db.flush()
        return seq.current_value

    @classmethod
    def next_shipment_id(cls, db: Session, year: int = 2026) -> str:
        seq_val = cls.allocate_next_sequence_val(db, f"shipment_{year}", "shipment", year=year)
        return f"SHP-{year}-{seq_val:06d}"

    @classmethod
    def next_rma_id(cls, db: Session, year: int = 2026) -> str:
        seq_val = cls.allocate_next_sequence_val(db, f"rma_{year}", "rma", year=year)
        return f"RMA-{year}-{seq_val:06d}"

    @classmethod
    def next_inspection_id(cls, db: Session, year: int = 2026) -> str:
        seq_val = cls.allocate_next_sequence_val(db, f"inspection_{year}", "inspection", year=year)
        return f"INSP-{year}-{seq_val:06d}"

    @classmethod
    def next_repair_id(cls, db: Session, year: int = 2026) -> str:
        seq_val = cls.allocate_next_sequence_val(db, f"repair_{year}", "repair", year=year)
        return f"REP-{year}-{seq_val:06d}"

    @classmethod
    def next_asset_id(cls, db: Session) -> str:
        seq_val = cls.allocate_next_sequence_val(db, "asset", "asset")
        return f"ASSET-{seq_val:07d}"

    @classmethod
    def next_custody_event_id(cls, db: Session, asset_id: str) -> str:
        seq_val = cls.allocate_next_sequence_val(db, f"custody_{asset_id}", "custody", asset_id=asset_id)
        return f"CUST-{asset_id}-{seq_val:06d}"

    @classmethod
    def next_anomaly_id(cls, db: Session) -> str:
        seq_val = cls.allocate_next_sequence_val(db, "anomaly", "anomaly")
        return f"ANOM-{seq_val:06d}"


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

    Supports both in-memory generation (for fast batch synthetic data generation)
    and persistent database-backed allocation when passed a database session.
    """

    def __init__(self, year: int = 2026, db: Optional[Session] = None):
        self.year = year
        self.db = db
        self.asset_counter = 0
        self.shipment_counter = 0
        self.rma_counter = 0
        self.inspection_counter = 0
        self.repair_counter = 0
        self.anomaly_counter = 0
        self.custody_counters: Dict[str, int] = {}

    def next_asset_id(self, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_asset_id(session)
        self.asset_counter += 1
        return f"ASSET-{self.asset_counter:07d}"

    def next_shipment_id(self, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_shipment_id(session, year=self.year)
        self.shipment_counter += 1
        return f"SHP-{self.year}-{self.shipment_counter:06d}"

    def next_rma_id(self, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_rma_id(session, year=self.year)
        self.rma_counter += 1
        return f"RMA-{self.year}-{self.rma_counter:06d}"

    def next_custody_event_id(self, asset_id: str, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_custody_event_id(session, asset_id=asset_id)
        count = self.custody_counters.get(asset_id, 0) + 1
        self.custody_counters[asset_id] = count
        return f"CUST-{asset_id}-{count:06d}"

    def next_inspection_id(self, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_inspection_id(session, year=self.year)
        self.inspection_counter += 1
        return f"INSP-{self.year}-{self.inspection_counter:06d}"

    def next_repair_id(self, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_repair_id(session, year=self.year)
        self.repair_counter += 1
        return f"REP-{self.year}-{self.repair_counter:06d}"

    def next_anomaly_id(self, db: Optional[Session] = None) -> str:
        session = db or self.db
        if session is not None:
            return PersistentIDGenerator.next_anomaly_id(session)
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
