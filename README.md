# ReturnFlow 📦
### Reusable Asset Return & Lifecycle Management System

ReturnFlow is an enterprise-grade, data-driven software solution designed to coordinate reusable packaging, pallets, transport containers, equipment, shipments, chain-of-custody handoffs, customer returns, QA inspections, refurbishments, and financial security deposits across multi-node supply chain networks.

Built for the **AI Forward Deployed Engineer** technical recruitment assessment, ReturnFlow demonstrates robust relational database design, Python backend engineering, event-based custody traceability, deterministic synthetic data generation at scale (20,000+ assets, 100,000+ events), independent anomaly detection, signed deposit ledger management and financial reconciliation, interactive operational dashboards, and automated verification.

---

## 1. Key Business Capabilities

1. **Complete Chain-of-Custody Traceability:**
   Every physical movement and handoff is recorded as an immutable `CustodyEvent`. Historical records are never updated in place.
2. **Materialized State Projection with Self-Healing Verification:**
   Fast current-state queries via materialized projections on `reusable_assets` (`current_location_id`, `current_custodian_owner_id`, `asset_status`), coupled with a service that rebuilds projections directly from the immutable event log.
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
- **Database:** MySQL 8.0+ / 9.1 Community Server (InnoDB, Foreign Key Constraints, Composite Indexes) • Fully compatible with Supabase PostgreSQL
- **Data Engineering & Analytics:** Pandas, NumPy, Faker, Python Datetime
- **Testing:** Pytest, HTTPX, SQLAlchemy Unit-of-Work
- **Dashboard & UI:** Streamlit, Plotly Express & Graph Objects
- **Authentication & Security:** Role-based access control (Admin, Operations Manager, Logistics Analyst, Warehouse Operator), authentication and authorization services
- **Deployment & Telemetry:** Deployment-ready configuration for container-based hosting; Cloudflare Pages and Fly.io compatibility considerations; Google Analytics configuration support

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
├── tests/                          # Automated Pytest suite (58 tests passed in final audit)
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
- MySQL Server 8.0 or later (running locally on port 3306), or Supabase PostgreSQL instance
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
TEST_DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/returnflow_test_db?charset=utf8mb4
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

Ensure MySQL is running, then create the database and apply migrations:

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

The database-loading generator refuses to replace populated tables by default. Use an empty database for normal loads. `--replace-existing` explicitly enables table truncation and should be used only with a disposable database after taking a backup.

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

Opens the enterprise operational dashboard at `http://localhost:8501`.

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
