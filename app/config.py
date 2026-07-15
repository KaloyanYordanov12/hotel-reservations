# Settings loaded from the environment.
#
# Values are required and have no fallback, so a missing one raises at startup
# instead of running against the wrong thing. On the VPS, a systemd unit whose
# EnvironmentFile is missing must crash rather than boot silently. For local dev,
# copy .env.example to .env (see README). Real environment variables take
# precedence over .env.
#
# The one allowed default is COOKIE_SECURE, because its default is the safe one:
# an unset value fails secure. See the note on that field.
from pydantic_settings import BaseSettings, SettingsConfigDict


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


settings = Settings()
