"""Delete bot token from BusinessModel and BusinessCreateSchema

Revision ID: c7f77e67b5ae
Revises: c8a45261b61e
Create Date: 2026-05-12 14:49:12.802479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7f77e67b5ae'
down_revision: Union[str, Sequence[str], None] = 'c8a45261b61e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
