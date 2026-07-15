from datetime import date

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import Reservation


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def api_client(test_engine):
    """A TestClient whose requests hit the test database with real commits.

    Overrides the get_db dependency so the API runs against hotel_test rather
    than the dev database, and truncates reservations afterward. Real commits are
    used (not a rolled-back transaction) so the conflict path can recover from an
    IntegrityError and run its follow-up query exactly as it will in production.
    """
    maker = sessionmaker(bind=test_engine, future=True)

    def override_get_db():
        session = maker()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        with test_engine.begin() as conn:
            conn.execute(text("TRUNCATE reservations"))


def _ensure_test_database() -> None:
    """Create the test database if it does not exist.

    You cannot create a database from a connection to the database being
    created, so connect to the server's default 'postgres' database to do it.
    """
    url = make_url(settings.test_database_url)
    admin_engine = create_engine(
        url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("select 1 from pg_database where datname = :name"),
            {"name": url.database},
        ).scalar()
        if not exists:
            conn.execute(text(f'create database "{url.database}"'))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def test_engine():
    """A test database with all migrations applied, built once per session.

    Creates the database if absent and runs ``alembic upgrade head`` against it,
    so tests run against exactly the schema the migrations produce, seeded rooms
    included.
    """
    _ensure_test_database()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(settings.test_database_url, future=True)
    yield engine
    engine.dispose()


# There are two session fixtures on purpose, and they are not interchangeable.
#
# db_session (below) is the default. Each test runs inside a single transaction
# on one connection that is rolled back at teardown, so tests are fast and leave
# no trace. But everything happens on one connection, so it cannot show one
# connection what another connection has committed.
#
# committed_session_factory is the exception for exactly that case. Step 4's
# concurrency test needs two independent connections that can see each other's
# committed work, which is impossible inside a single rolled-back transaction.
# So that fixture commits for real and cleans up by truncating afterward. Do not
# try to fold these two into one; the isolation models are opposites.


@pytest.fixture
def db_session(test_engine):
    """Default fixture: a session whose writes are rolled back after each test.

    The session is bound to a connection with an outer transaction that teardown
    rolls back. ``join_transaction_mode="create_savepoint"`` means a test may
    call ``commit()`` and still be undone: its commit lands on a savepoint, not
    the real transaction.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def committed_session_factory(test_engine):
    """Real committed sessions on independent connections, cleaned up by truncate.

    Call it to get a fresh session; call it again for a second, independent
    connection. Commits here actually persist, which is what lets two connections
    see each other (the Step 4 concurrency test). Because the writes are real,
    rollback cannot undo them, so teardown truncates the reservations table. The
    seeded rooms are left alone.
    """
    maker = sessionmaker(bind=test_engine, future=True)
    created: list[Session] = []

    def _make() -> Session:
        session = maker()
        created.append(session)
        return session

    try:
        yield _make
    finally:
        for session in created:
            session.close()
        with test_engine.begin() as conn:
            conn.execute(text("TRUNCATE reservations"))


@pytest.fixture
def reservation_factory():
    """Build a Reservation with sensible defaults so a test reads as one line.

    Returns an unsaved instance; the caller adds it to whichever session it is
    testing. Override any field via keyword argument.
    """

    def _make(**overrides) -> Reservation:
        values = dict(
            room_id="3.3",
            guest_name="Test Guest",
            guest_phone="+359888000000",
            check_in=date(2026, 8, 10),
            check_out=date(2026, 8, 15),
            num_guests=2,
        )
        values.update(overrides)
        return Reservation(**values)

    return _make
