# Repair reproducibility update — 2026-10-31

Full profile, seed 20261022: both generation passes matched counts and logical SHA-256 digests. Evidence/reproducibility_results.json records the current Python/Linux environment and all digests. Counts remain unchanged.

The preserved committed artifact set is NOT asserted identical to a fresh generator run. A clean-load regression initially paired fresh data with the old committed labels and produced 40% precision; pairing it with its own generated independent labels resolved the mismatch and the full suite passed. No detector was given those labels as input and no committed dataset was altered to make tests pass.

For a fresh generated test database, point RETURN_FLOW_TEST_GROUND_TRUTH_DIR to the matching generated ground-truth directory. For the preserved seed, use its committed paired labels. The source manifest records file-level hashes and unknown historical producer commit. Fresh export manifests include current generator source hashes.

## Earlier reproducibility report

# Reproducibility Report

Verification executed on 2026-10-30 with Python 3.13.9, full profile, and seed **20261022**.

## Commands

```powershell
python -m app.validation.reproducibility --profile full --seed 20261022
```

This runs two in-memory generation passes. It does not connect to or clear the database and does not overwrite generated CSVs. Counts and SHA-256 digests are saved in `data/exports/reproducibility_results.json`.

To generate one full dataset and export it to the configured destinations:

```powershell
python -m app.generator --profile full --seed 20261022 --no-db
```

To load data into MySQL, first configure `DATABASE_URL` to a dedicated empty database. The loader refuses populated target tables by default. `--replace-existing` permits dependency-ordered transactional deletion only in a disposable test database after backup; do not point that command at data that needs to be preserved.

## Result

Both full in-memory passes produced identical counts and checksums: **reproducible = true**. Each produced 8 asset types, 40 owners, 30 locations, 20,000 assets, 10,000 shipments, 20,000 shipment-asset links, 100,030 custody events, 12,400 return authorizations, 12,400 RMA-asset links, 12,400 inspections, 1,348 repairs, 34,148 ledger entries, and 50 ground-truth anomaly labels.

Logical row serialization uses sorted JSON keys and excludes `created_at` / `updated_at` database-managed metadata. Dates and timestamps are normalized to ISO strings; `Decimal` values are serialized as decimal strings. The generator sorts the unique asset IDs before applying the seeded shuffle in anomaly injection, preventing process hash randomization from changing scenario targets.

| Entity | SHA-256 (both passes) |
| --- | --- |
| Asset types | `21f41215a0bba72be4b48ac6c11eb5ad534e195483e904afde6b6eb165bdb77f` |
| Owners | `4b983ee18c0b0c589237ef0c86b346d0a2a4d685cb7bff30b65811cf411ab76a` |
| Locations | `ea9d7e07634c181f44e146e6332e768864313ebab502217af91f629af4ba26d4` |
| Assets | `5599d56af4a0b43dfcf7423fec5eb17dd493223d9bda8968609eeeab489d47c6` |
| Shipments | `27c1ea4a608de65780ef875eb853bb672226d86eb72ee57fb3a752e6553b91d9` |
| Shipment-asset links | `f1503e5ba3ed015b06ba9614ad9f890f464ce7706a5e691f4e084c1c28d1e295` |
| Custody events | `a4e8ee27d97c8bdab3466f90930300edb516c300b194d18931d22211c6a2558e` |
| Return authorizations | `f1c987ea6e4106b3765d6ab4fbe6c7bdd922d911198590fcb1c7dba8ec231e47` |
| RMA-asset links | `3ef7f1cf3dba03812b7b6432bc75d5c073d1e1f316303bf1743b9fdea1c805b6` |
| Inspections | `7bd104365a8f72e751b4de580a13fbfc26422fdf260d99131686a7fbef82d5e3` |
| Repairs | `8260f53e2ba64a99925c3dc03bbab7e6b1c0969242fc543b05a36f7334799b57` |
| Deposit ledger | `f92c8f356ffd8d5d2f469c8dab9523b2ebcee00fa9b2c6061cc581f2a551faf6` |
| Ground truth | `e18215a4039078ad584e5667bd3d339ad8376c524d862f44efb5c3e1d5407bf7` |

This verification proves repeatability for the current full-profile generator and configuration. It does not prove that a prior database loaded by an older generator revision has identical logical rows.
