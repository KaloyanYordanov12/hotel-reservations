"""The demo booking seed populates cleanly and resets idempotently.

These run against hotel_test (the db_session fixture), which already has the
seeded rooms from the migrations, so the bookings' room ids resolve and the
foreign key and exclusion constraint are the real ones.
"""
from datetime import date

from app.models import Reservation
from scripts.seed_demo import EXPECTED_RESERVATION_COUNT, seed

# A fixed anchor so the test does not depend on the day it runs.
_ANCHOR = date(2026, 9, 1)


def test_seed_produces_expected_count(db_session):
    seed(db_session, anchor=_ANCHOR)
    assert db_session.query(Reservation).count() == EXPECTED_RESERVATION_COUNT


def test_seed_is_idempotent_reset(db_session):
    # Running twice wipes and reseeds, so the count is stable, never doubled.
    seed(db_session, anchor=_ANCHOR)
    seed(db_session, anchor=_ANCHOR)
    assert db_session.query(Reservation).count() == EXPECTED_RESERVATION_COUNT


def test_seed_reset_clears_prior_bookings(db_session, reservation_factory):
    # A booking present before the seed must be gone after it: reset is a wipe.
    db_session.add(reservation_factory(room_id="4.4", guest_name="Стар гост"))
    db_session.flush()
    seed(db_session, anchor=_ANCHOR)
    names = {r.guest_name for r in db_session.query(Reservation).all()}
    assert "Стар гост" not in names
    assert db_session.query(Reservation).count() == EXPECTED_RESERVATION_COUNT


def test_seed_includes_a_same_day_turnover(db_session):
    # The half-open [check_in, check_out) handling is part of what the demo
    # shows, so at least one room must have a check_out that equals the next
    # booking's check_in. If this ever stops being true the demo lost a feature.
    seed(db_session, anchor=_ANCHOR)
    rows = db_session.query(Reservation).all()
    by_room: dict[str, list[Reservation]] = {}
    for row in rows:
        by_room.setdefault(row.room_id, []).append(row)
    turnovers = 0
    for room_rows in by_room.values():
        checkouts = {r.check_out for r in room_rows}
        checkins = {r.check_in for r in room_rows}
        turnovers += len(checkouts & checkins)
    assert turnovers >= 1
