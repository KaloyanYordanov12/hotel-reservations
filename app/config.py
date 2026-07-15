# Settings loaded from the environment.
#
# Values are required and have no fallback, so a missing one raises at startup
# instead of running against the wrong thing. On the VPS, a systemd unit whose
# EnvironmentFile is missing must crash rather than boot silently. For local dev,
# copy .env.example to .env (see README) and set real values. Real environment
# variables take precedence over .env.
#
# The auth settings are validated here, not just required, because this repo is
# public: the .env.example placeholders are published strings. A shipped
# placeholder SESSION_SECRET would let anyone forge a signed session cookie, and
# a placeholder APP_PASSWORD_HASH would boot an app nobody can log into while
# blaming my mother's typing. Both must refuse to start, the same way the
# database_url default was removed in Step 2.
#
# The one allowed default is COOKIE_SECURE, because its default is the safe one:
# an unset value fails secure. See the note on that field.
import bcrypt
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRET = "replace-with-a-long-random-string"
_PLACEHOLDER_HASH = "replace-with-an-argon2-or-bcrypt-hash"
_MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str
    session_secret: str
    app_password_hash: str

    # MUST be True in production. It is the Secure attribute on the session
    # cookie, so over plain HTTP the browser never sends the cookie back. It is
    # set False only in local .env and in tests, because the TestClient runs over
    # http://testserver, which httpx does not treat as a trustworthy origin, so a
    # Secure cookie would be stored and then silently never sent, making every
    # authenticated test 401 for no visible reason. Defaulting True means an unset
    # value fails secure. Do not delete this conditional after finding it "works
    # fine on localhost".
    cookie_secure: bool = True

    @field_validator("session_secret")
    @classmethod
    def _reject_weak_secret(cls, value: str) -> str:
        if value == _PLACEHOLDER_SECRET:
            raise ValueError(
                "SESSION_SECRET is still the .env.example placeholder. Anyone "
                "reading this public repo could forge a session. Generate one: "
                'python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        if len(value) < _MIN_SECRET_LENGTH:
            raise ValueError(
                f"SESSION_SECRET must be at least {_MIN_SECRET_LENGTH} characters. "
                'Generate one: python -c "import secrets; print(secrets.token_urlsafe(32))"'
            )
        return value

    @field_validator("app_password_hash")
    @classmethod
    def _reject_unusable_hash(cls, value: str) -> str:
        if value == _PLACEHOLDER_HASH:
            raise ValueError(
                "APP_PASSWORD_HASH is still the .env.example placeholder, so no "
                "password could ever match. Generate one: python scripts/hash_password.py"
            )
        # Prove it is a parseable bcrypt hash by actually running one checkpw. A
        # malformed hash raises ValueError; catch it and refuse to start rather
        # than boot an app where every login fails. One bcrypt round at boot is
        # a fine price.
        try:
            bcrypt.checkpw(b"probe", value.encode())
        except ValueError:
            raise ValueError(
                "APP_PASSWORD_HASH is not a valid bcrypt hash. Generate one: "
                "python scripts/hash_password.py"
            )
        return value


settings = Settings()
