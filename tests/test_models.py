from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Reservation, Room


def test_ten_rooms_seeded(db_session):
    assert db_session.query(Room).count() == 10


def test_display_order_must_be_unique(db_session):
    """Two rooms sharing a display_order would collapse under DISTINCT ON and one
    room would vanish from the availability screen. The database must forbid it."""
    room = db_session.get(Room, "3.4")  # display_order 3
    room.display_order = 1  # 3.2 already holds 1
    with pytest.raises(IntegrityError) as exc:
        db_session.flush()
    assert exc.value.orig.diag.constraint_name == "uq_rooms_display_order"


def test_deposit_paid_round_trips_as_decimal(db_session):
    """deposit_paid must come back from the database as Decimal, never float.

    This is the trap called out in the brief. A float here would silently
    introduce rounding error into money. We flush and then reload from the
    database so the value under test is the one psycopg produced, not the
    Decimal we happened to pass in.
    """
    reservation = Reservation(
        room_id="3.3",
        guest_name="Ivan Petrov",
        guest_phone="+359888123456",
        check_in=date(2026, 8, 10),
        check_out=date(2026, 8, 15),
        num_guests=2,
        deposit_paid=Decimal("50.00"),
    )
    db_session.add(reservation)
    db_session.flush()
    db_session.refresh(reservation)

    assert isinstance(reservation.deposit_paid, Decimal)
    assert reservation.deposit_paid == Decimal("50.00")
