"""Persistent customer owner; existing customers require explicit Admin assignment."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
revision = "0003_customer_owner"
down_revision = "0002_notifications"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("users", sa.Column("assigned_staff_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_users_assigned_staff", "users", "users", ["assigned_staff_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_users_assigned_staff_id", "users", ["assigned_staff_id"])

def downgrade():
    op.drop_index("ix_users_assigned_staff_id", table_name="users")
    op.drop_constraint("fk_users_assigned_staff", "users", type_="foreignkey")
    op.drop_column("users", "assigned_staff_id")
