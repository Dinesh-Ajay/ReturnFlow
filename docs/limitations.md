# ReturnFlow Known Limitations & Future Improvements

This document transparently records current system limitations and planned architectural enhancements.

---

## 1. Known Architectural Limitations

1. **Single Currency Handling:**
   - The current financial ledger assumes all deposit, repair, and penalty figures are denominated in USD. Multi-currency conversions and foreign exchange hedging are not currently implemented.
2. **Fixed Reference Date:**
   - Synthetic data generation and overdue standing calculations use a static `REFERENCE_DATE` (`2026-10-22`) for perfect reproducibility. In live production, this should switch to `datetime.now(timezone.utc)`.
3. **In-Process Background Task Execution:**
   - Long-running dataset generation and full validation passes currently execute in Python thread/process contexts. At hyper-scale (> 1,000,000 assets), an asynchronous task queue (e.g. Celery / Redis / Temporal) is recommended.
4. **Physical RFID / Telemetry Scans:**
   - Scan events are modeled as discrete REST API / batch operations. Real-time MQTT / WebSocket streaming ingestion from dock door RFID readers is not yet included.

---

## 2. Planned Future Improvements

1. **Automated Handoff Smart Contracts:**
   - Implement verifiable custody handoffs using cryptographic signatures from carrier and receiver drivers upon dock transfer.
2. **Predictive Loss Risk Modeling:**
   - Incorporate an ML classifier trained on custody dwell times, carrier routes, and asset types to predict probability of asset loss 10 days before reaching overdue thresholds.
3. **Geo-Fencing & GPS Telemetry:**
   - Extend `Location` with geospatial polygon boundaries (`ST_GeomFromText`) and integrate automated transit geofence triggers.
4. **Automated Deposit Escrow Integration:**
   - Integrate automated ACH / credit card deposit pre-authorization holds and automated settlement via banking APIs.
