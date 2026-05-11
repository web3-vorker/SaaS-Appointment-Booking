"""add_schedule_features_and_exceptions

Revision ID: c8a45261b61e
Revises: 28912222cbdc
Create Date: 2026-05-08 20:26:59.955396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8a45261b61e'
down_revision: Union[str, Sequence[str], None] = '28912222cbdc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем новые поля в businesses таблицу
    op.add_column('businesses', sa.Column('break_start', sa.Time(), nullable=True))
    op.add_column('businesses', sa.Column('break_end', sa.Time(), nullable=True))
    
    # Проверяем существование weekend_days и меняем тип на JSON
    # Для PostgreSQL можем просто добавить новую колонку если её нет
    from sqlalchemy import inspect
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('businesses')]
    
    if 'weekend_days' in columns:
        # Если колонка существует, удаляем и создаем заново
        op.drop_column('businesses', 'weekend_days')
    
    # Добавляем weekend_days как JSON
    op.add_column('businesses', sa.Column('weekend_days', sa.JSON(), nullable=True))
    
    # Создаем таблицу schedule_exceptions
    op.create_table(
        'schedule_exceptions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('business_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('is_working', sa.Boolean(), nullable=False, default=True),
        sa.Column('custom_start_time', sa.Time(), nullable=True),
        sa.Column('custom_end_time', sa.Time(), nullable=True),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Создаем индекс для быстрого поиска
    op.create_index('ix_schedule_exceptions_business_date', 'schedule_exceptions', ['business_id', 'date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем индекс
    op.drop_index('ix_schedule_exceptions_business_date', table_name='schedule_exceptions')
    
    # Удаляем таблицу schedule_exceptions
    op.drop_table('schedule_exceptions')
    
    # Удаляем weekend_days
    op.drop_column('businesses', 'weekend_days')
    
    # Удаляем новые колонки из businesses
    op.drop_column('businesses', 'break_end')
    op.drop_column('businesses', 'break_start')
