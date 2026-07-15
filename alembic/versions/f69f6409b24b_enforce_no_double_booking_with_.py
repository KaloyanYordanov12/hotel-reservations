"""enforce no double booking with exclusion constraint

Revision ID: f69f6409b24b
Revises: 96a12b9256b3
Create Date: 2026-07-15 23:09:40.507778

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f69f6409b24b'
down_revision: Union[str, Sequence[str], None] = '96a12b9256b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # btree_gist is required because room_id is compared with =, and plain GiST
    # has no operator class for scalar equality on text.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # check_out > check_in. Time does not run backwards, and a zero-night stay
    # is a typo. This also rejects the inverted-date case.
    op.execute(
        "ALTER TABLE reservations "
        "ADD CONSTRAINT valid_dates "
        "CHECK (check_out > check_in)"
    )

    # No two reservations for the same room may overlap. '[)' is half-open:
    # check-in inclusive, check-out exclusive. That is exactly A < D AND B > C,
    # which is what keeps same-day turnover (one guest's check-out equal to the
    # next guest's check-in) legal. Do not change '[)' to '[]'.
    op.execute(
        "ALTER TABLE reservations "
        "ADD CONSTRAINT no_double_booking "
        "EXCLUDE USING gist ("
        "  room_id WITH =, "
        "  daterange(check_in, check_out, '[)') WITH &&"
        ")"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE reservations DROP CONSTRAINT no_double_booking")
    op.execute("ALTER TABLE reservations DROP CONSTRAINT valid_dates")
    # btree_gist is left installed. CREATE EXTENSION IF NOT EXISTS is idempotent,
    # so leaving it does not block a re-upgrade, and dropping a shared extension
    # is riskier than leaving it.
