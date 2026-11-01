# ReturnFlow Business Rules & Lifecycle Specification

## 1. Asset Lifecycle State Machine

An asset's lifecycle status reflects its commercial and operational readiness, distinct from its physical facility location.

### Permitted Lifecycle States

| State | Definition | Permitted Next States |
| :--- | :--- | :--- |
| `AVAILABLE` | Clean, inspected, and ready for dispatch at a warehouse or DC | `RESERVED`, `DISPATCHED`, `RETIRED` |
| `RESERVED` | Staged for a planned shipment manifest | `DISPATCHED`, `AVAILABLE` |
| `DISPATCHED` | Handed over to carrier at origin dock | `IN_TRANSIT`, `LOST` |
| `IN_TRANSIT` | Under carrier custody en route to destination facility | `IN_CUSTODY`, `RETURNED`, `LOST` |
| `IN_CUSTODY` | Delivered to and actively held by customer or recipient facility | `RETURN_PENDING`, `RETURNED`, `LOST` |
| `RETURN_PENDING` | Covered under an approved Return Authorization (RMA) awaiting carrier pickup | `IN_TRANSIT`, `RETURNED`, `LOST` |
| `RETURNED` | Physically arrived at receiving dock of return facility | `INSPECTION_PENDING`, `AVAILABLE` |
| `INSPECTION_PENDING`| Awaiting QA inspection and condition triage | `AVAILABLE`, `DAMAGED`, `RETIRED` |
| `DAMAGED` | Physical defect detected; quarantined from general fleet | `UNDER_REPAIR`, `RETIRED` |
| `UNDER_REPAIR` | Actively undergoing maintenance at a designated repair center | `INSPECTION_PENDING`, `AVAILABLE`, `RETIRED` |
| `LOST` | Exceeded loss threshold retention days or declared unrecoverable | `INSPECTION_PENDING`, `AVAILABLE` (Recovery transition) |
| `RETIRED` | Terminal state for decommissioned or scrapped assets | None (Terminal) |

---

## 2. Separation of Physical Location and Lifecycle Status

An asset's physical location is tracked independently from its lifecycle state:
- An asset physically stationed at `Dallas Repair Center` (Location Type: `REPAIR_CENTER`) may have lifecycle status `DAMAGED`, `UNDER_REPAIR`, or `INSPECTION_PENDING`.
- An asset in `IN_TRANSIT` status has `current_location_id = NULL` and `current_custodian_owner_id` set to the carrier owner.
- Location changes must never overwrite past movement history.

---

## 3. Outstanding Age, Overdue, and Loss Classification

Calculations are computed deterministically relative to `REFERENCE_DATE` (2026-10-22) using the asset's active dispatch cycle:

1. **Days Outstanding:**
   $$\text{days\_outstanding} = \max(0, \text{REFERENCE\_DATE} - \text{dispatch\_date})$$
   Only active, unreturned dispatch cycles are measured. Historical completed cycles are excluded.

2. **Overdue Classification:**
   $$\text{is\_overdue} \iff (\text{days\_outstanding} > \text{asset\_type.return\_due\_days}) \land (\text{status} \in \{\text{DISPATCHED}, \text{IN\_TRANSIT}, \text{IN\_CUSTODY}, \text{RETURN\_PENDING}\})$$

3. **Lost Classification:**
   $$\text{is\_lost} \iff (\text{days\_outstanding} > \text{asset\_type.loss\_threshold\_days}) \land (\text{status} \neq \text{RETURNED})$$
   Assets already returned or recovered cannot be marked as lost.

---

## 4. Chain of Custody & Event Immutability

1. Every movement or handoff requires an immutable `CustodyEvent` with a deterministic per-asset identifier `CUST-<asset-id>-<counter>`.
2. Handoffs must record both the releasing entity (`from_owner_id`), the receiving entity (`to_owner_id`), and the responsible authorized actor (`actor_owner_id`).
3. Conflicting simultaneous locations for the same asset at the same effective timestamp are prohibited and flagged (`FLAG_FOR_INVESTIGATION`).
4. Chronological reversal (a return timestamp preceding its dispatch) constitutes an invalid lifecycle transition (`INVALID_LIFECYCLE_TRANSITION`).

---

## 5. Inspection & Repair Rules

1. Every asset returned from a customer must undergo QA inspection if `asset_type.requires_inspection == TRUE`.
2. Condition statuses:
   - `GOOD`: Triggers lifecycle transition to `AVAILABLE` and authorizes deposit refund.
   - `DAMAGED`: Triggers lifecycle transition to `DAMAGED`, assesses a damage fee, and creates a repair requirement.
   - `CRITICAL` / `UNUSABLE`: Triggers disposal evaluation or heavy structural repair.
3. **Repair Prerequisites:**
   - A repair cannot be closed as `COMPLETED` without referencing an originating inspection (`REPAIR_WITHOUT_INSPECTION`).
   - Repaired assets must undergo post-repair inspection (`INSPECTION_PENDING`) before re-entering active fleet availability.
   - Repair costs cannot be negative.

---

## 6. Financial Ledger & Deposit Accounting Convention

1. **Signed Monetary Convention:**
   - `DEPOSIT_CHARGE`: Positive (+) liability collected from customer on dispatch.
   - `DEPOSIT_REFUND`: Negative (-) credit returned to customer upon verified good return.
   - `DAMAGE_CHARGE`: Positive (+) assessment billed or deducted from deposit for damage.
   - `LOSS_CHARGE`: Positive (+) assessment billed for lost/unreturned equipment.
2. **Refund Eligibility Constraint:**
   $$\text{Eligible Refund} \le \text{Total Deposits Charged} - \text{Total Prior Refunds} - \text{Total Damage Charges}$$
   Any refund request exceeding the eligible balance is rejected with an exception.
3. **Duplicate Refund Detection:**
   Duplicate refund transactions on the same return obligation or referencing the same RMA are flagged (`DUPLICATE_REFUND`).


## Repair clarifications — 2026-10-31

New assets are commissioned AVAILABLE. Dispatch requires AVAILABLE/RESERVED and the actual current origin. Delivery accepts an explicit receiving owner (custodian); legal ownership is unchanged. The legacy recipient default is the legal owner when none is supplied.

Live RMA creation requires IN_CUSTODY and records RETURN_REQUESTED without moving the asset. Receipt records RETURNED and a compound transition to INSPECTION_PENDING at the receiving facility. GOOD inspection makes AVAILABLE; DAMAGED/CRITICAL makes DAMAGED; UNUSABLE retires. Repair requires a matching originating inspection; completion requires UNDER_REPAIR and leads to INSPECTION_PENDING, not automatic availability.

Outstanding age is UTC calendar days from the latest dispatch in the still-active cycle. A return closes the cycle; later dispatch starts a new one. Checkpoints do not reset age. Missing dispatch yields age zero without invented history. Current snapshots consistently use REFERENCE_DATE; period activity filters do not rewrite current portfolio history.

Deposit liability = charges + signed refunds - damage - loss + adjustments. Repair charges are separately billed. Both per-asset and per-cycle negative balances are exceptions. Identical partial refund amounts are valid while an obligation remains. Exhausted-obligation repeat refunds are findings irrespective of reference spelling. Financial references are opaque idempotency keys, not anomaly markers.
