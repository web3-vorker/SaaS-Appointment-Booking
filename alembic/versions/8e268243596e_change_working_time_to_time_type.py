"""change_working_time_to_time_type

Revision ID: 8e268243596e
Revises: b279b40843b1
Create Date: 2026-05-07 21:25:40.647257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e268243596e'
down_revision: Union[str, Sequence[str], None] = 'b279b40843b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: change working_time columns from DateTime to Time."""
    # PostgreSQL: изменяем тип колонок, извлекая только время из существующих DateTime значений
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN working_time_start TYPE TIME 
        USING working_time_start::time
    """)
    
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN working_time_end TYPE TIME 
        USING working_time_end::time
    """)


def downgrade() -> None:
    """Downgrade schema: revert Time back to DateTime."""
    # При откате добавляем текущую дату к времени
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN working_time_start TYPE TIMESTAMP 
        USING CURRENT_DATE + working_time_start
    """)
    
    op.execute("""
        ALTER TABLE businesses 
        ALTER COLUMN working_time_end TYPE TIMESTAMP 
        USING CURRENT_DATE + working_time_end
    """)
