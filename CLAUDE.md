# Hotel Reservation System

Single-user reservation system for my family's 10-room hotel in Bulgaria. The only user is my mother. She uses it on her phone, often mid-call with a guest, sometimes in a car.

## How we work

- `phase1_backend_brief.md` is the source of truth for scope and order. Work only from it.
- Execute ONE step per session. Stop at the end of that step and report. Do not begin the next step.
- Before writing anything, read what already exists and report what you found.
- One commit per step. Tests pass before every commit.
- YOU MUST NOT run `git push`. I push. Commit locally and give me the hash.
- If the brief is wrong, blocked, or contradicts what you find in the code, STOP and say so. Do not improvise around it.

## Hard rules

- YOU MUST NOT use em-dashes anywhere. Code, comments, docs, commit messages, chat.
- This project uses NO AI APIs. No Anthropic key, no OpenAI key, no LLM calls of any kind. If you find yourself wanting one, you have misread the scope.
- Never commit secrets. `.env` is gitignored. `.env.example` holds placeholders only.
- **Dependencies are pinned to exact versions with `==`. Never `>=`, never unbounded.** This app ships to a VPS as a venv under systemd, so `pip install -r requirements.txt` must resolve identically in three weeks as it does today. When you add a dependency, install it, then pin the exact version that you actually tested against. If you want to upgrade something, that is a deliberate commit of its own, not a side effect of someone reinstalling.
- **The lock is compiled inside a `python:3.13` Linux container, using the exact command in README.md. Never on Windows.** The VPS is the machine that has to be correct; this laptop is the odd one out. Never install pip-tools into the venv. If you are about to run `pip-compile` outside a container, stop.
- **No environment-specific defaults in `app/config.py`.** Database URLs, secrets, password hashes, and hostnames are required and have no fallback value. Missing config MUST raise at startup. An app that silently starts against a default is worse than an app that refuses to start, because the failure moves from my terminal to my mother's data. The one exception is a boolean whose default is the restrictive one: `COOKIE_SECURE` defaults to `True`, because an unset value then fails secure. That is the opposite of a database URL quietly pointing at localhost. A default is allowed only when being wrong about it is safe.

## Validation philosophy

The system this replaces is a paper notebook, and a notebook never argues. If this app tells my mother "no" about something she has decided is fine, she goes back to the notebook and never opens the app again.

Reject only what is physically impossible or is unambiguously a typo. Never reject a judgement call.

- Impossible: two guests in one room on one night, `check_out <= check_in`.
- Typo: `num_guests < 1`, `deposit_paid < 0`, a `room_id` that does not exist.
- Hers to decide: everything else.

`num_guests` is NEVER validated against `rooms.standard_occupancy`. She routinely puts more people in a room than it is intended for, and she must have no trouble doing it. `standard_occupancy` is a display value and appears in no rejection path, warning, or confirmation dialog anywhere in this system.

The column is named `standard_occupancy` and not `capacity` on purpose. "Capacity" means limit, and a limit invites enforcement. Do not rename it back.

There is no `total_price` column. She knows every price by heart. Do not add one.

`note` is nullable free text and is never validated, parsed, length-limited, or interpreted. It is the margin of the notebook.

Before writing any validator, ask: is this physically impossible, or am I merely surprised? If merely surprised, do not write it.

## Domain invariants

- Dates are `DATE`, never `TIMESTAMP`. There are no timezones in this system.
- Money is `NUMERIC(10, 2)` and must arrive in Python as `Decimal`, never `float`. All amounts are EUR. There is no currency column.
- Rooms use string natural keys: `"3.3"`, `"A11"`. Not surrogate integers.
- No two reservations for the same room may overlap. Same-day turnover, where one guest's check-out equals the next guest's check-in, is LEGAL and must stay legal.
- The overlap rule is enforced by a Postgres exclusion constraint over `daterange(check_in, check_out, '[)')`, not by application code. The database is the single source of truth for it. Do not add a redundant Python-side overlap check. The API layer catches `IntegrityError` and translates it to a 409.

## Stack

Postgres, FastAPI, SQLAlchemy, Alembic, pytest. React comes in Phase 2, not yet.

Postgres is not negotiable and the reason is the exclusion constraint. Do not suggest SQLite, and do not suggest moving the overlap rule into application code so that SQLite becomes possible.

## Scope

Availability view, add, edit, delete, deposit tracking. That is all of it.

Not in scope, do not build, do not suggest: phone or voice assistant, payments, guest-facing booking, multi-user, roles, notifications, analytics, reporting, caching, EGN.

## This repo is public, and that is deliberate

It lives at `github.com/KaloyanYordanov12/hotel-reservations` under my own name. It is a portfolio piece and people are meant to read it.

`kaloyanyordanov.dev` and `agentcentral.kaloyanyordanov.dev` are MY domain and MY portfolio piece, already public and on my CV. This repo being public is precisely so that someone connects the two. They appear in `docs/deploy.md` and the brief on purpose. They are not a leak. Do not replace them with placeholders, do not raise them as an audit finding, do not suggest making this repo private over them.

What genuinely must never be committed: real secrets, real session keys, real password hashes, `.env`, the VPS IP or SSH strings, the hotel's name or address, and any real guest data. None of those are here, and that is the standard to hold.

Never suggest deleting the repo, rewriting published history, or force-pushing. If you think something sensitive has been committed, say so plainly and stop. I decide.

## Commands

To be filled in once Step 1 exists.
