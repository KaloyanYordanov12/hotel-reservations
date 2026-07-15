import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


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
    """A test database with all migrations applied, as an Engine.

    This is deliberately minimal: Step 2 only needs a real Postgres to prove the
    schema migrates and that Decimal round-trips. Step 3 builds the full harness
    (a transactional-rollback fixture, a separate committed-session fixture, and
    a reservation factory). Do not grow this into that here.
    """
    _ensure_test_database()
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", settings.test_database_url)
    command.upgrade(alembic_cfg, "head")
    engine = create_engine(settings.test_database_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    """A session whose work is rolled back at the end of each test."""
    Session = sessionmaker(bind=test_engine, future=True)
    session = Session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
