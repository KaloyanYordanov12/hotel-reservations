"""seed the ten rooms

Revision ID: 96a12b9256b3
Revises: 5b7be229b247
Create Date: 2026-07-15 21:26:11.674681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96a12b9256b3'
down_revision: Union[str, Sequence[str], None] = '5b7be229b247'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# The ten rooms, exactly as confirmed in the Phase 1 brief. standard_occupancy
# is a display value only and is never enforced anywhere. These values are not
# to be adjusted.
ROOMS = [
    {"id": "3.3", "type": "double", "standard_occupancy": 2},
    {"id": "3.4", "type": "double", "standard_occupancy": 2},
    {"id": "4.3", "type": "double", "standard_occupancy": 2},
    {"id": "4.4", "type": "double", "standard_occupancy": 2},
    {"id": "3.2", "type": "triple", "standard_occupancy": 3},
    {"id": "4.2", "type": "triple", "standard_occupancy": 3},
    {"id": "A3", "type": "apartment", "standard_occupancy": 4},
    {"id": "A11", "type": "apartment", "standard_occupancy": 4},
    {"id": "4.1", "type": "studio", "standard_occupancy": 4},
    {"id": "A8", "type": "studio", "standard_occupancy": 4},
]

# create_type=False: the room_type enum already exists from the prior migration,
# so this table reference must not try to create it again.
room_type = sa.Enum(
    "double", "triple", "apartment", "studio", name="room_type", create_type=False
)

rooms_table = sa.table(
    "rooms",
    sa.column("id", sa.String),
    sa.column("type", room_type),
    sa.column("standard_occupancy", sa.Integer),
)


def upgrade() -> None:
    """Upgrade schema."""
    op.bulk_insert(rooms_table, ROOMS)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        rooms_table.delete().where(
            rooms_table.c.id.in_([room["id"] for room in ROOMS])
        )
    )
