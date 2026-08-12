"""Reset the demo database to a clean, populated state.

Invoked by cron on the VPS every 30 minutes (see docs/demo-reset.md for the
exact crontab line). It wipes every reservation in the demo database and reseeds
the fixed Bulgarian demo set (scripts.seed_demo.seed), so the public demo always
looks alive and anything visitors booked is cleared.

Hard safety guard: it refuses to run unless the target database is named exactly
"hotel_demo", checked BEFORE anything is wiped. This is the same spirit as the
test-suite guard in tests/conftest.py that keeps pytest from ever truncating the
real bookings. The seed itself is deliberately guard-free (the tests reuse it
against hotel_test); the guard lives here, at the one entrypoint that wipes a
real, running database on a schedule. It reads DATABASE_URL, which in the demo
deployment's env points only at hotel_demo and never references the real hotel
database.
"""
import sys

from sqlalchemy.engine import make_url

# The one database this script is ever allowed to wipe. Exact match, case
# sensitive: "hotel", "hotel_test", "HOTEL_DEMO", "hotel_demo_2" are all refused.
_REQUIRED_DATABASE = "hotel_demo"


class WrongDatabaseError(RuntimeError):
    """The target database is not the demo database, so the reset is refused."""


def assert_demo_database(database_url: str) -> None:
    """Refuse unless database_url names exactly the demo database.

    Called before any wipe, so a misconfigured DATABASE_URL, or a copy-paste of
    the real connection string, aborts loudly instead of destroying real
    bookings.
    """
    name = make_url(database_url).database
    if name != _REQUIRED_DATABASE:
        raise WrongDatabaseError(
            f"Refusing to reset: DATABASE_URL names database {name!r}, not "
            f"{_REQUIRED_DATABASE!r}. This script wipes reservations and only "
            f"ever runs against the demo database."
        )


def main() -> None:
    # Imported here, not at module top, so the guard can be tested without the
    # app config (which requires a full valid environment) being loaded.
    from app.config import settings
    from app.db import SessionLocal
    from app.models import Reservation
    from scripts.seed_demo import seed

    assert_demo_database(settings.database_url)
    with SessionLocal() as session:
        seed(session)
        session.commit()
        count = session.query(Reservation).count()
    print(f"Reset hotel_demo: {count} demo reservations.")


if __name__ == "__main__":
    try:
        main()
    except WrongDatabaseError as error:
        # Non-zero exit so a misconfigured cron run is visibly a failure in the
        # log, not a silent no-op.
        print(str(error), file=sys.stderr)
        sys.exit(1)
