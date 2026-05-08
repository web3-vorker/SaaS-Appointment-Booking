"""add_client_name_to_appointments

Revision ID: b279b40843b1
Revises: fa10ace46fd1
Create Date: 2026-05-06 22:46:41.301193

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b279b40843b1'
down_revision: Union[str, Sequence[str], None] = 'fa10ace46fd1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Добавляем колонку client_name в таблицу appointments
    op.add_column('appointments', sa.Column('client_name', sa.String(), nullable=True))
    
    # Заполняем существующие записи именами из таблицы clients
    op.execute("""
        UPDATE appointments 
        SET client_name = clients.name 
        FROM clients 
        WHERE appointments.client_id = clients.id
    """)
    
    # Делаем колонку NOT NULL после заполнения данных
    op.alter_column('appointments', 'client_name', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Удаляем колонку client_name
    op.drop_column('appointments', 'client_name')
