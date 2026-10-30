from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal

class AssetBase(BaseModel):
    asset_id: str
    asset_type_id: int
    owner_id: int
    serial_number: str
    manufacture_date: date
    purchase_date: date
    acquisition_cost: Decimal
    deposit_amount: Decimal

class AssetCreate(BaseModel):
    asset_type_id: Optional[int] = None
    asset_type_code: Optional[str] = None
    owner_id: int
    current_location_id: int
    purchase_date: date
    manufacture_date: Optional[date] = None
    serial_number: Optional[str] = None
    acquisition_cost: Optional[Decimal] = None
    deposit_amount: Decimal = Field(..., gt=0, description="Deposit amount must be strictly greater than 0")
    asset_status: Optional[str] = "AVAILABLE"
    notes: Optional[str] = None

class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    asset_type_id: int
    owner_id: int
    serial_number: str
    asset_status: str
    manufacture_date: date
    purchase_date: date
    current_location_id: Optional[int] = None
    current_custodian_owner_id: Optional[int] = None
    acquisition_cost: Decimal
    deposit_amount: Decimal
    last_event_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class AssetListItem(BaseModel):
    asset_id: str
    serial_number: str
    type_code: str
    type_name: str
    owner_id: int
    owner_name: str
    current_location_id: Optional[int]
    current_location_name: str
    current_custodian_id: Optional[int]
    current_custodian_name: str
    asset_status: str
    acquisition_cost: float
    deposit_amount: float
    last_event_at: str
    days_outstanding: int
    is_overdue: bool
    is_lost_candidate: bool
    created_at: str

class AssetListResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    items: List[AssetListItem]
