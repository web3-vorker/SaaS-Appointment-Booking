"""add_subscription_event_nullable_appointment_and_index

Revision ID: a1b2c3d4e5f6
Revises: 28912222cbdc
Create Date: 2026-06-14 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '28912222cbdc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        'events',
        'appointment_id',
        existing_type=sa.Integer(),
        nullable=True,
    )

    op.create_index(
        'uq_event_type_business_null_appointment',
        'events',
        ['type', 'business_id'],
        unique=True,
        postgresql_where=sa.text('appointment_id IS NULL'),
    )


def downgrade() -> None:
    op.drop_index('uq_event_type_business_null_appointment', table_name='events')
    op.alter_column(
        'events',
        'appointment_id',
        existing_type=sa.Integer(),
        nullable=False,
    )
