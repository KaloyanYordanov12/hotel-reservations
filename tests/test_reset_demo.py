"""The reset guard refuses any database that is not exactly hotel_demo.

This is a pure check on the connection string, so it needs no database. It is
the safety net that keeps the 30-minute reset cron from ever wiping the real
bookings if DATABASE_URL is ever misconfigured.
"""
import pytest

from scripts.reset_demo import WrongDatabaseError, assert_demo_database


def _url(name: str) -> str:
    return f"postgresql+psycopg://user:pw@127.0.0.1:5432/{name}"


def test_guard_rejects_the_real_database_name():
    with pytest.raises(WrongDatabaseError):
        assert_demo_database(_url("hotel"))


def test_guard_rejects_the_test_database_name():
    with pytest.raises(WrongDatabaseError):
        assert_demo_database(_url("hotel_test"))


@pytest.mark.parametrize(
    "name", ["hotel", "hotel_test", "hoteldemo", "hotel_demo_2", "HOTEL_DEMO", "demo"]
)
def test_guard_rejects_anything_not_exactly_hotel_demo(name):
    # Exact, case-sensitive match. A near-miss is still a refusal.
    with pytest.raises(WrongDatabaseError):
        assert_demo_database(_url(name))


def test_guard_allows_hotel_demo():
    # The one allowed target must pass without raising.
    assert_demo_database(_url("hotel_demo"))
