import bcrypt
import pytest
from pydantic import ValidationError

from app.config import _PLACEHOLDER_HASH, _PLACEHOLDER_SECRET, Settings


def _env_example_values() -> dict[str, str]:
    values = {}
    with open(".env.example", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def test_placeholder_guards_match_env_example():
    """The guards in config.py hardcode the .env.example placeholder strings. If
    the example ever changes and this copy does not, the guard silently stops
    guarding, so pin them together here."""
    values = _env_example_values()
    assert _PLACEHOLDER_SECRET == values["SESSION_SECRET"]
    assert _PLACEHOLDER_HASH == values["APP_PASSWORD_HASH"]

# A fully valid config. Individual tests override one field to a bad value and
# assert startup rejects it. rounds=4 keeps the probe hash cheap.
_VALID = dict(
    database_url="postgresql+psycopg://u:p@localhost:5432/db",
    test_database_url="postgresql+psycopg://u:p@localhost:5432/db_test",
    session_secret="x" * 40,
    app_password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt(rounds=4)).decode(),
    cookie_secure=False,
)


def _build(**overrides):
    return Settings(**{**_VALID, **overrides})


def test_valid_config_is_accepted():
    _build()  # must not raise


def test_rejects_placeholder_session_secret():
    with pytest.raises(ValidationError):
        _build(session_secret="replace-with-a-long-random-string")


def test_rejects_too_short_session_secret():
    with pytest.raises(ValidationError):
        _build(session_secret="short")


def test_rejects_placeholder_password_hash():
    with pytest.raises(ValidationError):
        _build(app_password_hash="replace-with-an-argon2-or-bcrypt-hash")


def test_rejects_malformed_password_hash():
    with pytest.raises(ValidationError):
        _build(app_password_hash="not-a-real-bcrypt-hash")
