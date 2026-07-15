from datetime import date
from decimal import Decimal

from app.models import Reservation, Room


def test_ten_rooms_seeded(db_session):
    assert db_session.query(Room).count() == 10


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
