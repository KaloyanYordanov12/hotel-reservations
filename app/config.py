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
_PLACEHOLDER_HASH = "replace-with-a-bcrypt-hash"
_MIN_SECRET_LENGTH = 32

# The only strings that turn demo mode ON. Case-insensitive, whitespace-trimmed.
# Everything else (unset, "0", "false", "", "banana") is OFF. See demo_mode.
_DEMO_TRUE_VALUES = {"1", "true", "yes"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    # Test-only, and must NOT exist in production. pytest ships in the venv and
    # the suite truncates tables, so a production box carrying a TEST_DATABASE_URL
    # is one copy-paste away from wiping real bookings. It defaults to None so
    # production simply does not have it; the test harness refuses to run unless
    # it is set to an obviously-separate test database (see tests/conftest.py).
    test_database_url: str | None = None
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

    # OFF unless an operator explicitly turns it on, exactly like cookie_secure
    # is a fail-secure boolean. The SAME codebase runs my mother's real app and
    # the public demo; a mistake here must never strip auth off the real one.
    # So the default is False, and _parse_demo_mode below only returns True for
    # a small set of explicit true tokens ("1"/"true"/"yes"). Every other value,
    # including an unset var, a "0", a "false", an empty string, or garbage,
    # resolves to False. Unset = secure = auth on. Only a deliberate DEMO_MODE=1
    # (set in the demo deployment's env, never the real one) disables the login
    # wall, and it does so in require_authenticated, not by touching any other
    # auth logic.
    demo_mode: bool = False

    @field_validator("demo_mode", mode="before")
    @classmethod
    def _parse_demo_mode(cls, value: object) -> bool:
        # mode="before" runs on the raw env string ahead of bool coercion, so a
        # value pydantic would otherwise reject (e.g. "banana") cannot raise and
        # take the app down; it simply reads as OFF. An unset var uses the field
        # default (False) and never reaches here, which is also OFF.
        if value is None:
            return False
        return str(value).strip().lower() in _DEMO_TRUE_VALUES

    # The exact origin(s) the demo frontend (a separate Cloudflare Pages project on
    # its own origin) is served from, so the demo backend can answer its
    # cross-origin API calls. Comma-separated for more than one. Consulted ONLY in
    # demo mode (see main.py); the real app never reads it and its CORS posture is
    # unchanged. Empty by default, so demo mode without it grants no cross-origin
    # access.
    demo_frontend_origin: str = ""

    @property
    def demo_allowed_origins(self) -> list[str]:
        """The configured demo frontend origins, split and cleaned. Empty when
        unset, which is the fail-secure default: no cross-origin access granted."""
        return [o.strip() for o in self.demo_frontend_origin.split(",") if o.strip()]

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
