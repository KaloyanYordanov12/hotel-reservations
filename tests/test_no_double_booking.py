"""The no-double-booking rule, enforced by the Postgres exclusion constraint.

These tests are written before the migration exists (TDD). The reject cases fail
until the constraint is added, which is the point.
"""
import threading
import time
from datetime import date

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from app.models import Reservation

# Every case shares this existing reservation for room 3.3.
BASELINE = dict(
    room_id="3.3", check_in=date(2026, 8, 10), check_out=date(2026, 8, 15)
)

# label, room, check_in, check_out, expected_constraint
# expected_constraint is None for an allowed insert, otherwise the exact name of
# the constraint that must reject it. The overlap cases fire no_double_booking;
# the zero-night and inverted-date cases fire valid_dates, which is a different
# constraint and must not be conflated with the overlap ones.
MATRIX = [
    ("identical", "3.3", date(2026, 8, 10), date(2026, 8, 15), "no_double_booking"),
    ("fully_inside", "3.3", date(2026, 8, 11), date(2026, 8, 14), "no_double_booking"),
    ("fully_contains", "3.3", date(2026, 8, 8), date(2026, 8, 18), "no_double_booking"),
    ("overlaps_start", "3.3", date(2026, 8, 8), date(2026, 8, 12), "no_double_booking"),
    ("overlaps_end", "3.3", date(2026, 8, 13), date(2026, 8, 18), "no_double_booking"),
    ("turnover_new_checkout_eq_existing_checkin", "3.3", date(2026, 8, 5), date(2026, 8, 10), None),
    ("turnover_new_checkin_eq_existing_checkout", "3.3", date(2026, 8, 15), date(2026, 8, 20), None),
    ("entirely_before", "3.3", date(2026, 8, 1), date(2026, 8, 5), None),
    ("entirely_after", "3.3", date(2026, 8, 20), date(2026, 8, 25), None),
    ("different_room_same_dates", "4.4", date(2026, 8, 10), date(2026, 8, 15), None),
    ("zero_night_stay", "3.3", date(2026, 8, 10), date(2026, 8, 10), "valid_dates"),
    ("inverted_dates", "3.3", date(2026, 8, 15), date(2026, 8, 10), "valid_dates"),
]


@pytest.mark.parametrize(
    "label,room,check_in,check_out,expected_constraint",
    MATRIX,
    ids=[row[0] for row in MATRIX],
)
def test_overlap_matrix(
    db_session, reservation_factory, label, room, check_in, check_out, expected_constraint
):
    db_session.add(reservation_factory(**BASELINE))
    db_session.flush()

    db_session.add(
        reservation_factory(room_id=room, check_in=check_in, check_out=check_out)
    )
    if expected_constraint is not None:
        with pytest.raises(IntegrityError) as exc:
            db_session.flush()
        assert exc.value.orig.diag.constraint_name == expected_constraint
    else:
        db_session.flush()
        total = db_session.scalar(select(func.count()).select_from(Reservation))
        assert total == 2


def test_self_update_does_not_conflict(db_session, reservation_factory):
    """A row must not conflict with its own previous version."""
    reservation = reservation_factory(**BASELINE)
    db_session.add(reservation)
    db_session.flush()

    reservation.check_in = date(2026, 8, 11)
    reservation.check_out = date(2026, 8, 16)
    db_session.flush()  # must not raise

    db_session.refresh(reservation)
    assert reservation.check_out == date(2026, 8, 16)


def test_update_into_conflict_is_rejected(db_session, reservation_factory):
    first = reservation_factory(**BASELINE)  # 08-10 to 08-15
    second = reservation_factory(
        room_id="3.3", check_in=date(2026, 8, 20), check_out=date(2026, 8, 25)
    )
    db_session.add_all([first, second])
    db_session.flush()

    first.check_out = date(2026, 8, 22)  # now overlaps second
    with pytest.raises(IntegrityError) as exc:
        db_session.flush()
    assert exc.value.orig.diag.constraint_name == "no_double_booking"


def _wait_until_blocked(engine, timeout):
    """Return once at least one backend is waiting on a lock, or after timeout.

    Bounded so that a failure to block (for example before the constraint
    exists) cannot hang the poll.
    """
    deadline = time.monotonic() + timeout
    with engine.connect() as conn:
        while time.monotonic() < deadline:
            blocked = conn.execute(
                text(
                    "select count(*) from pg_stat_activity "
                    "where datname = current_database() "
                    "and wait_event_type = 'Lock'"
                )
            ).scalar()
            conn.rollback()
            if blocked:
                return
            time.sleep(0.02)
    raise AssertionError(
        "session B never blocked on a lock within the timeout. Without the block "
        "this test degrades into two sequential inserts and cannot prove the "
        "constraint serialized concurrent bookings. Fail loudly instead."
    )


# This test exists because an application-level SELECT-then-INSERT check would
# let both of these inserts through: inside its own transaction neither session
# sees the other's uncommitted row, so both pass a "is it free?" check and both
# insert. The exclusion constraint is what makes the second insert block on a
# lock and then fail, which is why the rule lives in Postgres and not in Python.
def test_concurrent_overlapping_inserts_only_one_wins(
    committed_session_factory, reservation_factory, test_engine
):
    session_a = committed_session_factory()
    session_b = committed_session_factory()

    session_a.add(
        reservation_factory(
            room_id="3.3", check_in=date(2026, 8, 10), check_out=date(2026, 8, 15)
        )
    )
    session_a.flush()  # INSERT issued; transaction NOT yet committed

    result = {}

    def insert_b():
        session_b.add(
            reservation_factory(
                room_id="3.3", check_in=date(2026, 8, 12), check_out=date(2026, 8, 18)
            )
        )
        try:
            session_b.commit()
        except Exception as exc:  # noqa: BLE001
            result["error"] = exc

    thread = threading.Thread(target=insert_b)
    thread.start()

    # Wait until B is actually blocked before A commits, so we exercise the
    # block-then-fail path rather than winning a race.
    _wait_until_blocked(test_engine, timeout=5.0)

    session_a.commit()

    thread.join(timeout=10.0)
    assert not thread.is_alive(), "session B thread hung; the insert never unblocked"

    error = result.get("error")
    assert isinstance(error, IntegrityError)
    assert error.orig.diag.constraint_name == "no_double_booking"

    reader = committed_session_factory()
    survivors = reader.scalars(
        select(Reservation).where(Reservation.room_id == "3.3")
    ).all()
    assert len(survivors) == 1
    # The survivor must be A's booking; B is the one that lost.
    assert survivors[0].check_in == date(2026, 8, 10)
    assert survivors[0].check_out == date(2026, 8, 15)
