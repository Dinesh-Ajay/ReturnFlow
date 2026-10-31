from datetime import datetime, timezone
from sqlalchemy import Column, String, BigInteger, DateTime
from app.database.base import Base

def utc_now():
    return datetime.now(timezone.utc)

class IDSequence(Base):
    """
    Persistent, transaction-safe sequence counter for generated entity identifiers.
    Maintains current allocated numeric values per sequence_name.
    """
    __tablename__ = "id_sequences"

    sequence_name = Column(String(64), primary_key=True, index=True)
    current_value = Column(BigInteger, nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=utc_now, onupdate=utc_now)

    def __repr__(self) -> str:
        return f"<IDSequence(sequence_name='{self.sequence_name}', current_value={self.current_value})>"
