# ReturnFlow 📦
### Reusable Asset Return & Lifecycle Management System

ReturnFlow is an data-driven assessment software solution designed to coordinate reusable packaging, pallets, transport containers, equipment, shipments, chain-of-custody handoffs, customer returns, QA inspections, refurbishments, and financial security deposits across multi-node supply chain networks.

Built for the **AI Forward Deployed Engineer** technical recruitment assessment, ReturnFlow demonstrates robust relational database design, Python backend engineering, event-based custody traceability, deterministic synthetic data generation at scale (20,000+ assets, 100,000+ events), independent anomaly detection, signed deposit ledger management and financial reconciliation, interactive operational dashboards, and automated verification.

---


> **Repair status — 2026-10-31: PARTIAL overall.** Code corrections and 116 automated tests pass on disposable MariaDB databases. The immutable historical dataset still has 4,956 replay exceptions, and original company assessment files/local unpublished Git changes were unavailable. See `FINAL_CRITICAL_FIX_REPORT.md` and `docs/requirement_traceability.md`. No automatic historical-data repair was performed.

## 1. Key Business Capabilities

1. **Complete Chain-of-Custody Traceability:**
   New live workflows append custody/domain events atomically with their projections. ORM edits/deletes are rejected; legacy seeded histories have documented gaps and database-admin writes are outside this guard.
2. **Materialized State Projection with Read-Only Replay Verification:**
   Fast current-state queries via materialized projections on `reusable_assets` (`current_location_id`, `current_custodian_owner_id`, `asset_status`), coupled with read-only replay of custody events and legacy inspection/repair facts. Replay does not silently overwrite projections or invent missing evidence.
3. **Deterministic Scale Synthetic Generator:**
   Fixed-seed generation (`20261022`) supporting both a developer starter profile (200 assets, 1,000 events) and a full-scale benchmark profile (20,000 assets, 10,000 shipments, 100,030 custody events) executing in ~1.2 seconds.
4. **Independent Anomaly Detection Engine:**
   Detects the five required anomaly scenarios from operational records and evaluates findings against a separate positive-label ground-truth file. Current synthetic evaluation is 50 TP, 0 FP, and 0 FN; no labelled-negative population exists, so TN and false-positive rate are unavailable.
5. **Signed Deposit Ledger Reconciliation:**
   Security deposits tracked as liabilities (`DEPOSIT_CHARGE`), refundable only up to the eligible balance upon good return, deducting assessed damage fees.
6. **Enterprise SaaS Dashboard & REST API:**
   Modern light-theme dashboard matching enterprise Figma design with dark navy navigation, vertical custody timeline steppers, Plotly charts, and full Swagger API documentation.

---

## 2. Technology Stack

- **Backend:** Python 3.11 / 3.13, FastAPI, SQLAlchemy 2.0 ORM, Pydantic v2, Alembic
- **Database:** MySQL 8.0+ / 9.1 Community Server (InnoDB, Foreign Key Constraints, Composite Indexes); this repair was executed on MariaDB 10.11. PostgreSQL/Supabase end-to-end compatibility is not verified.
- **Data Engineering & Analytics:** Pandas, NumPy, Faker, Python Datetime
- **Testing:** Pytest, HTTPX, SQLAlchemy Unit-of-Work
- **Dashboard & UI:** Streamlit, Plotly Express & Graph Objects
- **Authentication & Security:** JWT authentication and explicit role policy (Operations Manager, Operations Staff, Finance Manager, Viewer); not an external Better Auth integration
- **Deployment & Telemetry:** Cloud hosting and telemetry integrations are planned/configuration placeholders, not verified deployed integrations

---

## 3. System Architecture & Directory Structure

```
ReturnFlow/
│
├── app/
│   ├── main.py                     # FastAPI application entrypoint & middleware
│   ├── config.py                   # Central configuration & environment loader
│   ├── database/
│   │   ├── base.py                 # SQLAlchemy Declarative Base
│   │   ├── connection.py           # Engine & connection pool configuration
│   │   └── session.py              # SessionLocal & get_db dependency
│   ├── models/                     # 13 SQLAlchemy models
│   │   ├── asset_type.py           # Asset categories & lifecycle rules
│   │   ├── asset.py                # Reusable assets & materialized projections
│   │   ├── owner.py                # Enterprise entities & commercial roles
│   │   ├── location.py             # Supply chain facilities & hubs
│   │   ├── shipment.py             # Multi-asset transport manifests
│   │   ├── shipment_asset.py       # Shipment-to-asset bridge table
│   │   ├── custody_event.py        # Immutable chain-of-custody event stream
│   │   ├── return_authorization.py # RMAs & return authorizations
│   │   ├── return_authorization_asset.py # RMA-to-asset bridge table
│   │   ├── inspection.py           # QA damage evaluations
│   │   ├── repair.py               # Maintenance & refurbishment operations
│   │   ├── deposit_ledger.py       # Financial security deposits & refunds
│   │   └── anomaly_record.py       # Injected & runtime detected anomalies
│   ├── schemas/                    # Pydantic request/response validation schemas
│   ├── api/                        # REST API routers & dependencies
│   ├── services/                   # Business domain services (Lifecycle, Custody, Deposit, etc.)
│   ├── generator/                  # Deterministic synthetic data generator & exporter
│   ├── validation/                 # Independent validation & evaluation engine
│   ├── analytics/                  # KPI & operational metrics engine
│   └── utils/                      # ID generator & logging configuration
│
├── dashboard/
│   └── streamlit_app.py            # Enterprise SaaS operational dashboard
│
├── database/
│   ├── schema.sql                  # Full DDL schema with constraints & indexes
│   └── migrations/                 # Alembic migration scripts
│
├── data/
│   ├── generated/                  # Exported CSVs for all entities
│   ├── ground_truth/               # ground_truth.csv and ground_truth.json
│   └── exports/                    # returnflow_seed.sql, validation_summary.json, analytics_summary.json
│
├── docs/                           # Complete technical documentation suite
│   ├── architecture.md             # Component architecture & Mermaid ERD
│   ├── data_dictionary.md          # Full data dictionary for all fields & constraints
│   ├── business_rules.md           # Lifecycle rules, transitions, and formulas
│   ├── assumptions.md              # Domain assumptions & accounting model
│   ├── validation_report.md        # Independent validation results & confusion matrix
│   ├── performance_report.md       # Measured execution durations & query latencies
│   ├── reproducibility_report.md   # Determinism & multi-run verification
│   └── limitations.md              # Known limitations & development roadmap
│
├── prompts/
│   └── ai_prompt_history.md        # Comprehensive AI interaction transparency log
│
├── tests/                          # Automated Pytest suite (116 tests passed in this repair; see final evidence)
│
├── .env.example                    # Environment variable template
├── requirements.txt                # Python dependencies
├── alembic.ini                     # Migration configuration
└── README.md                       # Master project documentation
```

---

## 4. Getting Started & Installation

### Prerequisites

- Python 3.11 or later
- MySQL-compatible InnoDB server; tested here with MariaDB 10.11.14. Actual MySQL 8/9 and PostgreSQL runs remain unverified
- Git

### Step 1: Clone and Configure Environment

```bash
git clone https://github.com/Dinesh-Ajay/ReturnFlow.git
cd ReturnFlow

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create `.env` based on `.env.example`:

```ini
DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/returnflow_db?charset=utf8mb4
TEST_DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/returnflow_test?charset=utf8mb4
RANDOM_SEED=20261022
REFERENCE_DATE=2026-10-22
DATA_PROFILE=full
BATCH_SIZE=1000
ENVIRONMENT=development
AUTH_SECRET=<random secret of at least 32 characters>
INITIAL_ADMIN_PASSWORD=<strong initial password>
GA_MEASUREMENT_ID=G-RETURNFLOW01
API_HOST=127.0.0.1
API_PORT=8000
```

### Step 3: Initialize Database

Create an empty database and a least-privilege application user using your database administration process. Set `DATABASE_URL` before running migrations. Revisions `0026_complete_schema` and `0027_ledger_idempotency` provide the complete schema and unique financial idempotency key; the historic initial revision remains in the chain.

For an existing database, back up first and review schema differences. Upgrade preserves rows, but DDL is not transactional on MySQL/MariaDB and duplicate financial references deliberately block the unique-key migration. No automatic destructive downgrade is provided.

Apply migrations:

```bash
# Run Alembic migrations
python -m alembic upgrade head
```

---

## 5. Execution Commands

### Generate Synthetic Datasets

```bash
# Generate a starter dataset and export files without touching the database
python -m app.generator --profile starter --no-db

# Generate a full dataset and export files without touching the database
python -m app.generator --profile full --seed 20261022 --no-db
```

The database-loading generator refuses to replace populated tables by default. Use an empty database for normal loads. `--replace-existing` is restricted to a disposable `_test`/`_test_` database and uses dependency-ordered transactional deletes. The loader never disables foreign keys or truncates tables. Do not use replacement loads for data you need to preserve.

### Verify counts, reproducibility, and performance

```bash
python -m app.validation.counts
python -m app.validation.reproducibility --profile full --seed 20261022
python -m app.validation.benchmark
```

### Run Independent Data Validation & Anomaly Detection

```bash
python -m app.validation
```

*Outputs a complete machine-readable audit report to `data/exports/validation_summary.json`.*

### Start FastAPI Backend Server

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Application:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Redoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### Start Streamlit Operational Dashboard

```bash
streamlit run dashboard/streamlit_app.py
```

Opens the operational dashboard at `http://localhost:8501`. Both the web portal and Streamlit require sign-in. Configure an initial administrator password explicitly; none is embedded or prefilled. Configure a stable AUTH_SECRET before using multiple processes; production rejects an absent/short configured secret.

### Run Automated Pytest Suite

```bash
python -m pytest -v
```

The test suite requires a dedicated test database with a full-profile dataset. Set both `DATABASE_URL` and `TEST_DATABASE_URL` to a separately named database ending in `_test` (or containing `_test_`); tests refuse to run against an ordinary database name. The existing test suite performs writes and commits.

---

## 6. Sample API Requests

### 1. Health Check
```bash
curl -X GET "http://127.0.0.1:8000/health"
```
**Response:**
```json
{
  "status": "HEALTHY",
  "app_name": "ReturnFlow",
  "version": "1.0.0",
  "database_connected": true,
  "environment": "development"
}
```

### 2. Search Assets with Pagination & Status Filtering
```bash
curl -X GET "http://127.0.0.1:8000/api/assets?page=1&page_size=2&status=IN_CUSTODY"
```
**Response:**
```json
{
  "total_count": 2400,
  "page": 1,
  "page_size": 2,
  "items": [
    {
      "asset_id": "ASSET-0000003",
      "serial_number": "SN-CONTAINER-0000003",
      "type_code": "CONTAINER",
      "type_name": "Heavy-Duty Plastic Bulk Container",
      "owner_name": "FreshMart Retail Inc",
      "current_location_name": "Los Angeles DC",
      "asset_status": "IN_CUSTODY",
      "deposit_amount": 250.0,
      "days_outstanding": 28,
      "is_overdue": false
    }
  ]
}
```

### 3. Reconstruct Complete Asset Custody Traceability
```bash
curl -X GET "http://127.0.0.1:8000/api/assets/ASSET-0000001"
```
**Response:**
Returns asset master metadata, current custodian, chronological events array, shipment manifests, RMA history, inspections, repairs, and financial ledger transactions.

### 4. Trigger Independent Validation & Detection
```bash
curl -X POST "http://127.0.0.1:8000/api/validation/run"
```
*Illustrative response for a successful synthetic-data validation run; actual execution metrics may vary.*
**Response:**
```json
{
  "status": "COMPLETED",
  "total_duration_seconds": 2.425,
  "evaluation_metrics": {
    "total_injected": 50,
    "total_detected": 50,
    "true_positives": 50,
    "false_positives": 0,
    "false_negatives": 0,
    "precision_pct": 100.0,
    "recall_pct": 100.0
  }
}
```

---

## 7. Audit and verification

The detailed requirement-by-requirement evidence, actual database counts, results, blockers, and known limitations are maintained in [FINAL_REQUIREMENTS_AUDIT.md](FINAL_REQUIREMENTS_AUDIT.md). Measured reports are in `docs/` and machine-readable run outputs are in `data/exports/`.


## Repair verification and dataset provenance

Run tests only with a dedicated database name ending `_test` or containing `_test_`:

```bash
python -m alembic upgrade head
python -m app.validation.counts
python -m app.validation.acceptance_audit
python -m app.validation.reproducibility --profile full --seed 20261022
python -m pytest -v
```

The test suite requires a populated full-profile dedicated test database. A fresh database can be loaded with `python -m app.generator --profile full --seed 20261022` after pointing `DATABASE_URL` at that empty test database. This exports data too; use `RETURNFLOW_GENERATED_DIR`, `RETURNFLOW_GROUND_TRUTH_DIR`, and `RETURNFLOW_EXPORTS_DIR` to isolate outputs from the checked-in historical files.

**Always pair the database with its matching ground truth.** Set `RETURN_FLOW_TEST_GROUND_TRUTH_DIR` for pytest and `RETURNFLOW_GROUND_TRUTH_DIR` for normal commands when using an alternate generated dataset. The committed artifact set differs from the current generator's anomaly targeting despite equal seed/counts; never mix the two label files. These repair runs did not replace committed data.

`data/source_manifest.json` hashes the preserved historical artifacts and records that their exact producing commit is unknown. Fresh generator exports now emit an accompanying source manifest. Logical repeatability excludes database timestamps, not business fields.

`GET /api/deposits/reconciliation` reports portfolio arithmetic **and** individual obligations. The deliberately anomalous seed correctly returns `is_reconciled=false`; a positive portfolio total is not sufficient. Repair costs are separately billed, while damage/loss charges consume deposits. This is a signed liability ledger, not a double-entry general ledger.

Current standing uses the fixed UTC reference date 2026-10-22 and the latest active-cycle dispatch, not the latest scan. Dashboard reporting dates filter activity; current holding/age metrics retain the same standing reference date, exposed as `standing_reference_date`. They are not historical as-of portfolio reconstructions.

Live delivery supports `POST /api/shipments/{shipment_id}/deliver` with `actual_delivery_date` and optional `receiving_owner_id`. Supply the actual recipient; if omitted, the legacy convention uses each asset's legal owner. The event records the selected custodian without changing legal ownership.

Business APIs require bearer tokens. Health, documentation, static login assets and recovery/login entry points remain public. Read access is allowed to the four documented roles; operations writes are manager/staff, financial writes manager/finance, and validation runs manager-only. Database roles, not client headers/token role claims, determine permissions. This is a small application policy, not tenant isolation or a comprehensive enterprise IAM system.

Security limitations: token logout is client-side (no revocation list), browser tokens remain in localStorage, login lacks a distributed rate limiter, SMTP delivery was not externally exercised, and password-reset token storage deserves further hardening. Do not expose the assessment deployment publicly without operational security controls.
