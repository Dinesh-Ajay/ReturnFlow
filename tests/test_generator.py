import random
from app.generator.master_generator import MasterGenerator
from app.generator.transaction_generator import TransactionGenerator
from app.utils.id_generator import IDGenerator
from app.generator.config import PROFILES

def test_deterministic_id_generator():
    gen1 = IDGenerator(year=2026)
    assert gen1.next_asset_id() == "ASSET-0000001"
    assert gen1.next_asset_id() == "ASSET-0000002"
    assert gen1.next_shipment_id() == "SHP-2026-000001"
    assert gen1.next_rma_id() == "RMA-2026-000001"
    assert gen1.next_custody_event_id("ASSET-0000001") == "CUST-ASSET-0000001-000001"
    assert gen1.next_custody_event_id("ASSET-0000001") == "CUST-ASSET-0000001-000002"

def test_starter_profile_generation():
    seed = 20261022
    rng = random.Random(seed)
    id_gen = IDGenerator(year=2026)
    p_conf = PROFILES["starter"]

    m_gen = MasterGenerator(rng, id_gen)
    asset_types = m_gen.generate_asset_types(p_conf["num_asset_types"])
    owners = m_gen.generate_owners(p_conf["num_owners"])
    locations = m_gen.generate_locations(p_conf["num_locations"])
    assets = m_gen.generate_assets(p_conf["num_assets"], asset_types, owners, locations)

    assert len(asset_types) == 5
    assert len(owners) == 15
    assert len(locations) == 12
    assert len(assets) == 200

    asset_types_map = {at["asset_type_id"]: at for at in asset_types}
    tx_gen = TransactionGenerator(rng, id_gen)
    wf = tx_gen.generate_workflows(
        assets=assets,
        asset_types_map=asset_types_map,
        owners=owners,
        locations=locations,
        num_shipments=p_conf["num_shipments"],
        target_custody_events=p_conf["target_custody_events"]
    )

    assert len(wf["shipments"]) >= 100
    assert len(wf["custody_events"]) >= 1000
    assert len(wf["return_authorizations"]) > 0
    assert len(wf["inspections"]) > 0
    assert len(wf["deposit_ledger"]) > 0
