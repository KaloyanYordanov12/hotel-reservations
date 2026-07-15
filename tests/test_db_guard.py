import pytest

from tests.conftest import _check_test_database_is_safe

_PROD = "postgresql+psycopg://u:p@localhost:5432/hotel"


def test_rejects_same_database_name_as_production():
    with pytest.raises(pytest.UsageError):
        _check_test_database_is_safe(
            _PROD, "postgresql+psycopg://u:p@localhost:5432/hotel"
        )


def test_rejects_name_without_test_suffix():
    with pytest.raises(pytest.UsageError):
        _check_test_database_is_safe(
            _PROD, "postgresql+psycopg://u:p@localhost:5432/hotel_scratch"
        )


def test_rejects_unset_test_database_url():
    with pytest.raises(pytest.UsageError):
        _check_test_database_is_safe(_PROD, None)


def test_accepts_a_distinct_test_database():
    # Must not raise.
    _check_test_database_is_safe(
        _PROD, "postgresql+psycopg://u:p@localhost:5432/hotel_test"
    )
