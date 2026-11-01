"""Read-only replay of immutable custody facts plus legacy inspection/repair facts.

Never synthesizes a missing custody event or reads the stored projection to
choose replay results. Incomplete historical information is explicitly reported.
"""
from collections import defaultdict
from app.models.custody_event import CustodyEvent
from app.models.inspection import Inspection
from app.models.repair import Repair
from app.services.lifecycle_service import utc_naive


def replay(asset_id, events, inspections=(), repairs=()):
    timeline = []
    references = {e.event_reference for e in events}
    for e in events:
        timeline.append((utc_naive(e.event_timestamp), 10, e.custody_event_id, 'event', e))
    for i in inspections:
        if i.inspection_id not in references:
            timeline.append((utc_naive(i.inspection_date), 20, i.inspection_id, 'inspection', i))
    for r in repairs:
        if not any(e.event_type == 'REPAIR_STARTED' and e.event_reference == r.repair_id for e in events):
            timeline.append((utc_naive(r.repair_start_date), 30, r.repair_id, 'repair_start', r))
        if r.repair_completion_date and not any(e.event_type == 'REPAIR_COMPLETED' and e.event_reference == r.repair_id for e in events):
            timeline.append((utc_naive(r.repair_completion_date), 40, r.repair_id, 'repair_end', r))
    timeline.sort(key=lambda x: x[:3])
    status, location, custodian, last, last_id = None, None, None, None, None
    reasons = []
    mapping = {'COMMISSIONED': 'AVAILABLE', 'DISPATCHED': 'IN_TRANSIT',
               'PICKED_UP': 'IN_TRANSIT', 'IN_TRANSIT': 'IN_TRANSIT',
               'RECEIVED': 'IN_CUSTODY', 'TRANSFERRED': 'IN_CUSTODY',
               'RETURN_REQUESTED': 'RETURN_PENDING', 'RETURNED': 'INSPECTION_PENDING',
               'INSPECTED_GOOD': 'AVAILABLE', 'INSPECTED_DAMAGED': 'DAMAGED',
               'INSPECTED_UNUSABLE': 'RETIRED', 'REPAIR_STARTED': 'UNDER_REPAIR',
               'REPAIR_COMPLETED': 'INSPECTION_PENDING', 'LOST_REPORTED': 'LOST',
               'RETIRED': 'RETIRED', 'RECOVERED': 'INSPECTION_PENDING'}
    nonphysical = {'RETURN_REQUESTED', 'INSPECTED_GOOD', 'INSPECTED_DAMAGED',
                   'INSPECTED_UNUSABLE', 'REPAIR_COMPLETED', 'RETIRED'}
    for when, _, identifier, kind, row in timeline:
        last, last_id = when, identifier
        if kind == 'event':
            t = row.event_type
            if t not in mapping:
                reasons.append(f'Unknown event type {t}: {identifier}')
                continue
            if t == 'IN_TRANSIT' and status not in (None, 'IN_TRANSIT', 'DISPATCHED', 'RETURN_PENDING'):
                reasons.append(f'Transit scan after completed movement: {identifier}')
            status = mapping[t]
            if t not in nonphysical:
                if t in ('DISPATCHED', 'IN_TRANSIT', 'PICKED_UP'):
                    location, custodian = None, row.to_owner_id
                elif t == 'LOST_REPORTED':
                    location, custodian = None, None
                else:
                    location, custodian = row.to_location_id, row.to_owner_id
        elif kind == 'inspection':
            status = {'GOOD': 'AVAILABLE', 'UNUSABLE': 'RETIRED', 'DAMAGED': 'DAMAGED', 'CRITICAL': 'DAMAGED'}.get(row.condition_status)
            if status is None:
                reasons.append(f'Unknown inspection outcome: {identifier}')
        elif kind == 'repair_start':
            status, location = 'UNDER_REPAIR', row.repair_location_id
            reasons.append(f'Legacy repair lacks custody transfer event: {identifier}')
        elif kind == 'repair_end':
            status = 'INSPECTION_PENDING'
            reasons.append(f'Legacy repair completion lacks post-repair inspection/movement evidence: {identifier}')
    if not timeline:
        reasons.append('No authoritative history; projection cannot be reconstructed')
    return {'asset_id': asset_id, 'projected_status': status,
            'projected_location_id': location, 'projected_custodian_owner_id': custodian,
            'projected_last_event_at': last, 'last_relevant_record': last_id,
            'history_complete': not reasons, 'history_exceptions': reasons}


def bulk_replay(db):
    events, inspections, repairs = defaultdict(list), defaultdict(list), defaultdict(list)
    for model, grouped in ((CustodyEvent, events), (Inspection, inspections), (Repair, repairs)):
        for row in db.query(model).yield_per(2000):
            grouped[row.asset_id].append(row)
    from app.models.asset import ReusableAsset
    for a in db.query(ReusableAsset).yield_per(2000):
        result = replay(a.asset_id, events[a.asset_id], inspections[a.asset_id], repairs[a.asset_id])
        expected = {'status': a.asset_status, 'location_id': a.current_location_id,
                    'custodian_owner_id': a.current_custodian_owner_id,
                    'last_event_at': utc_naive(a.last_event_at)}
        mismatches = {key: {'stored': value, 'replayed': result['projected_' + key]}
                      for key,value in expected.items() if value != result['projected_' + key]}
        yield {**result, 'mismatches': mismatches}
