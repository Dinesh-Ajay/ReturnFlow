import random
from datetime import date, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from app.utils.id_generator import IDGenerator

class MasterGenerator:
    """
    Generates deterministic master data:
    1. AssetTypes
    2. Owners
    3. Locations
    4. ReusableAssets
    """

    ASSET_TYPE_DEFINITIONS = [
        {"type_code": "PALLET", "type_name": "Standard Wooden Pallet", "deposit": Decimal("50.00"), "lifecycle": 730, "return_due": 30, "loss_threshold": 60, "requires_inspection": True, "repairable": True},
        {"type_code": "CONTAINER", "type_name": "Heavy-Duty Plastic Bulk Container", "deposit": Decimal("250.00"), "lifecycle": 1095, "return_due": 45, "loss_threshold": 90, "requires_inspection": True, "repairable": True},
        {"type_code": "CRATE", "type_name": "Collapsible Transport Crate", "deposit": Decimal("75.00"), "lifecycle": 540, "return_due": 30, "loss_threshold": 60, "requires_inspection": True, "repairable": True},
        {"type_code": "RACK", "type_name": "Industrial Steel Stacking Rack", "deposit": Decimal("500.00"), "lifecycle": 1825, "return_due": 60, "loss_threshold": 120, "requires_inspection": True, "repairable": True},
        {"type_code": "TOTE", "type_name": "Automated Storage Tote", "deposit": Decimal("40.00"), "lifecycle": 365, "return_due": 21, "loss_threshold": 45, "requires_inspection": False, "repairable": False},
        {"type_code": "METAL_PALLET", "type_name": "Galvanized Metal Pallet", "deposit": Decimal("180.00"), "lifecycle": 1460, "return_due": 45, "loss_threshold": 90, "requires_inspection": True, "repairable": True},
        {"type_code": "THERMAL_BOX", "type_name": "Insulated Cold-Chain Box", "deposit": Decimal("120.00"), "lifecycle": 365, "return_due": 14, "loss_threshold": 30, "requires_inspection": True, "repairable": True},
        {"type_code": "DRUM", "type_name": "Reusable Stainless Steel Drum", "deposit": Decimal("350.00"), "lifecycle": 1825, "return_due": 60, "loss_threshold": 120, "requires_inspection": True, "repairable": True},
    ]

    OWNER_TEMPLATES = [
        ("Acme Packaging Corp", "SUPPLIER", "contact@acmepackaging.fake", "212-555-0101"),
        ("FreshMart Retail Inc", "CUSTOMER", "logistics@freshmart.fake", "312-555-0102"),
        ("Global Logistics Express", "CARRIER", "dispatch@globallogistics.fake", "415-555-0103"),
        ("Apex Freight Systems", "CARRIER", "freight@apexfreight.fake", "206-555-0104"),
        ("Inland Warehouse Operations", "WAREHOUSE_OPERATOR", "operations@inlandwh.fake", "713-555-0105"),
        ("ReturnFlow Internal Operations", "INTERNAL_OPERATIONS", "admin@returnflow.fake", "800-555-0106"),
        ("RetailCo Department Stores", "CUSTOMER", "inventory@retailco.fake", "214-555-0107"),
        ("Pinnacle Food Supplies", "CUSTOMER", "supply@pinnaclefood.fake", "404-555-0108"),
        ("Pacific Cold Storage", "WAREHOUSE_OPERATOR", "cold@pacificstorage.fake", "619-555-0109"),
        ("SpeedShip Transit Inc", "CARRIER", "shipping@speedship.fake", "305-555-0110"),
        ("Midwest Distribution Center", "WAREHOUSE_OPERATOR", "ops@midwestdc.fake", "317-555-0111"),
        ("BioPharma Supply Logistics", "CUSTOMER", "pharma@biopharmasupply.fake", "617-555-0112"),
    ]

    LOCATION_TEMPLATES = [
        ("New York DC", "DISTRIBUTION_CENTER", "New York", "NY"),
        ("Chicago WH", "WAREHOUSE", "Chicago", "IL"),
        ("Los Angeles DC", "DISTRIBUTION_CENTER", "Los Angeles", "CA"),
        ("Dallas Repair Center", "REPAIR_CENTER", "Dallas", "TX"),
        ("Atlanta WH", "WAREHOUSE", "Atlanta", "GA"),
        ("Seattle DC", "DISTRIBUTION_CENTER", "Seattle", "WA"),
        ("Boston WH", "WAREHOUSE", "Boston", "MA"),
        ("Denver DC", "DISTRIBUTION_CENTER", "Denver", "CO"),
        ("Miami WH", "WAREHOUSE", "Miami", "FL"),
        ("Houston DC", "DISTRIBUTION_CENTER", "Houston", "TX"),
        ("Acme Supplier Site", "SUPPLIER", "Newark", "NJ"),
        ("FreshMart Store #101", "CUSTOMER_SITE", "Irvine", "CA"),
        ("RetailCo Store #44", "CUSTOMER_SITE", "Fort Worth", "TX"),
        ("Central Transit Hub", "TRANSIT_HUB", "Kansas City", "MO"),
    ]

    def __init__(self, rng: random.Random, id_gen: IDGenerator):
        self.rng = rng
        self.id_gen = id_gen

    def generate_asset_types(self, count: int) -> List[Dict[str, Any]]:
        types = []
        take = min(count, len(self.ASSET_TYPE_DEFINITIONS))
        for i in range(take):
            defn = self.ASSET_TYPE_DEFINITIONS[i]
            types.append({
                "asset_type_id": i + 1,
                "type_code": defn["type_code"],
                "type_name": defn["type_name"],
                "description": f"Standard enterprise specification for {defn['type_name']}",
                "default_deposit_amount": defn["deposit"],
                "expected_lifecycle_days": defn["lifecycle"],
                "return_due_days": defn["return_due"],
                "loss_threshold_days": defn["loss_threshold"],
                "requires_inspection": defn["requires_inspection"],
                "repairable": defn["repairable"],
                "active": True
            })
        return types

    def generate_owners(self, count: int) -> List[Dict[str, Any]]:
        owners = []
        for i in range(count):
            tpl_idx = i % len(self.OWNER_TEMPLATES)
            name, otype, email, phone = self.OWNER_TEMPLATES[tpl_idx]
            suffix = f" #{i // len(self.OWNER_TEMPLATES) + 1}" if i >= len(self.OWNER_TEMPLATES) else ""
            owners.append({
                "owner_id": i + 1,
                "owner_code": f"OWN-{i+1:03d}",
                "owner_name": f"{name}{suffix}",
                "owner_type": otype,
                "contact_email": email.replace("@", f"{i+1}@"),
                "contact_phone": phone,
                "active": True
            })
        return owners

    def generate_locations(self, count: int) -> List[Dict[str, Any]]:
        locations = []
        for i in range(count):
            tpl_idx = i % len(self.LOCATION_TEMPLATES)
            name, ltype, city, state = self.LOCATION_TEMPLATES[tpl_idx]
            suffix = f" Branch {i // len(self.LOCATION_TEMPLATES) + 1}" if i >= len(self.LOCATION_TEMPLATES) else ""
            locations.append({
                "location_id": i + 1,
                "location_code": f"LOC-{i+1:03d}",
                "location_name": f"{name}{suffix}",
                "location_type": ltype,
                "city": city,
                "state": state,
                "country": "USA",
                "active": True
            })
        return locations

    def generate_assets(
        self,
        count: int,
        asset_types: List[Dict[str, Any]],
        owners: List[Dict[str, Any]],
        locations: List[Dict[str, Any]],
        base_date: date = date(2026, 1, 15)
    ) -> List[Dict[str, Any]]:
        assets = []
        primary_owner_ids = [o["owner_id"] for o in owners if o["owner_type"] in ("SUPPLIER", "INTERNAL_OPERATIONS")]
        if not primary_owner_ids:
            primary_owner_ids = [o["owner_id"] for o in owners]

        loc_ids = [l["location_id"] for l in locations]

        for i in range(1, count + 1):
            asset_id = self.id_gen.next_asset_id()
            atype = self.rng.choice(asset_types)
            owner_id = self.rng.choice(primary_owner_ids)
            init_loc = self.rng.choice(loc_ids)

            # Dates
            mfg_days_ago = self.rng.randint(90, 700)
            mfg_date = base_date - timedelta(days=mfg_days_ago)
            purchase_date = mfg_date + timedelta(days=self.rng.randint(5, 30))

            deposit = atype["default_deposit_amount"]
            acq_cost = deposit * Decimal(str(self.rng.uniform(1.8, 3.2))).quantize(Decimal("0.01"))

            assets.append({
                "asset_id": asset_id,
                "asset_type_id": atype["asset_type_id"],
                "owner_id": owner_id,
                "serial_number": f"SN-{atype['type_code']}-{i:07d}",
                "asset_status": "AVAILABLE",
                "manufacture_date": mfg_date,
                "purchase_date": purchase_date,
                "current_location_id": init_loc,
                "current_custodian_owner_id": owner_id,
                "acquisition_cost": acq_cost,
                "deposit_amount": deposit,
                "last_event_at": None,
            })

        return assets
