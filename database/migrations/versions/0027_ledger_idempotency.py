"""Enforce a durable financial transaction idempotency key.

No rows are changed. Existing duplicates require an independently reviewed
financial correction; this migration refuses to hide or delete them.
"""
from alembic import op
import sqlalchemy as sa
revision = "0027_ledger_idempotency"
down_revision = "0026_complete_schema"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    duplicate = bind.execute(sa.text("SELECT transaction_reference FROM deposit_ledger GROUP BY transaction_reference HAVING COUNT(*) > 1 LIMIT 1")).first()
    if duplicate:
        raise RuntimeError("Duplicate ledger references exist; review obligations before migration")
    names = {c["name"] for c in sa.inspect(bind).get_unique_constraints("deposit_ledger")}
    if "uq_deposit_reference" not in names:
        op.create_unique_constraint("uq_deposit_reference", "deposit_ledger", ["transaction_reference"])


def downgrade():
    raise RuntimeError("Removing financial idempotency requires an approved manual rollback")
