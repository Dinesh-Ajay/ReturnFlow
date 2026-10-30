import random
from app.generator.master_generator import MasterGenerator
from app.generator.transaction_generator import TransactionGenerator
from app.generator.anomaly_injector import AnomalyInjector
from app.utils.id_generator import IDGenerator
from app.generator.__main__ import logical_checksums

def test_fixed_seed_reproducibility():
    """
    Verifies that two independent generation runs with the fixed seed 20261022
    produce identically matching records, IDs, and anomaly labels.
    """
    seed = 20261022

    # Run 1
    rng1 = random.Random(seed)
    id_gen1 = IDGenerator(year=2026)
    m1 = MasterGenerator(rng1, id_gen1)
    types1 = m1.generate_asset_types(5)
    owners1 = m1.generate_owners(10)
    locs1 = m1.generate_locations(8)
    assets1 = m1.generate_assets(50, types1, owners1, locs1)
    
    tmap1 = {at["asset_type_id"]: at for at in types1}
    tx1 = TransactionGenerator(rng1, id_gen1)
    wf1 = tx1.generate_workflows(assets1, tmap1, owners1, locs1, num_shipments=25, target_custody_events=200)

    inj1 = AnomalyInjector(rng1, id_gen1)
    gt1 = inj1.inject_all_anomalies(
        wf1["assets"], wf1["custody_events"], wf1["deposit_ledger"], wf1["repairs"], locs1, owners1, count_per_scenario=2
    )

    # Run 2
    rng2 = random.Random(seed)
    id_gen2 = IDGenerator(year=2026)
    m2 = MasterGenerator(rng2, id_gen2)
    types2 = m2.generate_asset_types(5)
    owners2 = m2.generate_owners(10)
    locs2 = m2.generate_locations(8)
    assets2 = m2.generate_assets(50, types2, owners2, locs2)
    
    tmap2 = {at["asset_type_id"]: at for at in types2}
    tx2 = TransactionGenerator(rng2, id_gen2)
    wf2 = tx2.generate_workflows(assets2, tmap2, owners2, locs2, num_shipments=25, target_custody_events=200)

    inj2 = AnomalyInjector(rng2, id_gen2)
    gt2 = inj2.inject_all_anomalies(
        wf2["assets"], wf2["custody_events"], wf2["deposit_ledger"], wf2["repairs"], locs2, owners2, count_per_scenario=2
    )

    # Verifications
    assert len(assets1) == len(assets2) == 50
    assert len(wf1["custody_events"]) == len(wf2["custody_events"])
    assert len(gt1) == len(gt2) == 10

    # Verify identical primary keys
    for a1, a2 in zip(assets1, assets2):
        assert a1["asset_id"] == a2["asset_id"]
        assert a1["serial_number"] == a2["serial_number"]

    # Verify identical ground truth anomalies
    for g1, g2 in zip(gt1, gt2):
        assert g1["issue_id"] == g2["issue_id"]
        assert g1["issue_type"] == g2["issue_type"]
        assert g1["expected_decision"] == g2["expected_decision"]
        assert g1["record_id"] == g2["record_id"]

def test_logical_checksums_ignore_database_managed_timestamps():
    rows_a = {"assets": [{"asset_id": "ASSET-1", "value": 4, "created_at": "t1"}]}
    rows_b = {"assets": [{"asset_id": "ASSET-1", "value": 4, "created_at": "t2"}]}
    assert logical_checksums(rows_a, []) == logical_checksums(rows_b, [])
