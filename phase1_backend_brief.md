# Hotel Reservations - Phase 1 Brief: Backend Foundation

## Standing rules for this brief

- This project uses NO AI APIs. There is no Anthropic API key, no OpenAI key, nothing. If you find yourself wanting one, you have misread the scope.
- No em-dashes in any file you write. Code, comments, docs, commit messages.
- One commit per step. Tests must pass before every commit. Do not batch steps into one commit.
- Do not push until I say so. Commit locally, tell me what you committed.
- Never commit secrets. `.env` is gitignored, `.env.example` is committed with placeholder values.
- Stop at the end of each step and report. Do not chain steps without me saying go.
- If a step turns out to be wrong or blocked, stop and say so. Do not improvise around it.

## Decisions already made (do not relitigate)

- Postgres, not SQLite. The reason is the exclusion constraint in Step 4. That is the whole reason. Do not suggest SQLite.
- Dates are `DATE`, never `TIMESTAMP`. No timezones anywhere in this system.
- Money is `NUMERIC(10, 2)` and must arrive in Python as `Decimal`, never `float`. All amounts are in EUR. Note this in the README, no currency column.
- **No `total_price` column.** My mother knows every price by heart, so the app would hold no information she lacks. An optional price field would get filled in sometimes and not others, and a half-populated field is worse than no field because it looks like data you can rely on. Deposit is just a number she records.
- **`note`: nullable `Text`.** The notebook has margins. This is the margins. Never validated, never parsed, never required. It is where the negotiated price, the late arrival, the dog, and everything else we failed to anticipate goes.
- No EGN. No guest table. No booking history. Reservations are a flat table.
- Single shared password auth, in this phase, not later.
- **Python 3.13, not 3.14.** This machine has both. 3.14 is the default on PATH, so you must create the venv explicitly with `py -3.13 -m venv venv` or you will silently get 3.14. Verify with `python --version` after activating and paste the output. 3.14 buys this project nothing and risks source builds for psycopg, bcrypt, and pydantic-core on Windows, which is an afternoon lost to build toolchains rather than to the constraint in Step 4. Do not argue for 3.14 on the grounds that the wheels probably exist by now.

---

## Step 0: Recon report. NO CODE.

Read whatever exists and report. Write nothing, install nothing, create no files.

Report on:

1. What is in this repo right now? Full tree, and the contents of any config files.
2. Python version available.
3. Is Docker Desktop installed and running on this machine? Run `docker --version` and `docker compose version`.
4. Is a Postgres server already reachable locally? Check for a local install and for any running containers.
5. Is there a git repo, and what is the current branch and status?

Then stop. I will confirm before you write anything.

The Docker question matters: the tests in Step 4 cannot run against SQLite, so we need a real Postgres for the test suite. Docker Compose is the default plan. If Docker is unavailable, say so and stop rather than picking an alternative yourself.

---

## Step 1: Project skeleton

Structure:

```
/
  docker-compose.yml       (postgres for local dev and test)
  pyproject.toml           (or requirements.txt, your call, one of them)
  .env.example
  .gitignore
  README.md
  alembic.ini
  /alembic
    /versions
  /app
    __init__.py
    main.py                (FastAPI app)
    config.py              (settings from env)
    db.py                  (engine, session)
    models.py
    schemas.py
    /routers
      __init__.py
  /tests
    conftest.py
    test_health.py
```

Deliverables:

- `docker-compose.yml` with one Postgres service, port mapped, named volume. A single database is fine for dev; tests will use a separate database name on the same server.
- FastAPI app with one endpoint: `GET /health` returning `{"status": "ok"}`.
- pytest configured. One test hitting `/health` and asserting 200.
- `.env.example` with `DATABASE_URL`, `TEST_DATABASE_URL`, `SESSION_SECRET`, `APP_PASSWORD_HASH` as placeholders.
- `.gitignore` covering `.env`, `__pycache__`, `.pytest_cache`, `venv`, `node_modules`.

Done when: `py -3.13 -m venv venv` has produced a venv that reports 3.13 on activation, `docker compose up -d` brings up Postgres, `pytest` passes with one test, `uvicorn app.main:app --reload` serves `/health`.

Commit: `chore: project skeleton with FastAPI, pytest, and Postgres compose`

---

## Step 2: Models and first migration

Two SQLAlchemy models.

`rooms`:
- `id`: `String`, primary key. Values are `"3.3"`, `"A11"`, etc. Natural key, not a surrogate.
- `type`: enum of `double`, `triple`, `apartment`, `studio`. Use a Postgres native enum via SQLAlchemy `Enum`.
- `standard_occupancy`: `Integer`, not null. NOT named `capacity`. See Step 5, and the note under the seed table.

`reservations`:
- `id`: `UUID`, primary key, server default `gen_random_uuid()`.
- `room_id`: `String`, FK to `rooms.id`, not null, indexed.
- `guest_name`: `String`, not null.
- `guest_phone`: `String`, not null.
- `check_in`: `Date`, not null.
- `check_out`: `Date`, not null.
- `num_guests`: `Integer`, not null.
- `parking`: `Boolean`, not null, default false.
- `deposit_paid`: `Numeric(10, 2)`, not null, default 0.
- `note`: `Text`, nullable.
- `created_at`: `TIMESTAMPTZ`, not null, server default now.
- `updated_at`: `TIMESTAMPTZ`, not null, server default now, updated on write.

`deposit_paid` must round-trip as `Decimal`. Write a test that asserts the type coming back from the database is `Decimal`, not `float`. This is a real trap and I want it caught by a test, not by me in production.

Alembic:
- `alembic init`, wired to read `DATABASE_URL` from env, and to use the models' metadata for autogenerate.
- One migration creating both tables.
- A second, separate migration that seeds the 10 rooms as data:

| id | type | standard_occupancy |
|----|------|--------------------|
| 3.3 | double | 2 |
| 3.4 | double | 2 |
| 4.3 | double | 2 |
| 4.4 | double | 2 |
| 3.2 | triple | 3 |
| 4.2 | triple | 3 |
| A3 | apartment | 4 |
| A11 | apartment | 4 |
| 4.1 | studio | 4 |
| A8 | studio | 4 |

These numbers are confirmed. The BLOCKER on this step is lifted. Seed exactly these values and do not adjust them.

The column is `standard_occupancy`, NOT `capacity`. This is deliberate and is not a style preference. My mother routinely puts more people in a room than it is intended for, and the system must never make that awkward for her. `capacity` is a word that means "limit", and a limit is a thing future readers of this code will feel an urge to enforce. `standard_occupancy` means "how many normally sleep here", which is descriptive and enforces nothing. The name is the last place the old assumption can hide.

It appears nowhere except this seed migration and in read responses for display. It appears in no rejection path anywhere in this system. See Step 5.

Done when: `alembic upgrade head` on an empty database produces both tables and 10 seeded rooms. `alembic downgrade base` cleanly reverses. Test asserting 10 rooms exist and that a Decimal round-trips.

Commit: `feat: room and reservation models with Alembic migrations and room seed`

---

## Step 3: Test harness against real Postgres

Before the constraint work, the test harness has to be right, because Step 4 depends on it.

- `conftest.py` creates the test database if absent, runs `alembic upgrade head` against it once per session, and drops or truncates between tests.
- Default isolation: each test runs inside a transaction that is rolled back at teardown. Fast and clean.
- Provide a SECOND fixture, separate, that gives real committed sessions with explicit cleanup. Step 4's concurrency test needs two independent connections and therefore cannot live inside a single rolled-back transaction. Do not try to make one fixture serve both.
- A factory helper for building reservations with sensible defaults so tests read as one line each.

Done when: both fixtures exist, are documented with a short comment explaining why there are two, and a smoke test uses each.

Commit: `test: Postgres test harness with transactional and committed session fixtures`

---

## Step 4: The exclusion constraint. THE CORE OF THE PROJECT.

This is the most important step in the whole system. Slow down here.

TDD, strictly. Write the full test matrix FIRST. Run it. Watch it fail. Then write the migration. Then watch it pass. Show me the red output before you write the migration.

### The tests, written first

Baseline in every case: an existing reservation for room `3.3`, `2026-08-10` to `2026-08-15`. Parametrize.

| # | New reservation | Room | Expected |
|---|-----------------|------|----------|
| 1 | 08-10 to 08-15 | 3.3 | REJECT, identical |
| 2 | 08-11 to 08-14 | 3.3 | REJECT, fully inside |
| 3 | 08-08 to 08-18 | 3.3 | REJECT, fully contains |
| 4 | 08-08 to 08-12 | 3.3 | REJECT, overlaps start |
| 5 | 08-13 to 08-18 | 3.3 | REJECT, overlaps end |
| 6 | 08-05 to 08-10 | 3.3 | ALLOW, same-day turnover, new checkout equals existing checkin |
| 7 | 08-15 to 08-20 | 3.3 | ALLOW, same-day turnover, new checkin equals existing checkout |
| 8 | 08-01 to 08-05 | 3.3 | ALLOW, entirely before |
| 9 | 08-20 to 08-25 | 3.3 | ALLOW, entirely after |
| 10 | 08-10 to 08-15 | 4.4 | ALLOW, different room, identical dates |
| 11 | 08-10 to 08-10 | 3.3 | REJECT, zero-night stay, CHECK constraint |
| 12 | 08-15 to 08-10 | 3.3 | REJECT, inverted dates, CHECK constraint |

Cases 6 and 7 are the ones that will be got wrong. They must pass.

Two more tests, separate from the matrix:

**Self-update.** Take the existing reservation and update it to `08-11` to `08-16`. It must succeed. A row must not conflict with its own previous version.

**Update into a conflict.** Add a second reservation for room `3.3` at `08-20` to `08-25`. Now try to update the first one to `08-10` to `08-22`. Must be rejected.

**Concurrency.** This is the test that proves the point, and it must use the committed-session fixture from Step 3.

- Open session A and session B on separate connections.
- Session A: `INSERT` room `3.3`, `08-10` to `08-15`. Do not commit.
- Session B, on a background thread: `INSERT` room `3.3`, `08-12` to `08-18`. This will BLOCK. That is correct and expected behaviour, the exclusion constraint takes a lock.
- Session A: commit.
- Session B unblocks and must raise `IntegrityError`.
- Join the thread. Assert exactly one row exists for room `3.3`.
- Put a generous timeout on the join so a hang fails the test instead of freezing the suite.

Add a comment above this test explaining in two sentences why it exists: an application-level `SELECT` then `INSERT` check would let both of these through, and the constraint is what makes that impossible.

### The migration, written second

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE reservations
  ADD CONSTRAINT valid_dates
  CHECK (check_out > check_in);

ALTER TABLE reservations
  ADD CONSTRAINT no_double_booking
  EXCLUDE USING gist (
    room_id WITH =,
    daterange(check_in, check_out, '[)') WITH &&
  );
```

Notes:
- `btree_gist` is required because `room_id` is compared with `=`, and plain GiST has no operator class for scalar equality on text.
- `'[)'` is half-open: check-in inclusive, check-out exclusive. That is exactly the rule `A < D AND B > C`, and it is what makes same-day turnover legal. Do not use `'[]'`.
- Write a proper `downgrade()` that drops both constraints.
- Do not add a redundant Python-side overlap check in this step. Step 5 catches the database error and translates it. The database is the source of truth, in one place.

Done when: every test above passes, and the red-then-green transition is in your report.

Commit: `feat: enforce no double-booking with Postgres exclusion constraint`

---

## Step 5: Reservations CRUD

Pydantic schemas: `ReservationCreate`, `ReservationUpdate` (all fields optional), `ReservationRead`.

### Validation philosophy. Read this before writing a single validator.

The system this replaces is a paper notebook. A notebook never argues. The moment this app tells my mother "no" about something she has decided is fine, while she is on the phone with a guest, she closes it and goes back to the notebook and never opens it again.

So: **reject only what is physically impossible or is unambiguously a typo. Never reject a judgement call.**

Physically impossible, so reject:
- Two guests in the same room on the same night. Handled by the constraint in Step 4.
- `check_out <= check_in`. Time does not run backwards.

Unambiguously a typo, so reject:
- `num_guests < 1`. A reservation for zero people is a slip of the thumb, not a decision.
- `deposit_paid < 0`. Negative money was not paid.
- `room_id` that does not exist. 404.

Everything else is HERS TO DECIDE. Specifically:

- **Do NOT validate `num_guests` against `rooms.standard_occupancy`.** She regularly puts more people in a room than it is intended for, when the guests are happy with it, and she must have no trouble doing it. `standard_occupancy` is a display value, nothing more. There is no code path anywhere in this system where it causes a rejection, a warning, or a confirmation dialog.
- **Do NOT add a `total_price` column and then validate against it.** There is no such column. See the decisions section.
- **Do NOT validate, parse, length-limit, or interpret `note`.** It is free text. That is the entire point of it.

If you find yourself writing a validator, ask: is this physically impossible, or am I just surprised? If you are only surprised, do not write it.

Endpoints:
- `POST /api/reservations` -> 201
- `GET /api/reservations` -> list, with optional `from` and `to` date filters, ordered by `check_in`
- `GET /api/reservations/{id}` -> 200 or 404
- `PATCH /api/reservations/{id}` -> 200, 404, or 409
- `DELETE /api/reservations/{id}` -> 204 or 404

Conflict handling. Catch `IntegrityError`, inspect the constraint name:
- `no_double_booking` -> 409 with a body naming the room and the dates that clash. Run a follow-up query to find the offending reservation so the message is useful. My mother needs to read this on a phone and understand it.
- `valid_dates` -> 422.

Do not let a raw 500 escape for either.

Add a `deposit_paid=false` style filter to the list endpoint so "who still owes a deposit" is one request. Derived from `deposit_paid = 0`, not a stored column.

Tests for every endpoint: happy path, 404, 409, and validation failures.

Commit: `feat: reservations CRUD API with conflict handling`

---

## Step 6: Availability endpoint

`GET /api/availability?check_in=2026-08-10&check_out=2026-08-15`

Returns every room with a free/booked flag, and for booked ones the reservation that blocks it. This is the endpoint my mother's primary screen calls while she is on the phone with a guest, so it is one request and no N+1.

Single query. Left join rooms against reservations overlapping the requested range, using the same half-open range logic as the constraint so the two can never disagree.

Also: `GET /api/availability/grid?from=&to=` returning the room-by-day matrix for the laptop calendar view. Same underlying query, different shape. Build it now, the frontend will want it.

Tests: all rooms free on an empty range, a booked room correctly flagged, same-day turnover shows the room as free, `standard_occupancy` and type present in the response.

Commit: `feat: availability endpoint with single-query room status`

---

## Step 7: Auth

Single shared password. Not a user table, not OAuth, not JWT.

- `APP_PASSWORD_HASH` in env, argon2 or bcrypt. Write a small script to generate the hash, do not make me do it by hand.
- `POST /api/login` takes a password, sets a signed session cookie on success, 401 on failure. Rate limit it, five attempts per minute per IP, in-memory is fine.
- Cookie: HttpOnly, SameSite=Lax, `max_age` of 180 days. She logs in once on her phone and never again. This is the whole point, do not shorten it.
- The `Secure` flag is CONDITIONAL. Drive it from a `COOKIE_SECURE` setting in `config.py`, defaulting to `True`, set to `False` in `.env` for dev and in the test fixtures.

  Why, because this will waste an hour if you do not know it: httpx honours the `Secure` attribute in its cookie jar. FastAPI's `TestClient` runs against `http://testserver`, which is not localhost and is not a trustworthy origin. A `Secure` cookie will be accepted and stored by the test client and then silently NOT sent on the next request. Your login test passes, and every authenticated test after it returns 401 for no visible reason. The bug does not reproduce in a browser, because Chrome and Firefox do treat `http://localhost` as trustworthy and send the cookie fine. So it looks like the tests are broken rather than the config.

  Assert this. One test that logs in with `COOKIE_SECURE=False` and confirms the cookie comes back on the following request. And add a comment on the setting saying it must be `True` in production, so nobody deletes the conditional later after finding it "works fine on localhost".
- `POST /api/logout` clears it.
- Dependency that guards every `/api/*` route except `/health` and `/api/login`.
- Tests: unauthenticated request to a protected route is 401, login then request succeeds, bad password is 401.

Commit: `feat: single-password session auth`

---

## Step 8: Deploy the backend to the real URL

Backend only. No frontend yet. The point is to find deployment problems now, not in three weeks.

Target: the existing Hetzner VPS, same pattern as Agent Central. Postgres on the box, systemd unit for uvicorn, Cloudflare tunnel to a subdomain.

READ THIS BEFORE ANYTHING ELSE IN THIS STEP. That VPS is not empty. It already runs Agent Central, live at `agentcentral.kaloyanyordanov.dev`, and that is my portfolio piece. It is the thing recruiters open. Taking it down while wiring up a booking app for my mother would be the most expensive mistake available in this entire project, and it is available right here, in this step, because we are about to install a database and edit a tunnel config on a machine that is currently serving it.

Rules for this step:
- ADD ONLY. Never modify, restart, or reconfigure an existing service, unit, or tunnel route. If the task appears to require it, STOP and tell me.
- Back up the cloudflared config before touching it. Show me the backup path.
- Report free RAM and free disk before installing anything. Agent Central runs ChromaDB and is not memory-free.
- After every VPS command that could plausibly affect it, verify Agent Central still answers, and say so.
- The runbook must include a rollback that returns the box to its current state.

FIRST: check what Python and what Postgres the VPS actually has. Local dev is pinned to Python 3.13 and runs `postgres:16` in Compose, the app ships as a venv under systemd rather than a container, so a mismatch in either surfaces here. Report both versions and stop if either differs. Do not silently retarget the pin, and do not silently accept a Postgres major that you have not run the Step 4 test matrix against. The exclusion constraint and `btree_gist` are old and stable, so a mismatch is unlikely to break, but "unlikely to break" is not something I want discovered on the box holding my mother's bookings.

Write, do not run:

- **The systemd unit file.** uvicorn binds to `127.0.0.1` and nothing else. Never `0.0.0.0`. cloudflared connects to it locally, so there is no reason for the app to be reachable on the public IP, and one strong reason against: `Secure` on the session cookie is enforced by browsers, not by servers. Anyone with curl and the box's IP could log in over plain HTTP and pass the session cookie back by hand, in cleartext, straight past the tunnel and past HTTPS. Bind local, and the tunnel is the only door.
- A short deploy runbook in `docs/deploy.md`: exact commands, in order.
- `docs/backup.md` plus a `pg_dump` script and the cron line. Nightly dump, gzipped, timestamped, keep 14 days, and a documented restore command that I have actually tested once. This is my mother's business data.

  **The dump must be copied off the box.** A gzip sitting on the same disk as the database it came from is not a backup, it is a second copy of the same failure. It protects against the likelier accidents (a bad migration, deleted rows, my own mistake at 1am) and against nothing else. If the VPS dies, an on-box dump dies with it, and the hotel loses every forward booking it has.

  Do not pick the destination yourself. Report what the VPS can already reach and what it would cost, and stop. I decide where it goes.

Then stop and hand me the runbook. I run it on the VPS myself.

Done when: `/health` answers over HTTPS on the real domain, login works from my phone, the app is not reachable on the VPS public IP, and I have restored a dump into a scratch database at least once.

Commit: `chore: deployment runbook, systemd unit, and backup script`

---

## Out of scope for Phase 1. Do not build these.

- Any frontend. No React, no templates, no HTML.
- Guest-facing anything.
- Notifications of any kind.
- Analytics, reporting, occupancy stats.
- Multi-user, roles, permissions.
- Payment processing.
- Caching. There are 10 rooms.
- Docker for the app itself. Compose is for the dev database only.

## Report format for each step

1. What you read before writing anything.
2. What you changed, file by file.
3. Test output, pasted.
4. The commit hash and message.
5. Anything you found that this brief got wrong.

Then stop.
