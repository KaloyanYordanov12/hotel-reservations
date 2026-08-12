"""Populate the demo database with a believable few weeks of bookings.

This is the demo's data, not the real hotel's. It wipes every existing
reservation and reseeds a fixed, known set, so a demo deployment can be reset to
a clean populated state on a schedule (the reset entrypoint added in a later step
calls seed()). Running it twice leaves the same rows, never duplicates.

It writes only to the database DATABASE_URL points at. In the demo deployment
that is hotel_demo; the demo env has no reference to the real hotel database at
all. The hard "refuse unless the database is named hotel_demo" guard belongs to
the reset entrypoint (a later step), not here, because this same seed() is what
the tests drive against hotel_test.

Rooms are NOT seeded here. They come from the Alembic migrations; this sits on
top of them and references their ids.

The bookings are anchored to a date passed in (today, when run as a script), so
the availability grid always looks alive relative to whenever a visitor opens
the demo. The spread is deliberately ordinary: some rooms busy, two rooms
(4.4 and A8) left free so availability is visible, stays of varying length, two
same-day turnovers (one guest checks out and the next checks in the same day) to
show the half-open [check_in, check_out) handling, a mix of paid and still-owed
deposits, and a few notes in Bulgarian. Nothing here is engineered to look like
a feature demo; a visitor who tries to book an already-booked room simply hits
the exclusion constraint, which is the feature demoing itself.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.models import Reservation

# Each entry is one booking. "in"/"out" are day offsets from the anchor date and
# are half-open: check_out is the morning the room frees. Per room the intervals
# never overlap, so every row inserts cleanly under the no_double_booking
# exclusion constraint. Two rooms are intentionally absent so they read as free.
_BOOKINGS = [
    # 3.2: an early stay, then a later one. Free in between.
    {"room": "3.2", "name": "Георги Иванов", "phone": "+359888123456",
     "in": 0, "out": 3, "guests": 3, "parking": True, "deposit": "100.00",
     "note": "Плаща при настаняване."},
    {"room": "3.2", "name": "Димитър Василев", "phone": "+359889654321",
     "in": 14, "out": 18, "guests": 2, "deposit": "90.00"},

    # 3.3: a same-day turnover. Петрова checks out the morning Димитров arrives.
    {"room": "3.3", "name": "Мария Петрова", "phone": "+359877445566",
     "in": 2, "out": 5, "guests": 2, "deposit": "50.00"},
    {"room": "3.3", "name": "Иван Димитров", "phone": "+359877998877",
     "in": 5, "out": 9, "guests": 2, "deposit": "0",
     "note": "Пристигат след 22:00 ч."},

    # 3.4
    {"room": "3.4", "name": "Елена Георгиева", "phone": "+359898112233",
     "in": 6, "out": 11, "guests": 2, "parking": True, "deposit": "75.50",
     "note": "Годишнина, моля цветя в стаята."},
    {"room": "3.4", "name": "Кристиан Христов", "phone": "+359898776655",
     "in": 15, "out": 19, "guests": 2, "deposit": "30.00"},

    # 4.1 studio
    {"room": "4.1", "name": "Николай Стоянов", "phone": "+359886334455",
     "in": 1, "out": 4, "guests": 4, "deposit": "120.00"},
    {"room": "4.1", "name": "Александър Данаилов", "phone": "+359886221100",
     "in": 9, "out": 13, "guests": 4, "deposit": "0", "note": "Тиха стая, моля."},

    # 4.2 triple
    {"room": "4.2", "name": "Десислава Тодорова", "phone": "+359895667788",
     "in": 8, "out": 12, "guests": 3, "deposit": "60.00"},
    {"room": "4.2", "name": "Йордан Петков", "phone": "+359895009988",
     "in": 16, "out": 20, "guests": 3, "parking": True, "deposit": "70.00"},

    # 4.3
    {"room": "4.3", "name": "Петър Колев", "phone": "+359877010203",
     "in": 3, "out": 7, "guests": 2, "deposit": "40.00"},
    {"room": "4.3", "name": "Габриела Панайотова", "phone": "+359877040506",
     "in": 12, "out": 16, "guests": 2, "deposit": "55.00"},

    # A3 apartment: the second same-day turnover.
    {"room": "A3", "name": "Виолета Ангелова", "phone": "+359884556677",
     "in": 1, "out": 4, "guests": 4, "parking": True, "deposit": "150.00"},
    {"room": "A3", "name": "Стефан Маринов", "phone": "+359884990011",
     "in": 4, "out": 8, "guests": 3, "deposit": "80.00"},

    # A11 apartment
    {"room": "A11", "name": "Валентина Атанасова", "phone": "+359883778899",
     "in": 1, "out": 5, "guests": 2, "deposit": "45.00"},
    {"room": "A11", "name": "Радостина Николова", "phone": "+359883001122",
     "in": 10, "out": 14, "guests": 4, "deposit": "0",
     "note": "Дете на 3 г., нужно е бебешко легло."},

    # 4.4 studio and A8 studio are left free on purpose.
]

# Fixed by construction, so the reset always lands on the same clean state and a
# test can assert it exactly.
EXPECTED_RESERVATION_COUNT = len(_BOOKINGS)


def build_reservations(anchor: date) -> list[Reservation]:
    """The demo bookings as unsaved Reservation objects, dated from ``anchor``."""
    rows = []
    for booking in _BOOKINGS:
        rows.append(
            Reservation(
                room_id=booking["room"],
                guest_name=booking["name"],
                guest_phone=booking["phone"],
                check_in=anchor + timedelta(days=booking["in"]),
                check_out=anchor + timedelta(days=booking["out"]),
                num_guests=booking["guests"],
                parking=booking.get("parking", False),
                deposit_paid=Decimal(booking.get("deposit", "0")),
                note=booking.get("note"),
            )
        )
    return rows


def seed(session, anchor: date | None = None) -> None:
    """Wipe all reservations and insert the demo set. The caller commits.

    Idempotent by wiping first: run it any number of times and the table holds
    exactly the demo bookings. Rooms are never touched. ``anchor`` defaults to
    today so a script run looks current; tests pass a fixed date.
    """
    if anchor is None:
        anchor = date.today()
    session.execute(delete(Reservation))
    session.add_all(build_reservations(anchor))


def main() -> None:
    # Uses the app's engine, so it writes to whatever DATABASE_URL is set to.
    from app.db import SessionLocal

    with SessionLocal() as session:
        seed(session)
        session.commit()
        count = session.query(Reservation).count()
    print(f"Seeded {count} demo reservations.")


if __name__ == "__main__":
    main()
