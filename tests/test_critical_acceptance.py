"""Acceptance-focused probes beyond the historical regression suite."""
import concurrent.futures
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.config import settings
from app.models import ReusableAsset, CustodyEvent, DepositLedger, User, IDSequence
from app.services.asset_service import AssetService
from app.services.shipment_service import ShipmentService
from app.services.return_service import ReturnService
from app.services.inspection_service import InspectionService
from app.services.repair_service import RepairService
from app.services.lifecycle_service import LifecycleService, record_transition
from app.services.custody_service import CustodyService
from app.services.deposit_service import DepositService
from app.services.auth_service import AuthService
from app.validation.financial import FinancialValidator
from app.utils.id_generator import PersistentIDGenerator


def asset(db):
    result = AssetService.create_asset(db, dict(asset_type_id=1, owner_id=1,
        current_location_id=1, deposit_amount=50, purchase_date=date(2026, 1, 1)))
    return db.get(ReusableAsset, result['asset_id'])


def ledger(db, a, kind, amount, reference=None, related=None, when=None):
    row = DepositLedger(asset_id=a.asset_id, owner_id=1, transaction_type=kind,
        transaction_amount=Decimal(str(amount)), transaction_reference=reference or uuid4().hex,
        transaction_date=when or datetime(2026, 10, 1), related_ledger_id=related)
    db.add(row)
    db.flush()
    return row


def assert_projection(db, a):
    db.flush()
    result = CustodyService.rebuild_asset_projection_from_events(db, a.asset_id)
    assert result['history_complete'], result
    assert result['projected_status'] == a.asset_status
    assert result['projected_location_id'] == a.current_location_id
    assert result['projected_custodian_owner_id'] == a.current_custodian_owner_id
    assert result['projected_last_event_at'] == a.last_event_at.replace(tzinfo=None)


def test_full_live_lifecycle_replays_after_every_operation(db_session):
    db = db_session
    a = asset(db)
    assert_projection(db, a)
    t = datetime(2026, 10, 1)
    shipment = ShipmentService.create_shipment(db, 1, 2, 3, dispatch_date=t, asset_ids=[a.asset_id])
    assert_projection(db, a)
    ShipmentService.deliver_shipment(db, shipment.shipment_id, t + timedelta(days=1))
    assert_projection(db, a)
    rma = ReturnService.create_rma(db, 1, 1, 1, requested_date=t+timedelta(days=2), asset_ids=[a.asset_id])
    assert_projection(db, a)
    ReturnService.receive_return(db, rma.rma_id, t+timedelta(days=3))
    assert_projection(db, a)
    i = InspectionService.record_inspection(db, a.asset_id, 1, 'DAMAGED', inspection_date=t+timedelta(days=4))
    assert_projection(db, a)
    r = RepairService.initiate_repair(db, a.asset_id, 4, inspection_id=i.inspection_id, start_date=t+timedelta(days=5))
    assert_projection(db, a)
    RepairService.complete_repair(db, r.repair_id, Decimal('10'), completion_date=t+timedelta(days=6))
    assert_projection(db, a)
    InspectionService.record_inspection(db, a.asset_id, 1, 'GOOD', inspection_date=t+timedelta(days=7))
    assert_projection(db, a)
    record_transition(db, a, 'RETIRED', t+timedelta(days=8), 1)
    assert_projection(db, a)


def test_loss_nulls_and_recovery_replay(db_session):
    db = db_session
    a = asset(db)
    t = datetime(2026, 10, 1)
    ShipmentService.create_shipment(db, 1, 2, 3, dispatch_date=t, asset_ids=[a.asset_id])
    record_transition(db, a, 'LOST_REPORTED', t+timedelta(days=1), 3, physical=True)
    assert a.current_location_id is None and a.current_custodian_owner_id is None
    assert_projection(db, a)
    record_transition(db, a, 'RECOVERED', t+timedelta(days=2), 1, physical=True, location=1, custodian=1)
    assert_projection(db, a)


def test_service_failure_is_atomic_even_if_caller_catches(db_session):
    db = db_session
    a, b = asset(db), asset(db)
    b.asset_status = 'RETIRED'
    before = db.query(CustodyEvent).filter_by(asset_id=a.asset_id).count()
    with pytest.raises(ValueError):
        ShipmentService.create_shipment(db, 1, 2, 3, asset_ids=[a.asset_id, b.asset_id])
    db.flush()
    assert a.asset_status == 'AVAILABLE'
    assert db.query(CustodyEvent).filter_by(asset_id=a.asset_id).count() == before


def test_duplicate_delivery_rejected_without_extra_events(db_session):
    db = db_session
    a = asset(db)
    t = datetime(2026,10,1)
    s = ShipmentService.create_shipment(db, 1, 2, 3, dispatch_date=t, asset_ids=[a.asset_id])
    ShipmentService.deliver_shipment(db, s.shipment_id, t+timedelta(days=1))
    n = db.query(CustodyEvent).filter_by(asset_id=a.asset_id).count()
    with pytest.raises(ValueError):
        ShipmentService.deliver_shipment(db, s.shipment_id, t+timedelta(days=2))
    assert db.query(CustodyEvent).filter_by(asset_id=a.asset_id).count() == n


def test_outstanding_age_uses_dispatch_not_checkpoint(db_session):
    db = db_session
    a = asset(db)
    ShipmentService.create_shipment(db, 1, 2, 3, dispatch_date=datetime(2026,9,1), asset_ids=[a.asset_id])
    a.last_event_at = datetime(2026,10,20)  # projection's latest scan does not reset cycle age
    items, total = AssetService.list_assets(db, search=a.asset_id)
    detail = CustodyService.get_asset_full_traceability(db, a.asset_id)
    assert total == 1
    assert items[0]['days_outstanding'] == detail['days_outstanding'] == 51
    assert items[0]['is_overdue'] is True


def test_return_and_subsequent_dispatch_reset_age(db_session):
    db = db_session
    a = asset(db)
    t = datetime(2026,9,1)
    s = ShipmentService.create_shipment(db, 1, 2, 3, dispatch_date=t, asset_ids=[a.asset_id])
    ShipmentService.deliver_shipment(db, s.shipment_id, t+timedelta(days=1))
    r = ReturnService.create_rma(db, 1, 1, 1, requested_date=t+timedelta(days=2), asset_ids=[a.asset_id])
    ReturnService.receive_return(db, r.rma_id, t+timedelta(days=3))
    assert LifecycleService.standing_for_asset(db,a)['days_outstanding'] == 0
    InspectionService.record_inspection(db, a.asset_id, 1, 'GOOD', inspection_date=t+timedelta(days=4))
    ShipmentService.create_shipment(db, 1, 2, 3, dispatch_date=datetime(2026,10,20), asset_ids=[a.asset_id])
    assert LifecycleService.standing_for_asset(db,a)['days_outstanding'] == 2


def test_utc_outstanding_and_missing_dispatch():
    dispatch = datetime(2026,10,2,1,tzinfo=timezone(timedelta(hours=3)))
    assert LifecycleService.calculate_outstanding_days(dispatch, date(2026,10,2)) == 1
    assert LifecycleService.classify_asset_standing('IN_TRANSIT', None)['days_outstanding'] == 0


def test_overdue_filter_before_count_and_pagination(db_session):
    db = db_session
    a = asset(db)
    ShipmentService.create_shipment(db,1,2,3,dispatch_date=datetime(2026,8,1),asset_ids=[a.asset_id])
    results, count = AssetService.list_assets(db, search=a.asset_id, overdue_only=True, page_size=1)
    assert count == 1 and len(results) == 1
    results, count = AssetService.list_assets(db, search=a.asset_id, overdue_only=True, page_size=1, page=2)
    assert count == 1 and results == []
    results, count = AssetService.list_assets(db, search='no-such-asset-acceptance', overdue_only=True)
    assert count == 0 and results == []


@pytest.mark.parametrize('label,expected', [('At Location','AVAILABLE'),('In Transit','IN_TRANSIT'),('In Repair','UNDER_REPAIR')])
def test_visible_status_aliases(db_session,label,expected):
    rows, _ = AssetService.list_assets(db_session, search=label)
    assert all(r['asset_status'] == expected for r in rows)


def test_duplicate_refunds_survive_reference_renaming(db_session):
    db = db_session
    original = FinancialValidator.detect_duplicate_refunds(db)
    assert original
    old_ids = {r['ledger_id'] for r in original}
    for r in db.query(DepositLedger).filter(DepositLedger.ledger_id.in_(old_ids)):
        r.transaction_reference = uuid4().hex
    db.flush()
    renamed = FinancialValidator.detect_duplicate_refunds(db)
    assert {r['ledger_id'] for r in renamed} == old_ids


def test_equal_partial_refunds_not_duplicates(db_session):
    db = db_session
    a = asset(db)
    c = ledger(db,a,'DEPOSIT_CHARGE',100)
    ledger(db,a,'DEPOSIT_REFUND',-50,related=c.ledger_id)
    ledger(db,a,'DEPOSIT_REFUND',-50,related=c.ledger_id)
    audit = FinancialValidator.audit_obligations(db)
    assert not [r for r in audit['duplicate_refund_details'] if r['asset_id'] == a.asset_id]
    assert not [r for r in audit['over_refund_details'] if r['asset_id'] == a.asset_id]


def test_positive_portfolio_never_hides_negative_asset(db_session):
    db = db_session
    a,b = asset(db),asset(db)
    ledger(db,a,'DEPOSIT_CHARGE',1000)
    c=ledger(db,b,'DEPOSIT_CHARGE',10)
    ledger(db,b,'DEPOSIT_REFUND',-20,related=c.ledger_id)
    audit=FinancialValidator.audit_obligations(db)
    assert audit['net_liability'] > 0
    assert audit['portfolio_arithmetic_balanced']
    assert not audit['individual_obligations_valid']
    assert any(r['asset_id']==b.asset_id for r in audit['negative_asset_liabilities'])
    assert not audit['is_reconciled']


def test_invalid_original_and_cross_asset_refund(db_session):
    db=db_session
    a,b=asset(db),asset(db)
    c=ledger(db,a,'DEPOSIT_CHARGE',100)
    ledger(db,b,'DEPOSIT_REFUND',-10,related=c.ledger_id)
    audit=FinancialValidator.audit_obligations(db)
    assert any(r['asset_id']==b.asset_id for r in audit['invalid_refund_references'])


def test_refund_idempotency_and_cycle_limit(db_session):
    db=db_session
    a=asset(db)
    c=ledger(db,a,'DEPOSIT_CHARGE',100)
    ref=uuid4().hex
    r=DepositService.record_deposit_refund(db,a.asset_id,1,Decimal('60'),ref,related_ledger_id=c.ledger_id)
    retry=DepositService.record_deposit_refund(db,a.asset_id,1,Decimal('60'),ref,related_ledger_id=c.ledger_id)
    assert r.ledger_id == retry.ledger_id
    with pytest.raises(ValueError):
        DepositService.record_deposit_refund(db,a.asset_id,1,Decimal('60'),uuid4().hex,related_ledger_id=c.ledger_id)


@pytest.mark.parametrize('entity',['shipment','rma','inspection','repair'])
def test_cold_concurrent_sequences(db_engine,entity):
    factory=sessionmaker(bind=db_engine)
    # Unique sequence namespace guarantees first-allocation race is exercised.
    sequence='acceptance_'+entity+'_'+uuid4().hex
    def run(_):
        with factory() as db:
            value=PersistentIDGenerator.allocate_next_sequence_val(db,sequence,entity,year=2091)
            db.commit()
            return value
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        values=list(pool.map(run,range(8)))
    assert sorted(values)==list(range(1,9))


@pytest.mark.parametrize('header',[None,'Bearer invalid-token'])
def test_business_routes_require_valid_token(header):
    with TestClient(app) as client:
        headers={} if header is None else {'Authorization':header}
        assert client.get('/api/assets',headers=headers).status_code==401
        assert client.get('/api/exports/assets?format=csv',headers=headers).status_code==401
        assert client.post('/api/validation/run',headers=headers).status_code==401
        assert client.get('/health').status_code==200
        assert client.get('/docs').status_code==200


def test_expired_and_missing_exp_tokens_rejected(api_client):
    import jwt
    expired=AuthService.create_access_token({'sub':settings.INITIAL_ADMIN_EMAIL},timedelta(seconds=-1))
    assert api_client.get('/api/assets',headers={'Authorization':'Bearer '+expired}).status_code==401
    invalid=jwt.encode({'sub':settings.INITIAL_ADMIN_EMAIL},settings.AUTH_SECRET,algorithm='HS256')
    assert api_client.get('/api/assets',headers={'Authorization':'Bearer '+invalid}).status_code==401


def test_role_is_read_from_database_not_headers(db_engine):
    factory=sessionmaker(bind=db_engine)
    email=uuid4().hex+'@example.test'
    with factory() as db:
        user=User(full_name='Viewer Acceptance',email=email,role='Viewer',password_hash=AuthService.hash_password(uuid4().hex))
        db.add(user); db.commit()
    token=AuthService.create_access_token({'sub':email,'role':'Operations Manager'})
    try:
        with TestClient(app) as client:
            headers={'Authorization':'Bearer '+token,'X-User-Role':'Operations Manager'}
            assert client.get('/api/assets',headers=headers).status_code==200
            assert client.post('/api/deposits/refund',headers=headers,json={}).status_code==403
            assert client.post('/api/validation/run',headers=headers).status_code==403
    finally:
        with factory() as db:
            db.query(User).filter_by(email=email).delete(); db.commit()


def test_no_smtp_never_returns_otp(monkeypatch):
    from app.services.email_service import EmailService
    monkeypatch.setattr(settings,'SMTP_APP_PASSWORD','')
    success,message=EmailService.send_otp_email('nobody@example.test','Nobody','123456')
    assert not success and '123456' not in message


def test_admin_fallback_password_removed(db_session):
    # A configured bootstrap password is not an alternate password for an existing user.
    email=uuid4().hex+'@example.test'
    db_session.add(User(full_name='No fallback',email=email,role='Operations Manager',password_hash=AuthService.hash_password(uuid4().hex)))
    db_session.flush()
    assert AuthService.authenticate(db_session,email,'WrongPassword123!') is None


@pytest.mark.parametrize("kind", ["shipment", "rma", "inspection", "repair"])
def test_two_live_creations_per_entity_on_populated_db(db_session, kind):
    db=db_session
    made=[]
    for _ in range(2):
        a=asset(db)
        t=datetime(2026,10,1)
        if kind=="shipment":
            obj=ShipmentService.create_shipment(db,1,2,3,dispatch_date=t,asset_ids=[a.asset_id])
            made.append(obj.shipment_id)
        elif kind=="rma":
            a.asset_status="IN_CUSTODY"  # arrange independent fixture prerequisite
            obj=ReturnService.create_rma(db,1,1,1,requested_date=t,asset_ids=[a.asset_id])
            made.append(obj.rma_id)
        elif kind=="inspection":
            a.asset_status="INSPECTION_PENDING"
            obj=InspectionService.record_inspection(db,a.asset_id,1,"GOOD",inspection_date=t)
            made.append(obj.inspection_id)
        else:
            a.asset_status="INSPECTION_PENDING"
            i=InspectionService.record_inspection(db,a.asset_id,1,"DAMAGED",inspection_date=t)
            obj=RepairService.initiate_repair(db,a.asset_id,4,inspection_id=i.inspection_id,start_date=t)
            made.append(obj.repair_id)
    assert len(set(made))==2
    assert int(made[1].split("-")[-1]) > int(made[0].split("-")[-1])


def test_equal_timestamp_domain_events_are_deterministic(db_session):
    db=db_session
    a=asset(db)
    t=datetime(2026,10,1)
    s=ShipmentService.create_shipment(db,1,2,3,dispatch_date=t,asset_ids=[a.asset_id])
    ShipmentService.deliver_shipment(db,s.shipment_id,t)
    assert_projection(db,a)
    first=CustodyService.rebuild_asset_projection_from_events(db,a.asset_id)
    second=CustodyService.rebuild_asset_projection_from_events(db,a.asset_id)
    assert first==second


def test_orm_custody_events_are_append_only(db_session):
    db=db_session
    a=asset(db)
    row=db.query(CustodyEvent).filter_by(asset_id=a.asset_id).one()
    with pytest.raises(ValueError,match="append-only"):
        with db.begin_nested():
            row.notes="Attempted historical alteration"
            db.flush()


def test_two_separate_financial_cycles_are_not_duplicates(db_session):
    db=db_session
    a=asset(db)
    first=ledger(db,a,"DEPOSIT_CHARGE",50,when=datetime(2026,9,1))
    ledger(db,a,"DEPOSIT_REFUND",-50,related=first.ledger_id,when=datetime(2026,9,2))
    second=ledger(db,a,"DEPOSIT_CHARGE",50,when=datetime(2026,10,1))
    ledger(db,a,"DEPOSIT_REFUND",-50,related=second.ledger_id,when=datetime(2026,10,2))
    audit=FinancialValidator.audit_obligations(db,asset_id=a.asset_id)
    assert audit["is_reconciled"]
    assert audit["duplicate_refund_findings"]==0


@pytest.mark.parametrize("deduction",["DAMAGE_CHARGE","LOSS_CHARGE"])
def test_deductions_reduce_refundable_obligation(db_session,deduction):
    db=db_session
    a=asset(db)
    c=ledger(db,a,"DEPOSIT_CHARGE",100)
    ledger(db,a,deduction,35,related=c.ledger_id)
    ledger(db,a,"DEPOSIT_REFUND",-65,related=c.ledger_id)
    audit=FinancialValidator.audit_obligations(db,asset_id=a.asset_id)
    assert audit["is_reconciled"] and audit["net_liability"]==0


def test_database_enforces_unique_financial_reference(db_session):
    from sqlalchemy.exc import IntegrityError
    db=db_session
    a=asset(db)
    ref=uuid4().hex
    ledger(db,a,"DEPOSIT_CHARGE",100,reference=ref)
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            ledger(db,a,"DEPOSIT_CHARGE",100,reference=ref)


def test_api_age_matches_list_detail_and_overdue(api_client):
    response=api_client.get("/api/assets?status=IN_CUSTODY&page_size=1")
    row=response.json()["items"][0]
    detail=api_client.get("/api/assets/"+row["asset_id"]).json()
    status=api_client.get("/api/assets/"+row["asset_id"]+"/status").json()
    assert row["days_outstanding"]==detail["days_outstanding"]==status["days_outstanding"]
    assert row["is_overdue"]==detail["is_overdue"]==status["is_overdue"]


def test_expired_reset_session_is_rejected(db_session):
    from app.models.user import PasswordResetOTP
    email=uuid4().hex+"@example.test"
    token=uuid4().hex
    db_session.add(PasswordResetOTP(email=email,otp_hash="unused",reset_token=token,is_used=True,
        expires_at=datetime.now(timezone.utc)-timedelta(minutes=1)))
    db_session.flush()
    ok,msg=AuthService.reset_password(db_session,email,token,uuid4().hex)
    assert not ok and "expired" in msg.lower()


def test_configured_bootstrap_password_is_not_login_backdoor(db_session):
    user=db_session.query(User).filter_by(email=settings.INITIAL_ADMIN_EMAIL).one()
    user.password_hash=AuthService.hash_password(uuid4().hex)
    db_session.flush()
    assert AuthService.authenticate(db_session,user.email,settings.INITIAL_ADMIN_PASSWORD) is None



def test_delivery_uses_explicit_recipient_and_preserves_legal_owner(db_session):
    db=db_session
    a=asset(db)
    t=datetime(2026,10,1)
    s=ShipmentService.create_shipment(db,1,2,3,dispatch_date=t,asset_ids=[a.asset_id])
    ShipmentService.deliver_shipment(db,s.shipment_id,t+timedelta(days=1),receiving_owner_id=2)
    assert a.owner_id==1 and a.current_custodian_owner_id==2
    assert_projection(db,a)


def test_dispatch_origin_must_match_projection(db_session):
    db=db_session
    a=asset(db)
    with pytest.raises(ValueError,match="origin"):
        ShipmentService.create_shipment(db,2,1,3,asset_ids=[a.asset_id])
    assert a.asset_status=="AVAILABLE"


def test_custody_workflow_bypass_rejected(api_client):
    response=api_client.post("/api/custody-events",json={"asset_id":"ASSET-0000001",
        "event_type":"INSPECTED_GOOD","event_timestamp":"2026-10-31T12:00:00Z","actor_owner_id":1})
    assert response.status_code==400
