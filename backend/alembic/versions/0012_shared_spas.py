"""Explicit owner boundary; legacy rows remain unmapped until verified mapping."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0012_shared_spas"
down_revision = "0011_staff_profile"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("spas",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("theme_color", sa.String(7), nullable=False, server_default="#be185d"),
        sa.Column("logo_url", sa.String(500)), sa.Column("logo_data", sa.LargeBinary()), sa.Column("cover_url", sa.String(500)), sa.Column("cover_data", sa.LargeBinary()),
        sa.Column("contact_phone", sa.String(20)),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("branch_limit", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("staff_limit", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("operator_id", UUID(), sa.ForeignKey("deployment_operators.id")),
        sa.CheckConstraint("theme_color ~ '^#[0-9a-f]{6}$'", name="ck_spa_color"),
        sa.CheckConstraint("branch_limit > 0 AND staff_limit > 0", name="ck_spa_limits"))
    for table in ("tenants", "login_accounts"):
        op.add_column(table, sa.Column("spa_id", UUID(), sa.ForeignKey("spas.id")))
        op.create_index(f"ix_{table}_spa_id", table, ["spa_id"])
    op.add_column("login_accounts", sa.Column("default_branch_id", UUID(), sa.ForeignKey("tenants.id")))
    op.create_unique_constraint("uq_account_spa", "login_accounts", ["id", "spa_id"])
    op.create_unique_constraint("uq_tenant_spa", "tenants", ["id", "spa_id"])
    op.create_table("staff_assignments",
        sa.Column("id", UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("spa_id", UUID(), sa.ForeignKey("spas.id"), nullable=False, index=True),
        sa.Column("account_id", UUID(), sa.ForeignKey("login_accounts.id"), nullable=False, index=True),
        sa.Column("tenant_id", UUID(), sa.ForeignKey("tenants.id")),
        sa.Column("day", sa.Date()), sa.Column("weekday", sa.Integer()),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time()), sa.Column("end_time", sa.Time()),
        sa.ForeignKeyConstraint(["account_id", "spa_id"], ["login_accounts.id", "login_accounts.spa_id"]),
        sa.ForeignKeyConstraint(["tenant_id", "spa_id"], ["tenants.id", "tenants.spa_id"]),
        sa.UniqueConstraint("account_id", "day", name="uq_assignment_date"),
        sa.UniqueConstraint("account_id", "effective_from", "weekday", name="uq_assignment_week"),
        sa.CheckConstraint("(day IS NOT NULL AND weekday IS NULL) OR (day IS NULL AND weekday IS NOT NULL AND weekday BETWEEN 0 AND 6)", name="ck_assignment_kind"),
        sa.CheckConstraint("day IS NULL OR effective_from = day", name="ck_assignment_date"),
        sa.CheckConstraint("(tenant_id IS NULL AND start_time IS NULL AND end_time IS NULL) OR (tenant_id IS NOT NULL AND start_time IS NOT NULL AND end_time IS NOT NULL AND end_time > start_time)", name="ck_assignment_hours"))
    # Membership/account data remains private. No public global brand directory.
    spa = "NULLIF(current_setting('app.current_spa_id',true),'')::uuid"
    tenant = "NULLIF(current_setting('app.current_tenant_id',true),'')::uuid"
    operator = "NULLIF(current_setting('app.current_operator_id',true),'')::uuid"
    public = "NULLIF(current_setting('app.public_spa_slug',true),'')"
    for table in ("spas", "staff_assignments"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""DO $$ DECLARE r text; BEGIN
          FOR r IN SELECT DISTINCT grantee FROM information_schema.role_table_grants
            WHERE table_schema='public' AND table_name='users' AND privilege_type='SELECT'
          LOOP EXECUTE format('GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO %I', r); END LOOP;
          END $$""")
    allowed = f"id={spa} OR id IN (SELECT spa_id FROM tenants WHERE id={tenant})"
    op.execute(f"CREATE POLICY spa_read ON spas FOR SELECT USING ({allowed} OR slug={public} OR operator_id={operator})")
    op.execute(f"CREATE POLICY spa_write ON spas FOR ALL USING (id={spa}) WITH CHECK (id={spa})")
    scope = f"spa_id={spa} OR spa_id IN (SELECT spa_id FROM tenants WHERE id={tenant})"
    op.execute(f"CREATE POLICY assignment_read ON staff_assignments FOR SELECT USING ({scope})")
    op.execute(f"CREATE POLICY assignment_write ON staff_assignments FOR ALL USING (spa_id={spa}) WITH CHECK (spa_id={spa})")
    # Validate owner boundaries even when callers accidentally mix branch IDs.
    op.execute("""CREATE FUNCTION spaos_check_membership_spa() RETURNS trigger LANGUAGE plpgsql AS $$
      DECLARE a uuid; b uuid; BEGIN
        SELECT spa_id INTO a FROM login_accounts WHERE id=NEW.account_id;
        SELECT spa_id INTO b FROM tenants WHERE id=NEW.tenant_id;
        IF a IS NULL OR b IS NULL OR a<>b THEN RAISE EXCEPTION 'Membership spa mismatch' USING ERRCODE='23514'; END IF;
        RETURN NEW;
      END $$""")
    op.execute("CREATE TRIGGER check_membership_spa BEFORE INSERT OR UPDATE ON branch_memberships FOR EACH ROW EXECUTE FUNCTION spaos_check_membership_spa()")


def downgrade():
    raise RuntimeError("Shared spa migration requires reviewed restore/reconciliation; automatic destructive downgrade disabled")
