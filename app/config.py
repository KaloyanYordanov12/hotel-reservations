# Settings loaded from the environment.
#
# There are no defaults. DATABASE_URL and TEST_DATABASE_URL are required, so a
# missing value raises at startup instead of silently connecting to localhost.
# On the VPS, a systemd unit whose EnvironmentFile is missing must crash rather
# than boot against the wrong database. For local dev, copy .env.example to .env
# (see README). Real environment variables take precedence over .env. Cookie and
# auth settings arrive in Step 7.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    test_database_url: str


settings = Settings()
