# ReturnFlow Data Dictionary

This document details the relational data dictionary for **ReturnFlow** (Database: `returnflow_db`), built on MySQL 8.0+ / InnoDB with support for PostgreSQL (Supabase).

---

## 1. AssetType (`asset_types`)
*Purpose:* Defines categories of reusable assets, deposit requirements, lifecycle thresholds, and inspection rules.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `asset_type_id` | INT | NO | AUTO_INCREMENT | PRIMARY KEY | Unique surrogate identifier for the asset type |
| `type_code` | VARCHAR(32) | NO | - | UNIQUE, INDEX | Business mnemonic (e.g. `PALLET`, `CONTAINER`, `CRATE`) |
| `type_name` | VARCHAR(100) | NO | - | - | Full descriptive category name |
| `description` | TEXT | YES | NULL | - | Functional description and handling specifications |
| `default_deposit_amount` | DECIMAL(12, 2) | NO | 0.00 | >= 0.00 | Standard refundable deposit charged per asset unit |
| `expected_lifecycle_days` | INT | NO | 365 | > 0 | Expected operational longevity in days |
| `return_due_days` | INT | NO | 30 | > 0 | Permissible customer retention threshold before overdue |
| `loss_threshold_days` | INT | NO | 60 | > return_due_days | Retention duration after which asset is flagged as lost |
| `requires_inspection` | BOOLEAN | NO | TRUE | - | Whether post-return QA inspection is mandatory |
| `repairable` | BOOLEAN | NO | TRUE | - | Whether damaged units can be refurbished |
| `active` | BOOLEAN | NO | TRUE | - | Soft-delete / active configuration flag |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | UTC timestamp of record creation |

---

## 2. Owner (`owners`)
*Purpose:* Represents corporate and logistical organizations participating in ownership, custody handoffs, carriage, and returns.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `owner_id` | INT | NO | AUTO_INCREMENT | PRIMARY KEY | Unique surrogate identifier for owner entity |
| `owner_code` | VARCHAR(32) | NO | - | UNIQUE, INDEX | Deterministic code (`OWN-001`, `OWN-002`) |
| `owner_name` | VARCHAR(150) | NO | - | - | Enterprise trading or legal entity name |
| `owner_type` | VARCHAR(50) | NO | - | INDEX | Enum: `SUPPLIER`, `CUSTOMER`, `CARRIER`, `WAREHOUSE_OPERATOR`, `INTERNAL_OPERATIONS` |
| `contact_email` | VARCHAR(150) | YES | NULL | - | Synthetic business contact email |
| `contact_phone` | VARCHAR(50) | YES | NULL | - | Synthetic customer service / dispatch phone |
| `active` | BOOLEAN | NO | TRUE | - | Active operating status |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | UTC timestamp of record creation |

---

## 3. Location (`locations`)
*Purpose:* Physical supply chain facilities where assets are stored, cross-docked, repaired, or received.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `location_id` | INT | NO | AUTO_INCREMENT | PRIMARY KEY | Unique surrogate identifier for facility |
| `location_code` | VARCHAR(32) | NO | - | UNIQUE, INDEX | Deterministic facility code (`LOC-001`) |
| `location_name` | VARCHAR(150) | NO | - | - | Facility name (e.g. `New York DC`, `Chicago WH`) |
| `location_type` | VARCHAR(50) | NO | - | INDEX | Enum: `SUPPLIER`, `WAREHOUSE`, `DISTRIBUTION_CENTER`, `CUSTOMER_SITE`, `REPAIR_CENTER`, `TRANSIT_HUB` |
| `city` | VARCHAR(100) | NO | - | - | City name |
| `state` | VARCHAR(100) | NO | - | - | State / province code |
| `country` | VARCHAR(100) | NO | 'USA' | - | Country name |
| `active` | BOOLEAN | NO | TRUE | - | Operating status |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | UTC timestamp of record creation |

---

## 4. ReusableAsset (`reusable_assets`)
*Purpose:* Core entity representing an individual tracked reusable container, pallet, or piece of equipment.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `asset_id` | VARCHAR(32) | NO | - | PRIMARY KEY | Immutable zero-padded ID: `ASSET-0000001` |
| `asset_type_id` | INT | NO | - | FK -> `asset_types.asset_type_id`, INDEX | Category configuration reference |
| `owner_id` | INT | NO | - | FK -> `owners.owner_id`, INDEX | Commercial proprietary asset owner |
| `serial_number` | VARCHAR(64) | NO | - | UNIQUE, INDEX | Permanent physical engraved / RFID serial |
| `asset_status` | VARCHAR(32) | NO | 'AVAILABLE' | INDEX | Lifecycle status: `AVAILABLE`, `DISPATCHED`, `IN_TRANSIT`, `IN_CUSTODY`, `RETURN_PENDING`, `RETURNED`, `INSPECTION_PENDING`, `DAMAGED`, `UNDER_REPAIR`, `LOST`, `RETIRED` |
| `manufacture_date`| DATE | NO | - | - | Date asset was manufactured |
| `purchase_date` | DATE | NO | - | - | Date asset was acquired into fleet |
| `current_location_id` | INT | YES | NULL | FK -> `locations.location_id`, INDEX | Materialized current facility location projection |
| `current_custodian_owner_id` | INT | YES | NULL | FK -> `owners.owner_id`, INDEX | Materialized current custodian organization |
| `acquisition_cost`| DECIMAL(12, 2)| NO | 0.00 | >= 0.00 | Capital fleet replacement value |
| `deposit_amount` | DECIMAL(12, 2)| NO | 0.00 | >= 0.00 | Active security deposit liability value |
| `last_event_at` | DATETIME | YES | NULL | INDEX | Timestamp of most recent custody/movement event |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | UTC creation timestamp |
| `updated_at` | DATETIME | NO | CURRENT_TIMESTAMP ON UPDATE | - | UTC modification timestamp |

---

## 5. Shipment (`shipments`)
*Purpose:* Freight movement transporting reusable assets between facilities.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_id` | VARCHAR(32) | NO | - | PRIMARY KEY | Year-padded identifier: `SHP-2026-000001` |
| `origin_location_id` | INT | NO | - | FK -> `locations.location_id`, INDEX | Departure facility |
| `destination_location_id` | INT | NO | - | FK -> `locations.location_id`, INDEX | Destination facility |
| `carrier_owner_id` | INT | NO | - | FK -> `owners.owner_id`, INDEX | Carrier organization transporting shipment |
| `dispatch_date` | DATETIME | NO | - | INDEX | UTC departure timestamp |
| `expected_delivery_date` | DATETIME | NO | - | - | Promised arrival timestamp |
| `actual_delivery_date` | DATETIME | YES | NULL | - | Actual verified arrival timestamp |
| `shipment_status` | VARCHAR(32) | NO | 'PLANNED' | INDEX | Status: `PLANNED`, `DISPATCHED`, `IN_TRANSIT`, `DELIVERED`, `DELAYED`, `CANCELLED` |
| `tracking_reference` | VARCHAR(64) | YES | NULL | INDEX | Bill of Lading / carrier tracking number |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |

---

## 6. ShipmentAsset (`shipment_assets`)
*Purpose:* Bridge table linking shipments with assigned reusable assets.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_asset_id` | INT | NO | AUTO_INCREMENT | PRIMARY KEY | Surrogate link identifier |
| `shipment_id` | VARCHAR(32) | NO | - | FK -> `shipments.shipment_id`, INDEX | Shipment reference |
| `asset_id` | VARCHAR(32) | NO | - | FK -> `reusable_assets.asset_id`, INDEX | Reusable asset reference |
| `assigned_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Manifest assignment timestamp |
| `removed_at` | DATETIME | YES | NULL | - | Removal / de-consolidation timestamp |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |
| **Constraint** | UNIQUE(`shipment_id`, `asset_id`) | - | - | - | Prevents duplicate asset manifest entries |

---

## 7. CustodyEvent (`custody_events`)
*Purpose:* Immutable historical audit log tracking physical movement, chain-of-custody handoffs, and lifecycle state changes.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `custody_event_id` | VARCHAR(64) | NO | - | PRIMARY KEY | Deterministic per-asset format: `CUST-ASSET-0000001-000001` |
| `asset_id` | VARCHAR(32) | NO | - | FK -> `reusable_assets.asset_id`, INDEX | Target reusable asset |
| `shipment_id` | VARCHAR(32) | YES | NULL | FK -> `shipments.shipment_id`, INDEX | Transport shipment context |
| `from_owner_id` | INT | YES | NULL | FK -> `owners.owner_id`, INDEX | Prior responsible organization |
| `to_owner_id` | INT | YES | NULL | FK -> `owners.owner_id`, INDEX | Successor custodian organization |
| `from_location_id` | INT | YES | NULL | FK -> `locations.location_id`, INDEX | Point of origin |
| `to_location_id` | INT | YES | NULL | FK -> `locations.location_id`, INDEX | Receiving point |
| `actor_owner_id` | INT | YES | NULL | FK -> `owners.owner_id`, INDEX | Entity executing handoff (Null only in injected anomaly) |
| `event_type` | VARCHAR(32) | NO | - | INDEX | Type: `DISPATCHED`, `PICKED_UP`, `IN_TRANSIT`, `RECEIVED`, `TRANSFERRED`, `RETURNED`, `LOST_REPORTED`, `RECOVERED`, `ADJUSTED` |
| `event_timestamp` | DATETIME | NO | - | INDEX | Effective occurrence timestamp |
| `event_reference` | VARCHAR(64) | YES | NULL | - | Document / scan reference |
| `notes` | TEXT | YES | NULL | - | Qualitative audit notes |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record append timestamp |

---

## 8. ReturnAuthorization (`return_authorizations`)
*Purpose:* Commercial permission (RMA) authorizing the return of assets from customers or partner distribution centers.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rma_id` | VARCHAR(32) | NO | - | PRIMARY KEY | Format: `RMA-2026-000001` |
| `requesting_owner_id` | INT | NO | - | FK -> `owners.owner_id`, INDEX | Entity requesting return authorization |
| `receiving_owner_id` | INT | NO | - | FK -> `owners.owner_id`, INDEX | Fleet owner receiving return |
| `return_location_id` | INT | NO | - | FK -> `locations.location_id`, INDEX | Designated return facility |
| `requested_date` | DATETIME | NO | - | INDEX | Request timestamp |
| `approved_date` | DATETIME | YES | NULL | - | Authorization timestamp |
| `expected_return_date` | DATETIME | NO | - | - | Scheduled delivery date |
| `actual_return_date` | DATETIME | YES | NULL | - | Actual receiving dock timestamp |
| `rma_status` | VARCHAR(32) | NO | 'REQUESTED' | INDEX | Status: `REQUESTED`, `APPROVED`, `IN_TRANSIT`, `RECEIVED`, `INSPECTION_PENDING`, `COMPLETED`, `REJECTED`, `CANCELLED` |
| `reason` | VARCHAR(255) | YES | NULL | - | Business justification |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |

---

## 9. ReturnAuthorizationAsset (`return_authorization_assets`)
*Purpose:* Bridge table linking return authorizations and returned assets.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `rma_asset_id` | INT | NO | AUTO_INCREMENT | PRIMARY KEY | Bridge surrogate key |
| `rma_id` | VARCHAR(32) | NO | - | FK -> `return_authorizations.rma_id`, INDEX | Return authorization reference |
| `asset_id` | VARCHAR(32) | NO | - | FK -> `reusable_assets.asset_id`, INDEX | Asset reference |
| `return_condition` | VARCHAR(32) | YES | NULL | - | Condition: `GOOD`, `DAMAGED`, `CRITICAL`, `UNUSABLE` |
| `received_at` | DATETIME | YES | NULL | - | Verified dock arrival timestamp |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |
| **Constraint** | UNIQUE(`rma_id`, `asset_id`) | - | - | - | Prevents duplicate manifest returns |

---

## 10. Inspection (`inspections`)
*Purpose:* Detailed physical inspection and grading of returned reusable assets prior to restocking or repair.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `inspection_id` | VARCHAR(32) | NO | - | PRIMARY KEY | Format: `INSP-2026-000001` |
| `asset_id` | VARCHAR(32) | NO | - | FK -> `reusable_assets.asset_id`, INDEX | Inspected asset |
| `rma_id` | VARCHAR(32) | YES | NULL | FK -> `return_authorizations.rma_id`, INDEX | Associated RMA context |
| `inspector_owner_id` | INT | NO | - | FK -> `owners.owner_id`, INDEX | Organization performing QA |
| `inspection_date` | DATETIME | NO | - | INDEX | Inspection execution timestamp |
| `condition_status` | VARCHAR(32) | NO | - | INDEX | Condition: `GOOD`, `DAMAGED`, `CRITICAL`, `UNUSABLE` |
| `damage_severity` | VARCHAR(32) | YES | NULL | - | Severity: `NONE`, `MINOR`, `MODERATE`, `SEVERE` |
| `requires_repair` | BOOLEAN | NO | FALSE | - | Flag indicating refurbishment required |
| `inspection_notes` | TEXT | YES | NULL | - | Inspector observation details |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |

---

## 11. Repair (`repairs`)
*Purpose:* Tracks maintenance, repair operations, labor/material costs, and refurbishment completion.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `repair_id` | VARCHAR(32) | NO | - | PRIMARY KEY | Format: `REP-2026-000001` |
| `asset_id` | VARCHAR(32) | NO | - | FK -> `reusable_assets.asset_id`, INDEX | Asset undergoing repair |
| `inspection_id` | VARCHAR(32) | YES | NULL | FK -> `inspections.inspection_id`, INDEX | Originating inspection |
| `repair_location_id` | INT | NO | - | FK -> `locations.location_id`, INDEX | Repair center facility |
| `repair_status` | VARCHAR(32) | NO | 'REQUESTED' | INDEX | Status: `REQUESTED`, `IN_PROGRESS`, `COMPLETED`, `FAILED`, `CANCELLED` |
| `repair_start_date` | DATETIME | NO | - | INDEX | Repair commencement timestamp |
| `repair_completion_date` | DATETIME | YES | NULL | - | Refurbishment completion timestamp |
| `repair_cost` | DECIMAL(12, 2)| NO | 0.00 | >= 0.00 | Actual recorded repair expense |
| `repair_notes` | TEXT | YES | NULL | - | Maintenance technician notes |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |

---

## 12. DepositLedger (`deposit_ledger`)
*Purpose:* Financial ledger tracking security deposits, refunds, damage assessments, and adjustments.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ledger_id` | INT | NO | AUTO_INCREMENT | PRIMARY KEY | Immutable transaction ledger ID |
| `asset_id` | VARCHAR(32) | NO | - | FK -> `reusable_assets.asset_id`, INDEX | Associated asset |
| `owner_id` | INT | NO | - | FK -> `owners.owner_id`, INDEX | Commercial entity billed or refunded |
| `shipment_id` | VARCHAR(32) | YES | NULL | FK -> `shipments.shipment_id`, INDEX | Dispatch context |
| `rma_id` | VARCHAR(32) | YES | NULL | FK -> `return_authorizations.rma_id`, INDEX | Return authorization context |
| `transaction_type` | VARCHAR(32) | NO | - | INDEX | Type: `DEPOSIT_CHARGE` (+), `DEPOSIT_REFUND` (-), `DAMAGE_CHARGE` (+), `REPAIR_CHARGE` (+), `LOSS_CHARGE` (+), `ADJUSTMENT` (+/-) |
| `transaction_amount`| DECIMAL(12, 2)| NO | - | - | Signed monetary value in USD |
| `transaction_reference` | VARCHAR(64) | NO | - | INDEX | Reference invoice or refund slip ID |
| `transaction_date` | DATETIME | NO | - | INDEX | Transaction booking date |
| `related_ledger_id` | INT | YES | NULL | FK -> `deposit_ledger.ledger_id`, INDEX | Original entry link (for refund / adjustment) |
| `description` | VARCHAR(255) | YES | NULL | - | Accounting narrative |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Record creation timestamp |

---

## 13. AnomalyRecord (`anomaly_records`)
*Purpose:* Operational audit and issue tracking table storing injected baseline anomalies and detected exceptions.

| Field Name | Data Type | Nullable | Default | Constraints & Relationships | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `issue_id` | VARCHAR(64) | NO | - | PRIMARY KEY | Identifier: `ANOM-000001` or `DET-XXXXXX` |
| `affected_asset_id` | VARCHAR(32) | YES | NULL | INDEX | Asset subject to exception |
| `affected_record_id` | VARCHAR(64) | NO | - | INDEX | Underlying entity record ID |
| `entity_name` | VARCHAR(64) | NO | - | INDEX | Table name where exception occurred |
| `issue_type` | VARCHAR(64) | NO | - | INDEX | Issue classification type |
| `severity` | VARCHAR(16) | NO | - | INDEX | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| `description` | TEXT | NO | - | - | Diagnostic defect description |
| `ground_truth_label` | VARCHAR(64) | YES | NULL | INDEX | Label for ground truth evaluation |
| `expected_decision` | VARCHAR(64) | NO | - | - | Required system decision |
| `detected_decision` | VARCHAR(64) | YES | NULL | - | Actual decision produced by detector |
| `detection_status` | VARCHAR(32) | NO | 'OPEN' | INDEX | Lifecycle: `OPEN`, `DETECTED`, `RESOLVED`, `SUPPRESSED` |
| `is_injected` | BOOLEAN | NO | FALSE | - | Flag indicating injected synthetic anomaly |
| `detected_at` | DATETIME | YES | NULL | - | Detection timestamp |
| `created_at` | DATETIME | NO | CURRENT_TIMESTAMP | - | Creation timestamp |


## Repair additions and corrections — 2026-10-31

There are 16 mapped tables, including `users`, `password_reset_otps`, and `id_sequences`. `id_sequences.sequence_name` is the primary key; `current_value` is a BIGINT; `updated_at` is UTC. It is an allocation counter inside the enclosing business transaction, not a user-editable asset identifier.

`deposit_ledger.transaction_reference` now has unique constraint `uq_deposit_reference`. `related_ledger_id` references the original deposit ledger entry for new refunds. It is not a ground-truth label. Existing duplicate references block migration rather than being deleted.

New event types include RETURN_REQUESTED, INSPECTED_GOOD, INSPECTED_DAMAGED, INSPECTED_UNUSABLE, REPAIR_STARTED and REPAIR_COMPLETED. Inspection/repair completion preserve location and custodian unless a physical transfer was explicitly recorded. Loss clears both; transit clears physical facility location.

New schema installation uses frozen Alembic operations, including server-side timestamp/scalar defaults needed by raw seed import. Legacy `database/schema.sql` is a historical alternative, not the complete current schema by itself; follow it with migrations if used.
