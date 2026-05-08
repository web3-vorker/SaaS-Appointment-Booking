"""add_indexes_to_events_table

Revision ID: 28912222cbdc
Revises: 8e268243596e
Create Date: 2026-05-08 15:27:19.724603

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '28912222cbdc'
down_revision: Union[str, Sequence[str], None] = '8e268243596e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем индексы для оптимизации запросов к events таблице
    op.create_index('ix_events_business_pending', 'events', ['business_id', 'is_sent'], unique=False)
    op.create_index('ix_events_sent_created', 'events', ['is_sent', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индексы при откате миграции
    op.drop_index('ix_events_sent_created', table_name='events')
    op.drop_index('ix_events_business_pending', table_name='events')
