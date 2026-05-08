"""Add staff_services table for many-to-many relationship

Revision ID: 6a8ea777362e
Revises: 
Create Date: 2026-05-04 17:00:59.224443

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6a8ea777362e'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('staff_services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', sa.Integer(), nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staffs.id'], name=op.f('staff_services_staff_id_fkey')),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], name=op.f('staff_services_service_id_fkey')),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('staff_services_business_id_fkey')),
        sa.PrimaryKeyConstraint('id', name=op.f('staff_services_pkey'))
    )
    op.create_index(op.f('ix_staff_services_business_id'), 'staff_services', ['business_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_staff_services_business_id'), table_name='staff_services')
    op.drop_table('staff_services')
