# Settings loaded from the environment.
#
# The defaults match the local docker-compose Postgres described in
# .env.example, so the app and the test suite run without a committed .env file.
# In production, DATABASE_URL and TEST_DATABASE_URL arrive as real environment
# variables (or a .env) and override these defaults. Cookie and auth settings
# arrive in Step 7.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://hotel:hotel@localhost:5432/hotel"
    test_database_url: str = (
        "postgresql+psycopg://hotel:hotel@localhost:5432/hotel_test"
    )


settings = Settings()
