"""add room display_order

Revision ID: 859d84317512
Revises: f69f6409b24b
Create Date: 2026-07-16 00:44:35.892803

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '859d84317512'
down_revision: Union[str, Sequence[str], None] = 'f69f6409b24b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Sensible screen order, not the string order of the ids.
DISPLAY_ORDER = {
    "3.2": 1,
    "3.3": 2,
    "3.4": 3,
    "4.1": 4,
    "4.2": 5,
    "4.3": 6,
    "4.4": 7,
    "A3": 8,
    "A8": 9,
    "A11": 10,
}


def upgrade() -> None:
    """Upgrade schema."""
    # Add nullable first so the existing seeded rooms are legal, populate each
    # one, then enforce NOT NULL.
    op.add_column(
        "rooms", sa.Column("display_order", sa.Integer(), nullable=True)
    )
    for room_id, order in DISPLAY_ORDER.items():
        op.execute(
            sa.text("UPDATE rooms SET display_order = :order WHERE id = :id").bindparams(
                order=order, id=room_id
            )
        )
    op.alter_column("rooms", "display_order", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("rooms", "display_order")
