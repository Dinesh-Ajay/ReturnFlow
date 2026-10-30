-- ReturnFlow Database Schema (MySQL 8.0+ / InnoDB)
-- Database: returnflow_db
-- Character Set: utf8mb4, Collation: utf8mb4_unicode_ci

CREATE DATABASE IF NOT EXISTS returnflow_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE returnflow_db;

-- 1. Asset Types
CREATE TABLE IF NOT EXISTS asset_types (
    asset_type_id INT AUTO_INCREMENT PRIMARY KEY,
    type_code VARCHAR(32) NOT NULL UNIQUE,
    type_name VARCHAR(100) NOT NULL,
    description TEXT NULL,
    default_deposit_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    expected_lifecycle_days INT NOT NULL DEFAULT 365,
    return_due_days INT NOT NULL DEFAULT 30,
    loss_threshold_days INT NOT NULL DEFAULT 60,
    requires_inspection BOOLEAN NOT NULL DEFAULT TRUE,
    repairable BOOLEAN NOT NULL DEFAULT TRUE,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_asset_types_code (type_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Owners
CREATE TABLE IF NOT EXISTS owners (
    owner_id INT AUTO_INCREMENT PRIMARY KEY,
    owner_code VARCHAR(32) NOT NULL UNIQUE,
    owner_name VARCHAR(150) NOT NULL,
    owner_type VARCHAR(50) NOT NULL,
    contact_email VARCHAR(150) NULL,
    contact_phone VARCHAR(50) NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_owners_code (owner_code),
    INDEX idx_owners_type (owner_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Locations
CREATE TABLE IF NOT EXISTS locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    location_code VARCHAR(32) NOT NULL UNIQUE,
    location_name VARCHAR(150) NOT NULL,
    location_type VARCHAR(50) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL DEFAULT 'USA',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_locations_code (location_code),
    INDEX idx_locations_type (location_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Reusable Assets
CREATE TABLE IF NOT EXISTS reusable_assets (
    asset_id VARCHAR(32) PRIMARY KEY,
    asset_type_id INT NOT NULL,
    owner_id INT NOT NULL,
    serial_number VARCHAR(64) NOT NULL UNIQUE,
    asset_status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE',
    manufacture_date DATE NOT NULL,
    purchase_date DATE NOT NULL,
    current_location_id INT NULL,
    current_custodian_owner_id INT NULL,
    acquisition_cost DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    deposit_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    last_event_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_assets_type FOREIGN KEY (asset_type_id) REFERENCES asset_types(asset_type_id) ON DELETE RESTRICT,
    CONSTRAINT fk_assets_owner FOREIGN KEY (owner_id) REFERENCES owners(owner_id) ON DELETE RESTRICT,
    CONSTRAINT fk_assets_location FOREIGN KEY (current_location_id) REFERENCES locations(location_id) ON DELETE SET NULL,
    CONSTRAINT fk_assets_custodian FOREIGN KEY (current_custodian_owner_id) REFERENCES owners(owner_id) ON DELETE SET NULL,
    INDEX idx_assets_type (asset_type_id),
    INDEX idx_assets_owner (owner_id),
    INDEX idx_assets_status (asset_status),
    INDEX idx_assets_location (current_location_id),
    INDEX idx_assets_custodian (current_custodian_owner_id),
    INDEX idx_assets_last_event (last_event_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Shipments
CREATE TABLE IF NOT EXISTS shipments (
    shipment_id VARCHAR(32) PRIMARY KEY,
    origin_location_id INT NOT NULL,
    destination_location_id INT NOT NULL,
    carrier_owner_id INT NOT NULL,
    dispatch_date DATETIME NOT NULL,
    expected_delivery_date DATETIME NOT NULL,
    actual_delivery_date DATETIME NULL,
    shipment_status VARCHAR(32) NOT NULL DEFAULT 'PLANNED',
    tracking_reference VARCHAR(64) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_shipments_origin FOREIGN KEY (origin_location_id) REFERENCES locations(location_id) ON DELETE RESTRICT,
    CONSTRAINT fk_shipments_dest FOREIGN KEY (destination_location_id) REFERENCES locations(location_id) ON DELETE RESTRICT,
    CONSTRAINT fk_shipments_carrier FOREIGN KEY (carrier_owner_id) REFERENCES owners(owner_id) ON DELETE RESTRICT,
    INDEX idx_shipments_origin (origin_location_id),
    INDEX idx_shipments_dest (destination_location_id),
    INDEX idx_shipments_carrier (carrier_owner_id),
    INDEX idx_shipments_status (shipment_status),
    INDEX idx_shipments_dispatch (dispatch_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Shipment Assets Bridge
CREATE TABLE IF NOT EXISTS shipment_assets (
    shipment_asset_id INT AUTO_INCREMENT PRIMARY KEY,
    shipment_id VARCHAR(32) NOT NULL,
    asset_id VARCHAR(32) NOT NULL,
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    removed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_shipment_asset UNIQUE (shipment_id, asset_id),
    CONSTRAINT fk_sa_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
    CONSTRAINT fk_sa_asset FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id) ON DELETE CASCADE,
    INDEX idx_sa_shipment (shipment_id),
    INDEX idx_sa_asset (asset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Custody Events
CREATE TABLE IF NOT EXISTS custody_events (
    custody_event_id VARCHAR(64) PRIMARY KEY,
    asset_id VARCHAR(32) NOT NULL,
    shipment_id VARCHAR(32) NULL,
    from_owner_id INT NULL,
    to_owner_id INT NULL,
    from_location_id INT NULL,
    to_location_id INT NULL,
    actor_owner_id INT NULL,
    event_type VARCHAR(32) NOT NULL,
    event_timestamp DATETIME NOT NULL,
    event_reference VARCHAR(64) NULL,
    notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_ce_asset FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id) ON DELETE CASCADE,
    CONSTRAINT fk_ce_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE SET NULL,
    CONSTRAINT fk_ce_from_owner FOREIGN KEY (from_owner_id) REFERENCES owners(owner_id) ON DELETE SET NULL,
    CONSTRAINT fk_ce_to_owner FOREIGN KEY (to_owner_id) REFERENCES owners(owner_id) ON DELETE SET NULL,
    CONSTRAINT fk_ce_from_loc FOREIGN KEY (from_location_id) REFERENCES locations(location_id) ON DELETE SET NULL,
    CONSTRAINT fk_ce_to_loc FOREIGN KEY (to_location_id) REFERENCES locations(location_id) ON DELETE SET NULL,
    CONSTRAINT fk_ce_actor FOREIGN KEY (actor_owner_id) REFERENCES owners(owner_id) ON DELETE SET NULL,
    INDEX idx_ce_asset (asset_id),
    INDEX idx_ce_shipment (shipment_id),
    INDEX idx_ce_type (event_type),
    INDEX idx_ce_timestamp (event_timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Return Authorizations (RMAs)
CREATE TABLE IF NOT EXISTS return_authorizations (
    rma_id VARCHAR(32) PRIMARY KEY,
    requesting_owner_id INT NOT NULL,
    receiving_owner_id INT NOT NULL,
    return_location_id INT NOT NULL,
    requested_date DATETIME NOT NULL,
    approved_date DATETIME NULL,
    expected_return_date DATETIME NOT NULL,
    actual_return_date DATETIME NULL,
    rma_status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
    reason VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rma_req_owner FOREIGN KEY (requesting_owner_id) REFERENCES owners(owner_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rma_rec_owner FOREIGN KEY (receiving_owner_id) REFERENCES owners(owner_id) ON DELETE RESTRICT,
    CONSTRAINT fk_rma_ret_loc FOREIGN KEY (return_location_id) REFERENCES locations(location_id) ON DELETE RESTRICT,
    INDEX idx_rma_req_owner (requesting_owner_id),
    INDEX idx_rma_rec_owner (receiving_owner_id),
    INDEX idx_rma_ret_loc (return_location_id),
    INDEX idx_rma_status (rma_status),
    INDEX idx_rma_req_date (requested_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Return Authorization Assets Bridge
CREATE TABLE IF NOT EXISTS return_authorization_assets (
    rma_asset_id INT AUTO_INCREMENT PRIMARY KEY,
    rma_id VARCHAR(32) NOT NULL,
    asset_id VARCHAR(32) NOT NULL,
    return_condition VARCHAR(32) NULL,
    received_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rma_asset UNIQUE (rma_id, asset_id),
    CONSTRAINT fk_raa_rma FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id) ON DELETE CASCADE,
    CONSTRAINT fk_raa_asset FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id) ON DELETE CASCADE,
    INDEX idx_raa_rma (rma_id),
    INDEX idx_raa_asset (asset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. Inspections
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id VARCHAR(32) PRIMARY KEY,
    asset_id VARCHAR(32) NOT NULL,
    rma_id VARCHAR(32) NULL,
    inspector_owner_id INT NOT NULL,
    inspection_date DATETIME NOT NULL,
    condition_status VARCHAR(32) NOT NULL,
    damage_severity VARCHAR(32) NULL,
    requires_repair BOOLEAN NOT NULL DEFAULT FALSE,
    inspection_notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_insp_asset FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id) ON DELETE CASCADE,
    CONSTRAINT fk_insp_rma FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id) ON DELETE SET NULL,
    CONSTRAINT fk_insp_inspector FOREIGN KEY (inspector_owner_id) REFERENCES owners(owner_id) ON DELETE RESTRICT,
    INDEX idx_insp_asset (asset_id),
    INDEX idx_insp_rma (rma_id),
    INDEX idx_insp_inspector (inspector_owner_id),
    INDEX idx_insp_status (condition_status),
    INDEX idx_insp_date (inspection_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Repairs
CREATE TABLE IF NOT EXISTS repairs (
    repair_id VARCHAR(32) PRIMARY KEY,
    asset_id VARCHAR(32) NOT NULL,
    inspection_id VARCHAR(32) NULL,
    repair_location_id INT NOT NULL,
    repair_status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
    repair_start_date DATETIME NOT NULL,
    repair_completion_date DATETIME NULL,
    repair_cost DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    repair_notes TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rep_asset FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id) ON DELETE CASCADE,
    CONSTRAINT fk_rep_inspection FOREIGN KEY (inspection_id) REFERENCES inspections(inspection_id) ON DELETE SET NULL,
    CONSTRAINT fk_rep_location FOREIGN KEY (repair_location_id) REFERENCES locations(location_id) ON DELETE RESTRICT,
    INDEX idx_rep_asset (asset_id),
    INDEX idx_rep_inspection (inspection_id),
    INDEX idx_rep_location (repair_location_id),
    INDEX idx_rep_status (repair_status),
    INDEX idx_rep_start (repair_start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Deposit Ledger
CREATE TABLE IF NOT EXISTS deposit_ledger (
    ledger_id INT AUTO_INCREMENT PRIMARY KEY,
    asset_id VARCHAR(32) NOT NULL,
    owner_id INT NOT NULL,
    shipment_id VARCHAR(32) NULL,
    rma_id VARCHAR(32) NULL,
    transaction_type VARCHAR(32) NOT NULL,
    transaction_amount DECIMAL(12, 2) NOT NULL,
    transaction_reference VARCHAR(64) NOT NULL,
    transaction_date DATETIME NOT NULL,
    related_ledger_id INT NULL,
    description VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_dl_asset FOREIGN KEY (asset_id) REFERENCES reusable_assets(asset_id) ON DELETE CASCADE,
    CONSTRAINT fk_dl_owner FOREIGN KEY (owner_id) REFERENCES owners(owner_id) ON DELETE RESTRICT,
    CONSTRAINT fk_dl_shipment FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE SET NULL,
    CONSTRAINT fk_dl_rma FOREIGN KEY (rma_id) REFERENCES return_authorizations(rma_id) ON DELETE SET NULL,
    CONSTRAINT fk_dl_related FOREIGN KEY (related_ledger_id) REFERENCES deposit_ledger(ledger_id) ON DELETE SET NULL,
    INDEX idx_dl_asset (asset_id),
    INDEX idx_dl_owner (owner_id),
    INDEX idx_dl_shipment (shipment_id),
    INDEX idx_dl_rma (rma_id),
    INDEX idx_dl_ref (transaction_reference),
    INDEX idx_dl_type (transaction_type),
    INDEX idx_dl_date (transaction_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 13. Anomaly Records (Audit & Anomaly Tracking)
CREATE TABLE IF NOT EXISTS anomaly_records (
    issue_id VARCHAR(64) PRIMARY KEY,
    affected_asset_id VARCHAR(32) NULL,
    affected_record_id VARCHAR(64) NOT NULL,
    entity_name VARCHAR(64) NOT NULL,
    issue_type VARCHAR(64) NOT NULL,
    severity VARCHAR(16) NOT NULL,
    description TEXT NOT NULL,
    ground_truth_label VARCHAR(64) NULL,
    expected_decision VARCHAR(64) NOT NULL,
    detected_decision VARCHAR(64) NULL,
    detection_status VARCHAR(32) NOT NULL DEFAULT 'OPEN',
    is_injected BOOLEAN NOT NULL DEFAULT FALSE,
    detected_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ar_asset (affected_asset_id),
    INDEX idx_ar_record (affected_record_id),
    INDEX idx_ar_type (issue_type),
    INDEX idx_ar_severity (severity),
    INDEX idx_ar_status (detection_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
