# SQLAlchemy engine, session factory, and the declarative Base.
#
# Base.metadata is what the models register against and what Alembic reads for
# autogenerate, so both the app and the migrations see one schema definition.
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)


def get_db():
    """FastAPI dependency yielding a session, closed when the request ends.

    Tests override this to bind requests to the test database.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
