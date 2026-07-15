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

# label, room, check_in, check_out, expect_reject
MATRIX = [
    ("identical", "3.3", date(2026, 8, 10), date(2026, 8, 15), True),
    ("fully_inside", "3.3", date(2026, 8, 11), date(2026, 8, 14), True),
    ("fully_contains", "3.3", date(2026, 8, 8), date(2026, 8, 18), True),
    ("overlaps_start", "3.3", date(2026, 8, 8), date(2026, 8, 12), True),
    ("overlaps_end", "3.3", date(2026, 8, 13), date(2026, 8, 18), True),
    ("turnover_new_checkout_eq_existing_checkin", "3.3", date(2026, 8, 5), date(2026, 8, 10), False),
    ("turnover_new_checkin_eq_existing_checkout", "3.3", date(2026, 8, 15), date(2026, 8, 20), False),
    ("entirely_before", "3.3", date(2026, 8, 1), date(2026, 8, 5), False),
    ("entirely_after", "3.3", date(2026, 8, 20), date(2026, 8, 25), False),
    ("different_room_same_dates", "4.4", date(2026, 8, 10), date(2026, 8, 15), False),
    ("zero_night_stay", "3.3", date(2026, 8, 10), date(2026, 8, 10), True),
    ("inverted_dates", "3.3", date(2026, 8, 15), date(2026, 8, 10), True),
]


@pytest.mark.parametrize(
    "label,room,check_in,check_out,reject",
    MATRIX,
    ids=[row[0] for row in MATRIX],
)
def test_overlap_matrix(
    db_session, reservation_factory, label, room, check_in, check_out, reject
):
    db_session.add(reservation_factory(**BASELINE))
    db_session.flush()

    db_session.add(
        reservation_factory(room_id=room, check_in=check_in, check_out=check_out)
    )
    if reject:
        with pytest.raises(IntegrityError):
            db_session.flush()
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
    with pytest.raises(IntegrityError):
        db_session.flush()


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
    assert isinstance(result.get("error"), IntegrityError)

    reader = committed_session_factory()
    remaining = reader.scalar(
        select(func.count())
        .select_from(Reservation)
        .where(Reservation.room_id == "3.3")
    )
    assert remaining == 1
