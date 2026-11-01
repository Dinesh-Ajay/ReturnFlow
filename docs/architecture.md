# ReturnFlow Architecture Documentation

## 1. System Overview

**ReturnFlow** is an enterprise data-driven software solution designed to coordinate reusable packaging, pallets, transport crates, equipment, custody transfers, returns, inspections, repairs, and financial deposits across supply chain networks.

### Layered Architectural Model

```mermaid
flowchart TD
    subgraph UI_Layer["Presentation & Dashboard Layer"]
        StreamlitApp["Streamlit Operational UI (Enterprise SaaS)"]
        AnalyticsViz["Plotly Visualizations & Interactive Reports"]
    end

    subgraph API_Layer["Application & API Layer (FastAPI)"]
        AuthMiddleware["JWT Authentication + Explicit Route Role Policy"]
        RouterAsset["Asset & History Routers"]
        RouterShipment["Shipment & Manifest Routers"]
        RouterCustody["Custody Traceability Routers"]
        RouterReturn["Return Authorization (RMA) Routers"]
        RouterInspection["Inspection & Repair Routers"]
        RouterFinancial["Financial Ledger & Deposit Routers"]
        RouterValidation["Validation & Anomaly Routers"]
    end

    subgraph Service_Layer["Business Logic Layer"]
        LifecycleSvc["LifecycleService (Transitions & Age)"]
        CustodySvc["CustodyService (Traceability & Projections)"]
        DepositSvc["DepositService (Ledger & Reconciliation)"]
        ShipmentSvc["ShipmentService"]
        ReturnSvc["ReturnService"]
        InspectionSvc["InspectionService"]
        RepairSvc["RepairService"]
    end

    subgraph Engine_Layer["Validation & Engine Layer"]
        IntegrityEngine["Integrity Validator (PK, FK, Unique)"]
        CustodyEngine["Custody Validator (Simultaneous, Conflicts)"]
        LifecycleEngine["Lifecycle Validator (Chronology, Order)"]
        FinancialEngine["Financial Validator (Duplicate Refunds)"]
        DetectionEngine["Anomaly Detection & GT Evaluation Engine"]
    end

    subgraph Database_Layer["Database Layer (MySQL 8.0+ / Supabase PostgreSQL)"]
        DBEngine["SQLAlchemy ORM + Connection Pooling"]
        DBTables["returnflow_db (13 Relational Tables)"]
        AlembicMigrations["Alembic Versioned Migrations"]
    end

    StreamlitApp --> API_Layer
    AnalyticsViz --> API_Layer
    API_Layer --> Service_Layer
    Service_Layer --> Database_Layer
    Engine_Layer --> Database_Layer
```

---

## 2. Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    AssetType ||--o{ ReusableAsset : "categorizes (1:N)"
    Owner ||--o{ ReusableAsset : "owns (1:N)"
    Owner ||--o{ ReusableAsset : "current custodian (1:N)"
    Location ||--o{ ReusableAsset : "current location (1:N)"
    
    Location ||--o{ Shipment : "originates (1:N)"
    Location ||--o{ Shipment : "destined for (1:N)"
    Owner ||--o{ Shipment : "carries (1:N)"
    
    Shipment ||--|{ ShipmentAsset : "contains (1:N)"
    ReusableAsset ||--|{ ShipmentAsset : "manifest member (1:N)"
    
    ReusableAsset ||--|{ CustodyEvent : "tracks history (1:N)"
    Shipment ||--o{ CustodyEvent : "in transit on (1:N)"
    Owner ||--o{ CustodyEvent : "actor (1:N)"
    Location ||--o{ CustodyEvent : "to location (1:N)"
    
    Owner ||--o{ ReturnAuthorization : "requests (1:N)"
    Owner ||--o{ ReturnAuthorization : "receives (1:N)"
    Location ||--o{ ReturnAuthorization : "return facility (1:N)"
    
    ReturnAuthorization ||--|{ ReturnAuthorizationAsset : "authorizes (1:N)"
    ReusableAsset ||--|{ ReturnAuthorizationAsset : "authorized item (1:N)"
    
    ReusableAsset ||--o{ Inspection : "evaluated by (1:N)"
    ReturnAuthorization ||--o{ Inspection : "originates from (1:N)"
    
    ReusableAsset ||--o{ Repair : "repaired by (1:N)"
    Inspection ||--o{ Repair : "triggers (1:N)"
    Location ||--o{ Repair : "repair center (1:N)"
    
    ReusableAsset ||--o{ DepositLedger : "charges/refunds (1:N)"
    Owner ||--o{ DepositLedger : "billed/refunded (1:N)"
    Shipment ||--o{ DepositLedger : "dispatch context (1:N)"
    ReturnAuthorization ||--o{ DepositLedger : "return context (1:N)"
    
    ReusableAsset ||--o{ AnomalyRecord : "flags (1:N)"
```

---

## 3. Data Integrity & Traceability Principles

1. **Append-Only Historical Custody:**
   State changes, transfers, dispatches, and arrivals are appended as immutable `CustodyEvent` records. Historical records are never silently updated or overwritten when an asset moves.
2. **Materialized State Projection:**
   `current_location_id`, `current_custodian_owner_id`, `asset_status`, and `last_event_at` on `ReusableAsset` serve as a read-optimized materialized projection. The system provides `CustodyService.rebuild_asset_projection_from_events()`, which replays custody events plus recorded legacy inspections/repairs and reports incomplete histories without inventing events.
3. **Signed Deposit Liability Ledger:**
   Deposits are treated with signed decimal accounting. Initial deposits are positive liabilities (`DEPOSIT_CHARGE`); refunds are recorded as negative transactions (`DEPOSIT_REFUND`). Duplicate refunds and over-refunds are blocked at both the service and validator layer.
4. **Relational Constraints:**
   Foreign key relationships are strictly maintained using InnoDB / PostgreSQL foreign key constraints with indexed lookup columns to support high-throughput lookups across 20,000+ assets.

---

## 4. Verified boundaries and planned integrations

Verified here: FastAPI + SQLAlchemy + MariaDB 10.11.14, JWT authentication, guarded business routers, explicit four-role policy, in-process validation, and an authenticated Streamlit gate. The portal continues to use the existing HTML/CSS/JavaScript layout.

Supabase/PostgreSQL, external Better Auth, Fly.io, Cloudflare Pages and production telemetry are not established by configuration variables. A production Dockerfile and deployed integrations were not verified. Do not describe these as implemented deployments.

## 5. Repair architecture notes

Persistent ID allocation uses an upsert followed by a row lock, initializes from existing business identifiers, and joins the business transaction. Migrations, not request handlers, create schema.

`atomic_operation` gives live service operations a savepoint; route boundaries commit. `record_transition` centralizes state-machine validation and event/projection writes. Domain facts for inspection and repair are not fabricated physical transfers. Raw custody creation cannot bypass shipment/return/inspection/repair prerequisites. New registrations start AVAILABLE.

The read-only projection service combines explicit domain events with legacy inspection/repair facts when an equivalent domain event is absent. Equal timestamps use deterministic record ordering. Legacy missing movement/post-repair evidence is reported; no self-healing job mutates the archive.

Financial reconciliation includes obligation-level checks, not just a portfolio equation. Unique transaction references provide durable idempotency; explicit original-deposit links take precedence and ambiguous legacy links fail closed.
