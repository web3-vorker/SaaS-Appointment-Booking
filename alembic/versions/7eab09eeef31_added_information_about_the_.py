"""Added information about the subscription and expiration date

Revision ID: 7eab09eeef31
Revises: c7f77e67b5ae
Create Date: 2026-06-13 21:20:30.020114

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7eab09eeef31'
down_revision: Union[str, Sequence[str], None] = 'c7f77e67b5ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('businesses', sa.Column('subscription_plan', sa.String(), nullable=True))
    op.add_column('businesses', sa.Column('subscription_expires_at', sa.DateTime(), nullable=True))
    op.add_column('businesses', sa.Column('subscription_notified_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('businesses', 'subscription_notified_at')
    op.drop_column('businesses', 'subscription_expires_at')
    op.drop_column('businesses', 'subscription_plan')
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('business_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('date', sa.DATE(), autoincrement=False, nullable=False),
    sa.Column('is_working', sa.BOOLEAN(), autoincrement=False, nullable=False),
    sa.Column('custom_start_time', postgresql.TIME(), autoincrement=False, nullable=True),
    sa.Column('custom_end_time', postgresql.TIME(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('schedule_exceptions_business_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('schedule_exceptions_pkey'))
    op.create_index(op.f('ix_schedule_exceptions_business_date'), 'schedule_exceptions', ['business_id', 'date'], unique=False)
    op.create_table('businesses',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('working_time_start', postgresql.TIME(), autoincrement=False, nullable=False),
    sa.Column('working_time_end', postgresql.TIME(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), autoincrement=False, nullable=True),
    sa.Column('bot_token', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('owner_tg_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('api_key', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('break_start', postgresql.TIME(), autoincrement=False, nullable=True),
    sa.Column('break_end', postgresql.TIME(), autoincrement=False, nullable=True),
    sa.Column('weekend_days', postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('businesses_pkey')),
    sa.UniqueConstraint('api_key', name=op.f('businesses_api_key_key'), postgresql_include=[], postgresql_nulls_not_distinct=False),
    sa.UniqueConstraint('bot_token', name=op.f('businesses_bot_token_key'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_table('clients',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('name', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('phone', sa.VARCHAR(), autoincrement=False, nullable=True),
    sa.Column('tg_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('business_id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('created_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], name=op.f('clients_business_id_fkey')),
    sa.PrimaryKeyConstraint('id', name=op.f('clients_pkey')),
    sa.UniqueConstraint('business_id', 'tg_id', name=op.f('uq_client_business_tg'), postgresql_include=[], postgresql_nulls_not_distinct=False)
    )
    op.create_index(op.f('ix_clients_business_id'), 'clients', ['business_id'], unique=False)
    op.create_index(op.f('ix_clients_business_client'), 'clients', ['business_id', 'id'], unique=False)
    # ### end Alembic commands ###
