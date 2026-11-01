# Commands and evidence

All database commands used disposable local MariaDB databases owned by this repair session. Connection secrets are deliberately omitted; set DATABASE_URL / TEST_DATABASE_URL using your own credentials. The owner's working database was never accessible.

## Repository and checkpoint

`git clone https://github.com/Dinesh-Ajay/ReturnFlow.git`
`git status --short --branch`
`git log -1 --format='%H %s'`
`git diff --stat`
`git diff --cached --stat`
`git diff b414005..HEAD --stat`
`git bundle create <external-checkpoint>/original.bundle --all`
`tar --exclude=.git -czf <external-checkpoint>/original.tar.gz .`

The clone was clean master at ef3b0696840d8e2e875be8bb72d5285d140ee033. Staged/unstaged/untracked lists were initially empty. This does not establish the owner's unpublished local Git state.

## Baseline and focused tests

`python -m pytest -v` -> baseline_pytest.log: 73 passed, 1 failed.
`python -m pytest tests/test_persistent_id_generation.py -v` -> phase2_ids.log: 8 passed.
`python -m pytest tests/test_persistent_id_generation.py tests/test_lifecycle_custody_enforcement.py -v` -> phase3_lifecycle.log: 16 passed.
`python -m pytest tests/test_financial.py tests/test_anomalies.py -v` -> phase6_7_finance.log: 9 passed, 1 obsolete assertion failed (seed incorrectly expected RECONCILED); corrected with stronger assertions.
`python -m pytest tests/test_critical_acceptance.py -v` -> initial 26 passed; expanded run uncovered naive/aware comparison and it was corrected.

## Blank install and data load

`python -m alembic upgrade head` -> clean_install_final.log.
`python -m app.generator --profile full --seed 20261022` -> clean_full_load.log, targeting empty returnflow_regression_test with all generated/export/ground-truth paths isolated outside the source checkout. Full load: 16.622 s, not a repeated benchmark.

First schema+raw-seed probes failed on missing server defaults for timestamps and anomaly status. Frozen migration defaults were corrected before successful blank install. Raw committed seed also loaded successfully into returnflow_audit_test after omitting USE and FOREIGN_KEY_CHECKS lines, leaving constraints enabled. No main database migration/load was executed.

## Final regression

`python -m pytest -v` with TEST_DATABASE_URL=disposable returnflow_regression_test and RETURN_FLOW_TEST_GROUND_TRUTH_DIR=matching fresh ground-truth directory -> final_pytest.log: 116 passed, one Starlette/httpx dependency warning.

`python -m pytest -v` with TEST_DATABASE_URL=disposable preserved-seed returnflow_test and paired committed ground truth -> final_preserved_pytest.log: 116 passed, one warning.

A first fresh-load regression used the wrong historic label directory: 112 passed, 1 failed, precision 40%. The complete failed log was overwritten during the final rerun; that earlier result is recorded here and in the report, not represented as a preserved full transcript. The version comparison documents the underlying discrepancy. Detectors did not read labels; evaluation paths were corrected to select the matching dataset version.

## Actual project commands

`python -m app.validation.counts` -> counts.log.
`python -m app.validation` -> validation.log and validation_summary.json. This command updates anomaly detection metadata in the disposable database; it is NOT fully read-only.
`python -m app.validation.acceptance_audit` -> acceptance_audit evidence JSON (read-only).
`python -m app.validation.reproducibility --profile full --seed 20261022` -> reproducibility.log/results JSON (two isolated in-memory generation passes).
`python -m app.generator --profile full --seed 20261022 --no-db` -> generation.log; all output paths isolated from committed data.
`python -m app.validation.benchmark` -> benchmark.log/performance_results.json (one warm-up, three timed DB runs).
`python -m app.generator.manifest` -> data/source_manifest.json (hash manifest, not dataset replacement).

All report-generating validation commands used RETURNFLOW_EXPORTS_DIR pointing at a dedicated evidence directory, so the owner's supplied/committed reports were not silently overwritten.

## Browser

Headless Playwright Chromium ran against the protected local portal backed by a disposable database. Login credentials and tokens are not included in evidence. See browser_acceptance.json: category population (all eight), status/category pagination reset, aliases, bearer fetch and export passed; no page errors. Screenshot is a test artifact, not an interface redesign.

## Final Git checks

`git status --short`
`git diff --stat`
`git diff --check`
Tracked data preservation checked separately. No commit, push or staging was performed. Recovery checkpoints remain outside the delivered source archive; pre-existing tracked .audit_checkpoint files remain untouched in the checkout but are omitted from delivery archives.
