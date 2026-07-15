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
copy .env.example .env      # required; local config, gitignored
pip install -r requirements.txt
```

The copied `.env` still holds placeholders, and the app refuses to start until
`SESSION_SECRET` and `APP_PASSWORD_HASH` are real. Generate both and paste each
into `.env`, replacing the placeholder:

```
python -c "import secrets; print(secrets.token_urlsafe(32))"   # paste into SESSION_SECRET
python scripts\hash_password.py                                 # paste into APP_PASSWORD_HASH
```

`COOKIE_SECURE=False` in the copied `.env` is correct for local dev. After this,
`pytest` is green and `uvicorn app.main:app --reload` serves the app.

## Dependencies

Direct dependencies live in `requirements.in`, each pinned exactly. The fully
resolved lock, including every transitive dependency, is `requirements.txt`.
Install from the lock (`pip install -r requirements.txt`), never from the `.in`.

We deliberately use plain `uvicorn`, not `uvicorn[standard]`. The `[standard]`
extra pulls in `uvloop`, a Linux-only C extension that cannot install on
Windows and forces a platform-specific lock, to speed up an event loop that is
nowhere near the bottleneck for ten rooms and one user. `watchfiles` is added
back on its own so `uvicorn --reload` works; `httptools`, `websockets`,
`pyyaml`, and `python-dotenv` are intentionally omitted.

To add or change a dependency: edit `requirements.in`, then recompile the lock
inside a Linux `python:3.13` container so it matches the VPS, not this Windows
box:

```
docker run --rm -v "${PWD}:/repo" -w /repo python:3.13 \
  bash -c "pip install pip-tools && pip-compile --no-header --output-file=requirements.txt requirements.in"
```

Then reinstall from the lock and run the tests.

The lock is compiled for Linux and therefore omits `tzdata` and `colorama`,
which only Windows needs. Installing on Windows with `pip install -r
requirements.txt` re-resolves transitive deps and pulls both in automatically:
psycopg declares `tzdata; sys_platform == "win32"`, and click declares
`colorama; platform_system == 'Windows'`. This is intended and correct. Do not
add either to `requirements.in`. Do not use `pip-sync` or `--no-deps` on
Windows: both would strip `tzdata`, and psycopg needs it to build zoneinfo for
TIMESTAMPTZ columns.

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
