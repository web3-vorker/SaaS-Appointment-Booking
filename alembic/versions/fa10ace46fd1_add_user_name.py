"""Add user_name

Revision ID: fa10ace46fd1
Revises: 6a8ea777362e
Create Date: 2026-05-06 22:13:40.744505

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fa10ace46fd1'
down_revision: Union[str, Sequence[str], None] = '6a8ea777362e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
