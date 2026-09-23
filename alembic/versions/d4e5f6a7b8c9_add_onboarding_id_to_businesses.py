"""add onboarding id to businesses

Revision ID: d4e5f6a7b8c9
Revises: 7eab09eeef31, a1b2c3d4e5f6
Create Date: 2026-09-19
"""
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = (
    "7eab09eeef31",
    "a1b2c3d4e5f6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "businesses",
        sa.Column("onboarding_id", sa.String(length=128), nullable=True),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id FROM businesses WHERE onboarding_id IS NULL")
    ).fetchall()
    for (business_id,) in rows:
        connection.execute(
            sa.text(
                "UPDATE businesses SET onboarding_id = :onboarding_id "
                "WHERE id = :business_id"
            ),
            {
                "business_id": business_id,
                "onboarding_id": str(uuid.uuid4()),
            },
        )

    with op.batch_alter_table("businesses") as batch:
        batch.alter_column(
            "onboarding_id",
            existing_type=sa.String(length=128),
            nullable=False,
        )
        batch.create_unique_constraint(
            "uq_business_onboarding_id",
            ["onboarding_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("businesses") as batch:
        batch.drop_constraint("uq_business_onboarding_id", type_="unique")
        batch.drop_column("onboarding_id")
