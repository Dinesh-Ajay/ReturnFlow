"""Install complete frozen schema; repair historical no-op initial revision.

Existing tables are preserved. Back up and review schema differences before
applying to an existing database. No data is deleted by upgrade.
"""
from alembic import op
import sqlalchemy as sa
revision = "0026_complete_schema"
down_revision = "0025d1f7dd16"
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if 'anomaly_records' not in existing:
        op.create_table('anomaly_records',
        sa.Column('issue_id', sa.String(length=64), nullable=False),
        sa.Column('affected_asset_id', sa.String(length=32), nullable=True),
        sa.Column('affected_record_id', sa.String(length=64), nullable=False),
        sa.Column('entity_name', sa.String(length=64), nullable=False),
        sa.Column('issue_type', sa.String(length=64), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('ground_truth_label', sa.String(length=64), nullable=True),
        sa.Column('expected_decision', sa.String(length=64), nullable=False),
        sa.Column('detected_decision', sa.String(length=64), nullable=True),
        sa.Column('detection_status', sa.String(length=32), server_default=sa.text("'OPEN'"), nullable=False),
        sa.Column('is_injected', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('issue_id')
        )
    if 'ix_anomaly_records_affected_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_affected_asset_id'), 'anomaly_records', ['affected_asset_id'], unique=False)
    if 'ix_anomaly_records_affected_record_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_affected_record_id'), 'anomaly_records', ['affected_record_id'], unique=False)
    if 'ix_anomaly_records_detection_status' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_detection_status'), 'anomaly_records', ['detection_status'], unique=False)
    if 'ix_anomaly_records_entity_name' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_entity_name'), 'anomaly_records', ['entity_name'], unique=False)
    if 'ix_anomaly_records_ground_truth_label' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_ground_truth_label'), 'anomaly_records', ['ground_truth_label'], unique=False)
    if 'ix_anomaly_records_issue_type' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_issue_type'), 'anomaly_records', ['issue_type'], unique=False)
    if 'ix_anomaly_records_severity' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('anomaly_records')}:
        op.create_index(op.f('ix_anomaly_records_severity'), 'anomaly_records', ['severity'], unique=False)
    if 'asset_types' not in existing:
        op.create_table('asset_types',
        sa.Column('asset_type_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type_code', sa.String(length=32), nullable=False),
        sa.Column('type_name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('default_deposit_amount', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('expected_lifecycle_days', sa.Integer(), server_default=sa.text('365'), nullable=False),
        sa.Column('return_due_days', sa.Integer(), server_default=sa.text('30'), nullable=False),
        sa.Column('loss_threshold_days', sa.Integer(), server_default=sa.text('60'), nullable=False),
        sa.Column('requires_inspection', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('repairable', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('asset_type_id')
        )
    if 'ix_asset_types_type_code' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('asset_types')}:
        op.create_index(op.f('ix_asset_types_type_code'), 'asset_types', ['type_code'], unique=True)
    if 'id_sequences' not in existing:
        op.create_table('id_sequences',
        sa.Column('sequence_name', sa.String(length=64), nullable=False),
        sa.Column('current_value', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('sequence_name')
        )
    if 'ix_id_sequences_sequence_name' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('id_sequences')}:
        op.create_index(op.f('ix_id_sequences_sequence_name'), 'id_sequences', ['sequence_name'], unique=False)
    if 'locations' not in existing:
        op.create_table('locations',
        sa.Column('location_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('location_code', sa.String(length=32), nullable=False),
        sa.Column('location_name', sa.String(length=150), nullable=False),
        sa.Column('location_type', sa.String(length=50), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), server_default=sa.text("'USA'"), nullable=False),
        sa.Column('active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('location_id')
        )
    if 'ix_locations_location_code' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('locations')}:
        op.create_index(op.f('ix_locations_location_code'), 'locations', ['location_code'], unique=True)
    if 'ix_locations_location_type' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('locations')}:
        op.create_index(op.f('ix_locations_location_type'), 'locations', ['location_type'], unique=False)
    if 'owners' not in existing:
        op.create_table('owners',
        sa.Column('owner_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('owner_code', sa.String(length=32), nullable=False),
        sa.Column('owner_name', sa.String(length=150), nullable=False),
        sa.Column('owner_type', sa.String(length=50), nullable=False),
        sa.Column('contact_email', sa.String(length=150), nullable=True),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('owner_id')
        )
    if 'ix_owners_owner_code' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('owners')}:
        op.create_index(op.f('ix_owners_owner_code'), 'owners', ['owner_code'], unique=True)
    if 'ix_owners_owner_type' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('owners')}:
        op.create_index(op.f('ix_owners_owner_type'), 'owners', ['owner_type'], unique=False)
    if 'password_reset_otps' not in existing:
        op.create_table('password_reset_otps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('otp_hash', sa.String(length=255), nullable=False),
        sa.Column('reset_token', sa.String(length=255), nullable=True),
        sa.Column('attempts', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_used', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
    if 'ix_password_reset_otps_email' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('password_reset_otps')}:
        op.create_index(op.f('ix_password_reset_otps_email'), 'password_reset_otps', ['email'], unique=False)
    if 'ix_password_reset_otps_reset_token' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('password_reset_otps')}:
        op.create_index(op.f('ix_password_reset_otps_reset_token'), 'password_reset_otps', ['reset_token'], unique=False)
    if 'users' not in existing:
        op.create_table('users',
        sa.Column('user_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('role', sa.String(length=50), server_default=sa.text("'Operations Manager'"), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('user_id')
        )
    if 'ix_users_email' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('users')}:
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    if 'return_authorizations' not in existing:
        op.create_table('return_authorizations',
        sa.Column('rma_id', sa.String(length=32), nullable=False),
        sa.Column('requesting_owner_id', sa.Integer(), nullable=False),
        sa.Column('receiving_owner_id', sa.Integer(), nullable=False),
        sa.Column('return_location_id', sa.Integer(), nullable=False),
        sa.Column('requested_date', sa.DateTime(), nullable=False),
        sa.Column('approved_date', sa.DateTime(), nullable=True),
        sa.Column('expected_return_date', sa.DateTime(), nullable=False),
        sa.Column('actual_return_date', sa.DateTime(), nullable=True),
        sa.Column('rma_status', sa.String(length=32), server_default=sa.text("'REQUESTED'"), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['receiving_owner_id'], ['owners.owner_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requesting_owner_id'], ['owners.owner_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['return_location_id'], ['locations.location_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('rma_id')
        )
    if 'ix_return_authorizations_receiving_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorizations')}:
        op.create_index(op.f('ix_return_authorizations_receiving_owner_id'), 'return_authorizations', ['receiving_owner_id'], unique=False)
    if 'ix_return_authorizations_requested_date' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorizations')}:
        op.create_index(op.f('ix_return_authorizations_requested_date'), 'return_authorizations', ['requested_date'], unique=False)
    if 'ix_return_authorizations_requesting_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorizations')}:
        op.create_index(op.f('ix_return_authorizations_requesting_owner_id'), 'return_authorizations', ['requesting_owner_id'], unique=False)
    if 'ix_return_authorizations_return_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorizations')}:
        op.create_index(op.f('ix_return_authorizations_return_location_id'), 'return_authorizations', ['return_location_id'], unique=False)
    if 'ix_return_authorizations_rma_status' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorizations')}:
        op.create_index(op.f('ix_return_authorizations_rma_status'), 'return_authorizations', ['rma_status'], unique=False)
    if 'reusable_assets' not in existing:
        op.create_table('reusable_assets',
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('asset_type_id', sa.Integer(), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('serial_number', sa.String(length=64), nullable=False),
        sa.Column('asset_status', sa.String(length=32), server_default=sa.text("'AVAILABLE'"), nullable=False),
        sa.Column('manufacture_date', sa.Date(), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=False),
        sa.Column('current_location_id', sa.Integer(), nullable=True),
        sa.Column('current_custodian_owner_id', sa.Integer(), nullable=True),
        sa.Column('acquisition_cost', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('deposit_amount', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('last_event_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asset_type_id'], ['asset_types.asset_type_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['current_custodian_owner_id'], ['owners.owner_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['current_location_id'], ['locations.location_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['owner_id'], ['owners.owner_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('asset_id')
        )
    if 'ix_reusable_assets_asset_status' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_asset_status'), 'reusable_assets', ['asset_status'], unique=False)
    if 'ix_reusable_assets_asset_type_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_asset_type_id'), 'reusable_assets', ['asset_type_id'], unique=False)
    if 'ix_reusable_assets_current_custodian_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_current_custodian_owner_id'), 'reusable_assets', ['current_custodian_owner_id'], unique=False)
    if 'ix_reusable_assets_current_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_current_location_id'), 'reusable_assets', ['current_location_id'], unique=False)
    if 'ix_reusable_assets_last_event_at' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_last_event_at'), 'reusable_assets', ['last_event_at'], unique=False)
    if 'ix_reusable_assets_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_owner_id'), 'reusable_assets', ['owner_id'], unique=False)
    if 'ix_reusable_assets_serial_number' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('reusable_assets')}:
        op.create_index(op.f('ix_reusable_assets_serial_number'), 'reusable_assets', ['serial_number'], unique=True)
    if 'shipments' not in existing:
        op.create_table('shipments',
        sa.Column('shipment_id', sa.String(length=32), nullable=False),
        sa.Column('origin_location_id', sa.Integer(), nullable=False),
        sa.Column('destination_location_id', sa.Integer(), nullable=False),
        sa.Column('carrier_owner_id', sa.Integer(), nullable=False),
        sa.Column('dispatch_date', sa.DateTime(), nullable=False),
        sa.Column('expected_delivery_date', sa.DateTime(), nullable=False),
        sa.Column('actual_delivery_date', sa.DateTime(), nullable=True),
        sa.Column('shipment_status', sa.String(length=32), server_default=sa.text("'PLANNED'"), nullable=False),
        sa.Column('tracking_reference', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['carrier_owner_id'], ['owners.owner_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['destination_location_id'], ['locations.location_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['origin_location_id'], ['locations.location_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('shipment_id')
        )
    if 'ix_shipments_carrier_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipments')}:
        op.create_index(op.f('ix_shipments_carrier_owner_id'), 'shipments', ['carrier_owner_id'], unique=False)
    if 'ix_shipments_destination_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipments')}:
        op.create_index(op.f('ix_shipments_destination_location_id'), 'shipments', ['destination_location_id'], unique=False)
    if 'ix_shipments_dispatch_date' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipments')}:
        op.create_index(op.f('ix_shipments_dispatch_date'), 'shipments', ['dispatch_date'], unique=False)
    if 'ix_shipments_origin_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipments')}:
        op.create_index(op.f('ix_shipments_origin_location_id'), 'shipments', ['origin_location_id'], unique=False)
    if 'ix_shipments_shipment_status' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipments')}:
        op.create_index(op.f('ix_shipments_shipment_status'), 'shipments', ['shipment_status'], unique=False)
    if 'ix_shipments_tracking_reference' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipments')}:
        op.create_index(op.f('ix_shipments_tracking_reference'), 'shipments', ['tracking_reference'], unique=False)
    if 'custody_events' not in existing:
        op.create_table('custody_events',
        sa.Column('custody_event_id', sa.String(length=64), nullable=False),
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('shipment_id', sa.String(length=32), nullable=True),
        sa.Column('from_owner_id', sa.Integer(), nullable=True),
        sa.Column('to_owner_id', sa.Integer(), nullable=True),
        sa.Column('from_location_id', sa.Integer(), nullable=True),
        sa.Column('to_location_id', sa.Integer(), nullable=True),
        sa.Column('actor_owner_id', sa.Integer(), nullable=True),
        sa.Column('event_type', sa.String(length=32), nullable=False),
        sa.Column('event_timestamp', sa.DateTime(), nullable=False),
        sa.Column('event_reference', sa.String(length=64), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['actor_owner_id'], ['owners.owner_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['asset_id'], ['reusable_assets.asset_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_location_id'], ['locations.location_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['from_owner_id'], ['owners.owner_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipments.shipment_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['to_location_id'], ['locations.location_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['to_owner_id'], ['owners.owner_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('custody_event_id')
        )
    if 'ix_custody_events_actor_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_actor_owner_id'), 'custody_events', ['actor_owner_id'], unique=False)
    if 'ix_custody_events_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_asset_id'), 'custody_events', ['asset_id'], unique=False)
    if 'ix_custody_events_event_timestamp' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_event_timestamp'), 'custody_events', ['event_timestamp'], unique=False)
    if 'ix_custody_events_event_type' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_event_type'), 'custody_events', ['event_type'], unique=False)
    if 'ix_custody_events_from_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_from_location_id'), 'custody_events', ['from_location_id'], unique=False)
    if 'ix_custody_events_from_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_from_owner_id'), 'custody_events', ['from_owner_id'], unique=False)
    if 'ix_custody_events_shipment_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_shipment_id'), 'custody_events', ['shipment_id'], unique=False)
    if 'ix_custody_events_to_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_to_location_id'), 'custody_events', ['to_location_id'], unique=False)
    if 'ix_custody_events_to_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('custody_events')}:
        op.create_index(op.f('ix_custody_events_to_owner_id'), 'custody_events', ['to_owner_id'], unique=False)
    if 'deposit_ledger' not in existing:
        op.create_table('deposit_ledger',
        sa.Column('ledger_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('shipment_id', sa.String(length=32), nullable=True),
        sa.Column('rma_id', sa.String(length=32), nullable=True),
        sa.Column('transaction_type', sa.String(length=32), nullable=False),
        sa.Column('transaction_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('transaction_reference', sa.String(length=64), nullable=False),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('related_ledger_id', sa.Integer(), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['reusable_assets.asset_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['owner_id'], ['owners.owner_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['related_ledger_id'], ['deposit_ledger.ledger_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['rma_id'], ['return_authorizations.rma_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipments.shipment_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('ledger_id')
        )
    if 'ix_deposit_ledger_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_asset_id'), 'deposit_ledger', ['asset_id'], unique=False)
    if 'ix_deposit_ledger_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_owner_id'), 'deposit_ledger', ['owner_id'], unique=False)
    if 'ix_deposit_ledger_related_ledger_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_related_ledger_id'), 'deposit_ledger', ['related_ledger_id'], unique=False)
    if 'ix_deposit_ledger_rma_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_rma_id'), 'deposit_ledger', ['rma_id'], unique=False)
    if 'ix_deposit_ledger_shipment_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_shipment_id'), 'deposit_ledger', ['shipment_id'], unique=False)
    if 'ix_deposit_ledger_transaction_date' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_transaction_date'), 'deposit_ledger', ['transaction_date'], unique=False)
    if 'ix_deposit_ledger_transaction_reference' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_transaction_reference'), 'deposit_ledger', ['transaction_reference'], unique=False)
    if 'ix_deposit_ledger_transaction_type' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('deposit_ledger')}:
        op.create_index(op.f('ix_deposit_ledger_transaction_type'), 'deposit_ledger', ['transaction_type'], unique=False)
    if 'inspections' not in existing:
        op.create_table('inspections',
        sa.Column('inspection_id', sa.String(length=32), nullable=False),
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('rma_id', sa.String(length=32), nullable=True),
        sa.Column('inspector_owner_id', sa.Integer(), nullable=False),
        sa.Column('inspection_date', sa.DateTime(), nullable=False),
        sa.Column('condition_status', sa.String(length=32), nullable=False),
        sa.Column('damage_severity', sa.String(length=32), nullable=True),
        sa.Column('requires_repair', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('inspection_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['reusable_assets.asset_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inspector_owner_id'], ['owners.owner_id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['rma_id'], ['return_authorizations.rma_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('inspection_id')
        )
    if 'ix_inspections_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('inspections')}:
        op.create_index(op.f('ix_inspections_asset_id'), 'inspections', ['asset_id'], unique=False)
    if 'ix_inspections_condition_status' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('inspections')}:
        op.create_index(op.f('ix_inspections_condition_status'), 'inspections', ['condition_status'], unique=False)
    if 'ix_inspections_inspection_date' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('inspections')}:
        op.create_index(op.f('ix_inspections_inspection_date'), 'inspections', ['inspection_date'], unique=False)
    if 'ix_inspections_inspector_owner_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('inspections')}:
        op.create_index(op.f('ix_inspections_inspector_owner_id'), 'inspections', ['inspector_owner_id'], unique=False)
    if 'ix_inspections_rma_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('inspections')}:
        op.create_index(op.f('ix_inspections_rma_id'), 'inspections', ['rma_id'], unique=False)
    if 'return_authorization_assets' not in existing:
        op.create_table('return_authorization_assets',
        sa.Column('rma_asset_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('rma_id', sa.String(length=32), nullable=False),
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('return_condition', sa.String(length=32), nullable=True),
        sa.Column('received_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['reusable_assets.asset_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rma_id'], ['return_authorizations.rma_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('rma_asset_id'),
        sa.UniqueConstraint('rma_id', 'asset_id', name='uq_rma_asset')
        )
    if 'ix_return_authorization_assets_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorization_assets')}:
        op.create_index(op.f('ix_return_authorization_assets_asset_id'), 'return_authorization_assets', ['asset_id'], unique=False)
    if 'ix_return_authorization_assets_rma_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('return_authorization_assets')}:
        op.create_index(op.f('ix_return_authorization_assets_rma_id'), 'return_authorization_assets', ['rma_id'], unique=False)
    if 'shipment_assets' not in existing:
        op.create_table('shipment_assets',
        sa.Column('shipment_asset_id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('shipment_id', sa.String(length=32), nullable=False),
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('assigned_at', sa.DateTime(), nullable=False),
        sa.Column('removed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['reusable_assets.asset_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['shipment_id'], ['shipments.shipment_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('shipment_asset_id'),
        sa.UniqueConstraint('shipment_id', 'asset_id', name='uq_shipment_asset')
        )
    if 'ix_shipment_assets_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipment_assets')}:
        op.create_index(op.f('ix_shipment_assets_asset_id'), 'shipment_assets', ['asset_id'], unique=False)
    if 'ix_shipment_assets_shipment_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('shipment_assets')}:
        op.create_index(op.f('ix_shipment_assets_shipment_id'), 'shipment_assets', ['shipment_id'], unique=False)
    if 'repairs' not in existing:
        op.create_table('repairs',
        sa.Column('repair_id', sa.String(length=32), nullable=False),
        sa.Column('asset_id', sa.String(length=32), nullable=False),
        sa.Column('inspection_id', sa.String(length=32), nullable=True),
        sa.Column('repair_location_id', sa.Integer(), nullable=False),
        sa.Column('repair_status', sa.String(length=32), server_default=sa.text("'REQUESTED'"), nullable=False),
        sa.Column('repair_start_date', sa.DateTime(), nullable=False),
        sa.Column('repair_completion_date', sa.DateTime(), nullable=True),
        sa.Column('repair_cost', sa.Numeric(precision=12, scale=2), server_default=sa.text('0.0'), nullable=False),
        sa.Column('repair_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['reusable_assets.asset_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['inspection_id'], ['inspections.inspection_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['repair_location_id'], ['locations.location_id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('repair_id')
        )
    if 'ix_repairs_asset_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('repairs')}:
        op.create_index(op.f('ix_repairs_asset_id'), 'repairs', ['asset_id'], unique=False)
    if 'ix_repairs_inspection_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('repairs')}:
        op.create_index(op.f('ix_repairs_inspection_id'), 'repairs', ['inspection_id'], unique=False)
    if 'ix_repairs_repair_location_id' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('repairs')}:
        op.create_index(op.f('ix_repairs_repair_location_id'), 'repairs', ['repair_location_id'], unique=False)
    if 'ix_repairs_repair_start_date' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('repairs')}:
        op.create_index(op.f('ix_repairs_repair_start_date'), 'repairs', ['repair_start_date'], unique=False)
    if 'ix_repairs_repair_status' not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes('repairs')}:
        op.create_index(op.f('ix_repairs_repair_status'), 'repairs', ['repair_status'], unique=False)


def downgrade():
    raise RuntimeError("Destructive downgrade is intentionally disabled; restore an approved backup")
