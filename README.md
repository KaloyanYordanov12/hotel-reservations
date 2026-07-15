# Hotel Reservation System

Single-user reservation backend for a 10-room family hotel in Bulgaria.

## Money and dates

- All amounts are EUR. There is no currency column.
- Money is `NUMERIC(10, 2)` in the database and arrives in Python as `Decimal`, never `float`.
- Dates are `DATE`, never `TIMESTAMP`. There are no timezones in this system.

## Stack

Postgres, FastAPI, SQLAlchemy, Alembic, pytest.

Postgres is required. The no-double-booking rule is enforced by a Postgres exclusion constraint, not by application code, so SQLite is not an option.

## Local setup

Python is pinned to 3.13. This machine also has 3.14 on PATH, so the venv must be created explicitly with the 3.13 launcher or you will silently get 3.14.

```
py -3.13 -m venv venv
venv\Scripts\activate
python --version            # must report 3.13.x
pip install -r requirements.txt
```

## Database

The dev database runs in Docker Compose. Tests use a separate database name on the same server.

```
docker compose up -d
```

## Run

```
uvicorn app.main:app --reload
```

`GET /health` returns `{"status": "ok"}`.

## Test

```
pytest
```
