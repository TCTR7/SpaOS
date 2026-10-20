"""Manual receipts, receivables and append-only audit."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
revision = "0004_manual_payments"
down_revision = "0003_customer_owner"
branch_labels = None
depends_on = None

def cols():
    return [
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True),
    ]

def upgrade():
    op.add_column("customer_packages", sa.Column("purchase_price", sa.Numeric(12, 2), nullable=True))
    op.create_table("payment_invoices", *cols(),
        sa.Column("customer_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("booking_id", UUID(as_uuid=True), sa.ForeignKey("bookings.id"), unique=True),
        sa.Column("customer_package_id", UUID(as_uuid=True), sa.ForeignKey("customer_packages.id"), unique=True),
        sa.Column("amount_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.CheckConstraint("(booking_id IS NULL) <> (customer_package_id IS NULL)", name="ck_invoice_source"),
        sa.CheckConstraint("amount_due >= 0", name="ck_invoice_amount"))
    op.create_table("payment_entries", *cols(),
        sa.Column("invoice_id", UUID(as_uuid=True), sa.ForeignKey("payment_invoices.id"), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("method", sa.String(20), nullable=False),
        sa.Column("recorded_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("idempotency_key", UUID(as_uuid=True), nullable=False),
        sa.Column("reversal_of", UUID(as_uuid=True), sa.ForeignKey("payment_entries.id"), unique=True),
        sa.Column("note", sa.String(500)),
        sa.UniqueConstraint("tenant_id", "idempotency_key", name="uq_payment_idempotency"),
        sa.CheckConstraint("method IN ('CASH','BANK_TRANSFER')", name="ck_payment_method"),
        sa.CheckConstraint("(reversal_of IS NULL AND amount > 0) OR (reversal_of IS NOT NULL AND amount < 0)", name="ck_payment_sign"))
    op.create_table("audit_logs", *cols(),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("details", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")))
    for table in ("payment_invoices", "payment_entries", "audit_logs"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
            WITH CHECK (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)""")
        op.execute(f"""DO $$ DECLARE r text; BEGIN
            FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
                     WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
            LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO %I', r); END LOOP;
            END $$""")
    op.execute("""CREATE FUNCTION spaos_reject_ledger_change() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'Ledger and audit records are append-only'; END $$""")
    for table in ("payment_entries", "audit_logs"):
        op.execute(f"CREATE TRIGGER immutable_record BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION spaos_reject_ledger_change()")

def downgrade():
    for table in ("audit_logs", "payment_entries", "payment_invoices"):
        op.drop_table(table)
    op.execute("DROP FUNCTION spaos_reject_ledger_change()")
    op.drop_column("customer_packages", "purchase_price")
