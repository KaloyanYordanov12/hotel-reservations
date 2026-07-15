from datetime import date

from sqlalchemy import text

from app.models import Reservation


def test_db_session_rolls_back_and_isolates(db_session, reservation_factory, test_engine):
    """The transactional fixture keeps a test's writes off every other connection.

    We even commit inside the session; because the fixture joins the transaction
    with a savepoint, an independent connection still sees nothing, which is what
    teardown then rolls back.
    """
    db_session.add(reservation_factory())
    db_session.commit()
    assert db_session.query(Reservation).count() == 1

    with test_engine.connect() as other_connection:
        visible = other_connection.execute(
            text("select count(*) from reservations")
        ).scalar()
    assert visible == 0


def test_committed_session_visible_across_connections(
    committed_session_factory, reservation_factory
):
    """The committed fixture makes one connection's writes visible to another."""
    writer = committed_session_factory()
    writer.add(reservation_factory(check_in=date(2026, 9, 1), check_out=date(2026, 9, 3)))
    writer.commit()

    reader = committed_session_factory()
    assert reader.query(Reservation).count() == 1
