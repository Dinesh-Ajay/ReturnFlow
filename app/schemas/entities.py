from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal

# --- Asset Type ---
class AssetTypeCreate(BaseModel):
    type_code: str
    type_name: str
    description: Optional[str] = None
    default_deposit_amount: Decimal = Decimal("50.00")
    expected_lifecycle_days: int = 365
    return_due_days: int = 30
    loss_threshold_days: int = 60
    requires_inspection: bool = True
    repairable: bool = True

class AssetTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    asset_type_id: int
    type_code: str
    type_name: str
    description: Optional[str] = None
    default_deposit_amount: Decimal
    expected_lifecycle_days: int
    return_due_days: int
    loss_threshold_days: int
    requires_inspection: bool
    repairable: bool
    active: bool

# --- Owner ---
class OwnerCreate(BaseModel):
    owner_code: str
    owner_name: str
    owner_type: str  # SUPPLIER, CUSTOMER, CARRIER, WAREHOUSE_OPERATOR, INTERNAL_OPERATIONS
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None

class OwnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    owner_id: int
    owner_code: str
    owner_name: str
    owner_type: str
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    active: bool

# --- Location ---
class LocationCreate(BaseModel):
    location_code: str
    location_name: str
    location_type: str  # SUPPLIER, WAREHOUSE, DISTRIBUTION_CENTER, CUSTOMER_SITE, REPAIR_CENTER, TRANSIT_HUB
    city: str
    state: str
    country: str = "USA"

class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    location_id: int
    location_code: str
    location_name: str
    location_type: str
    city: str
    state: str
    country: str
    active: bool

# --- Shipment ---
class ShipmentCreate(BaseModel):
    origin_location_id: int
    destination_location_id: int
    carrier_owner_id: int
    dispatch_date: datetime
    expected_delivery_date: datetime
    asset_ids: List[str]
    tracking_reference: Optional[str] = None

class ShipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    shipment_id: str
    origin_location_id: int
    destination_location_id: int
    carrier_owner_id: int
    dispatch_date: datetime
    expected_delivery_date: datetime
    actual_delivery_date: Optional[datetime] = None
    shipment_status: str
    tracking_reference: Optional[str] = None
    created_at: datetime

# --- Custody ---
class CustodyEventCreate(BaseModel):
    asset_id: str
    shipment_id: Optional[str] = None
    from_owner_id: Optional[int] = None
    to_owner_id: Optional[int] = None
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    actor_owner_id: Optional[int] = None
    event_type: str
    event_timestamp: datetime
    event_reference: Optional[str] = None
    notes: Optional[str] = None

class CustodyEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    custody_event_id: str
    asset_id: str
    shipment_id: Optional[str] = None
    from_owner_id: Optional[int] = None
    to_owner_id: Optional[int] = None
    from_location_id: Optional[int] = None
    to_location_id: Optional[int] = None
    actor_owner_id: Optional[int] = None
    event_type: str
    event_timestamp: datetime
    event_reference: Optional[str] = None
    notes: Optional[str] = None

# --- Returns ---
class ReturnCreate(BaseModel):
    requesting_owner_id: int
    receiving_owner_id: int
    return_location_id: int
    requested_date: datetime
    expected_return_date: datetime
    asset_ids: List[str]
    reason: Optional[str] = None

class ReturnResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    rma_id: str
    requesting_owner_id: int
    receiving_owner_id: int
    return_location_id: int
    requested_date: datetime
    expected_return_date: datetime
    actual_return_date: Optional[datetime] = None
    rma_status: str
    reason: Optional[str] = None

class ReturnReceiveRequest(BaseModel):
    actual_return_date: Optional[datetime] = None
    return_condition: str = "GOOD"

# --- Inspections ---
class InspectionCreate(BaseModel):
    asset_id: str
    inspector_owner_id: int
    condition_status: str  # GOOD, DAMAGED, CRITICAL, UNUSABLE
    rma_id: Optional[str] = None
    damage_severity: Optional[str] = None
    requires_repair: bool = False
    inspection_notes: Optional[str] = None
    inspection_date: Optional[datetime] = None

class InspectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    inspection_id: str
    asset_id: str
    rma_id: Optional[str] = None
    inspector_owner_id: int
    inspection_date: datetime
    condition_status: str
    damage_severity: Optional[str] = None
    requires_repair: bool
    inspection_notes: Optional[str] = None

# --- Repairs ---
class RepairCreate(BaseModel):
    asset_id: str
    repair_location_id: int
    inspection_id: Optional[str] = None
    repair_notes: Optional[str] = None
    start_date: Optional[datetime] = None

class RepairCompleteRequest(BaseModel):
    repair_cost: Decimal
    completion_date: Optional[datetime] = None
    repair_notes: Optional[str] = None

class RepairResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    repair_id: str
    asset_id: str
    inspection_id: Optional[str] = None
    repair_location_id: int
    repair_status: str
    repair_start_date: datetime
    repair_completion_date: Optional[datetime] = None
    repair_cost: Decimal
    repair_notes: Optional[str] = None

# --- Deposit Ledger ---
class DepositChargeRequest(BaseModel):
    asset_id: str
    owner_id: int
    amount: Decimal
    reference: str
    shipment_id: Optional[str] = None
    description: Optional[str] = None

class DepositRefundRequest(BaseModel):
    asset_id: str
    owner_id: int
    amount: Decimal
    reference: str
    rma_id: Optional[str] = None
    related_ledger_id: Optional[int] = None
    description: Optional[str] = None

class DepositLedgerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ledger_id: int
    asset_id: str
    owner_id: int
    shipment_id: Optional[str] = None
    rma_id: Optional[str] = None
    transaction_type: str
    transaction_amount: Decimal
    transaction_reference: str
    transaction_date: datetime
    related_ledger_id: Optional[int] = None
    description: Optional[str] = None

# --- Anomaly Record ---
class AnomalyRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    issue_id: str
    affected_asset_id: Optional[str] = None
    affected_record_id: str
    entity_name: str
    issue_type: str
    severity: str
    description: str
    ground_truth_label: Optional[str] = None
    expected_decision: str
    detected_decision: Optional[str] = None
    detection_status: str
    is_injected: bool
    detected_at: Optional[datetime] = None
