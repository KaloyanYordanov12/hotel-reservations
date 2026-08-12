# Deploy runbook: public hotel DEMO backend (VPS)

Write only. You run every command on the VPS yourself; nothing here has been run
for you. This deploys the public, no-login demo BACKEND as a separate service
against a separate database, alongside the real app, touching neither it nor
Agent Central.

Scope of this runbook: backend service, database, seed, and reset cron. It does
NOT build or serve a frontend (that is a separate Cloudflare Pages project, see
the note below) and it does NOT touch the Cloudflare tunnel (that is Step 6 of
the brief, its own runbook). Until the tunnel step, the demo backend is reachable
only on the box's loopback, which is what we want here.

## The one rule that matters

The VPS already serves Agent Central, the real hotel (`reservations....`), voice,
and drinkingbrothers. This deploy is ADD ONLY. It never modifies, restarts, or
reconfigures an existing service, unit, database, tunnel, or route. In
particular it never alters the real `hotel` database or its role. If a step seems
to require touching any of them, STOP and do not improvise.

After every step marked `[CHECK AC]`, confirm the existing sites still answer:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
curl -fsS -o /dev/null -w "Hotel(real):  %{http_code}\n" https://reservations.kaloyanyordanov.dev/health
# plus voice and drinkingbrothers at their known URLs
```

Expect `200` from each. If any is unhealthy, STOP and roll back (see the end).

## Placeholders to settle before you start

- `DEMO_PORT` = `8011` (this runbook uses 8011; confirm it is free in Step 1)
- `DEMO_DB_PW` = the password you choose for the restricted demo role in Step 4
- `<THIS_REPO_URL>`, `<VPS_PUBLIC_IP>`

## Frontend: a separate Cloudflare Pages project (NOT built or served here)

The demo frontend is a SECOND Cloudflare Pages project that you set up in the
Cloudflare dashboard, separate from this runbook. It is built with
`VITE_API_URL=https://reservations-demo.kaloyanyordanov.dev`, and this backend
answers at that hostname once the tunnel route (Step 6) is added. Nothing about
the frontend is built or served on the VPS; this demo backend serves the API
only.

Flag before you build that Pages project, so it does not silently fail. As the
code stands today, a separate-origin frontend will NOT work without two code
changes I have deliberately not made here:

1. `frontend/src/api.js` calls `/api` as a RELATIVE, same-origin path and does not
   read `VITE_API_URL`. On Pages that means it would call the Pages origin, not
   this backend. It must be changed to prefix requests with `VITE_API_URL`.
2. Cross-origin browser calls from the Pages origin to
   `reservations-demo.kaloyanyordanov.dev` need CORS response headers, which the
   backend does not send today. DEMO_MODE removes the login/cookie, so it is a
   plain (no-credentials) CORS allow for the Pages origin, but it still must be
   added.

Both are small and belong in their own commit. Say the word and I will wire
`VITE_API_URL` support into `api.js` and a scoped CORS allow into the backend
before you build the Pages project. This runbook stands on its own regardless:
the backend below is correct and testable on loopback without any frontend.

---

## Step 0: Record the current state

So rollback has something to return to, and so we can prove nothing changed.

```
free -h
df -h /
ss -ltnp                        # note ports/services already up (8010 is the real hotel)
systemctl list-units --type=service --state=running
```

Baseline the existing sites (all must be healthy BEFORE we start):

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
curl -fsS -o /dev/null -w "Hotel(real):  %{http_code}\n" https://reservations.kaloyanyordanov.dev/health
# plus voice and drinkingbrothers
```

We do NOT back up cloudflared here: this runbook never touches it. That backup
belongs to the Step 6 tunnel runbook, right before the tunnel edit.

`[CHECK AC]`

---

## Step 1: Version checks and a free port. STOP if a version differs.

The real deploy already put Python 3.13 and Postgres 16 on the box. Confirm, and
confirm the demo port is free.

```
python3.13 --version            # expect Python 3.13.x
psql --version                  # expect psql (PostgreSQL) 16.x
ss -ltnp | grep -w :8011 || echo "8011 is free"
```

STOP conditions, do not work around them:

- No `python3.13`: stop and tell me.
- Postgres not major 16: stop and tell me. Do not touch the existing cluster.
- `8011` is taken: pick another free port and use it consistently in
  `deploy/hotel-demo.service` (the `--port`) and in the Step 6 tunnel target.

---

## Step 2: Demo service user and directories (separate from the real app)

A dedicated unprivileged user, its own app dir, its own config dir, and a log dir
for the reset cron. None of these overlap the real `hotel` user or
`/opt/hotel-reservations`.

```
sudo useradd --system --home /opt/hotel-demo --shell /usr/sbin/nologin hotel-demo
sudo mkdir -p /opt/hotel-demo /etc/hotel-demo /var/log/hotel-demo
sudo chown hotel-demo:hotel-demo /opt/hotel-demo /var/log/hotel-demo
```

Check: `/opt/hotel-demo` should be mode `755` (owner hotel-demo). The postgres OS
user needs to traverse it in Step 6 to run alembic from the venv.

```
stat -c '%a %U:%G %n' /opt/hotel-demo    # expect 755 hotel-demo:hotel-demo
```

---

## Step 3: Code, venv, dependencies

Same repo, a SEPARATE checkout. The pushed code already includes DEMO_MODE and the
seed/reset scripts.

```
sudo -u hotel-demo git clone <THIS_REPO_URL> /opt/hotel-demo
cd /opt/hotel-demo
sudo -u hotel-demo python3.13 -m venv venv
sudo -u hotel-demo ./venv/bin/python --version         # must report 3.13.x
sudo -u hotel-demo ./venv/bin/pip install -r requirements.txt
```

The lock resolves the same on this Linux box as it was compiled for. Do not
recompile it here.

`[CHECK AC]`

---

## Step 4: Demo database and RESTRICTED runtime role (ADD ONLY)

Two objects, both new. The database is owned by `postgres` (migrations run as the
superuser in Step 6). The runtime role `hotel_demo_app` is what the app connects
as: it can read and write the demo's rows but has no DDL and no privileges on the
real database. Nothing here touches the real `hotel` role or database.

```
# Restricted login role. Explicitly no superuser, no createdb, no createrole.
sudo -u postgres psql -c "CREATE ROLE hotel_demo_app LOGIN PASSWORD 'DEMO_DB_PW' NOSUPERUSER NOCREATEDB NOCREATEROLE;"

# Database owned by the postgres superuser (so migrations run as postgres).
sudo -u postgres createdb -O postgres hotel_demo
```

Confirm both exist:

```
sudo -u postgres psql -c "\du hotel_demo_app"
sudo -u postgres psql -c "\l hotel_demo" | grep hotel_demo
```

Isolation note: `hotel_demo_app` is granted privileges ONLY on the demo database's
tables, in Step 6, after they exist. It is never granted anything on the real
`hotel` database, so even if it opens a connection there it can read no rows. We
prove that at the end of Step 6 rather than modifying the real database (which
this runbook must not touch).

`[CHECK AC]`

---

## Step 5: The demo EnvironmentFile (secrets)

```
sudo cp /opt/hotel-demo/deploy/hotel-demo.env.example \
        /etc/hotel-demo/hotel-demo.env
sudo chmod 600 /etc/hotel-demo/hotel-demo.env
sudo chown hotel-demo:hotel-demo /etc/hotel-demo/hotel-demo.env
```

Owner is `hotel-demo` (not root) so the reset cron, which runs as `hotel-demo`,
can read it; `600` keeps every other unprivileged user out, and systemd reads it
as root regardless. Now edit `/etc/hotel-demo/hotel-demo.env` and set real values:

- `DATABASE_URL`: role `hotel_demo_app`, password `DEMO_DB_PW` from Step 4,
  database `hotel_demo`. It must name `hotel_demo`, never `hotel`. (The reset
  script hard-refuses any other database name.)
- `DEMO_MODE`: leave `1`. This is what makes it the demo.
- `SESSION_SECRET`: `python3.13 -c "import secrets; print(secrets.token_urlsafe(32))"`
- `APP_PASSWORD_HASH`: a throwaway hash, required to boot even though login is
  bypassed: `cd /opt/hotel-demo && sudo -u hotel-demo ./venv/bin/python scripts/hash_password.py`
- `COOKIE_SECURE`: leave `True`.

---

## Step 6: Migrations as the postgres superuser, then grant the app role

Alembic imports `app.config`, which validates SESSION_SECRET and APP_PASSWORD_HASH
at startup and connects using whatever `DATABASE_URL` it is given. We run it with a
SUPERUSER connection over the local socket (peer auth as the postgres role, no
password, no change to shared cluster auth) and throwaway valid secrets, so the
migration runs as `postgres` and the tables are owned by `postgres`.

```
cd /opt/hotel-demo
sudo -u postgres env \
  DATABASE_URL='postgresql+psycopg://postgres@/hotel_demo?host=/var/run/postgresql' \
  SESSION_SECRET="$(python3.13 -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  APP_PASSWORD_HASH="$(/opt/hotel-demo/venv/bin/python -c 'import bcrypt; print(bcrypt.hashpw(b"x", bcrypt.gensalt()).decode())')" \
  /opt/hotel-demo/venv/bin/alembic upgrade head
```

If your Postgres socket is not at `/var/run/postgresql` (the apt default), set the
correct dir in `host=`. Verify the schema is complete and identical to the real
one, including the exclusion constraint:

```
sudo -u postgres psql hotel_demo -c "SELECT count(*) FROM rooms;"                 # expect 10
sudo -u postgres psql hotel_demo -c "\d reservations" | grep no_double_booking    # constraint present
```

Now grant the restricted app role exactly what it needs: read the rooms, full
read/write on the reservations rows, and nothing else. No schema ownership, no
CREATE, so no DDL.

```
sudo -u postgres psql hotel_demo <<'SQL'
REVOKE ALL ON SCHEMA public FROM hotel_demo_app;
GRANT USAGE ON SCHEMA public TO hotel_demo_app;
GRANT SELECT ON rooms TO hotel_demo_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON reservations TO hotel_demo_app;
SQL
```

Prove the isolation (run these three; the first passes, the other two must FAIL):

```
# Can read the demo's rooms:
PGPASSWORD='DEMO_DB_PW' psql "postgresql://hotel_demo_app@127.0.0.1:5432/hotel_demo" -c "SELECT count(*) FROM rooms;"       # expect 10

# Cannot create objects (no DDL): expect ERROR permission denied for schema public
PGPASSWORD='DEMO_DB_PW' psql "postgresql://hotel_demo_app@127.0.0.1:5432/hotel_demo" -c "CREATE TABLE probe(x int);"        # must FAIL

# Cannot read the real hotel data: expect ERROR permission denied for table reservations
PGPASSWORD='DEMO_DB_PW' psql "postgresql://hotel_demo_app@127.0.0.1:5432/hotel" -c "SELECT count(*) FROM reservations;"     # must FAIL
```

The second and third failing is the proof: the demo role has no DDL and cannot
read the real bookings.

`[CHECK AC]`

---

## Step 7: Seed hotel_demo once (initial data)

Populate the demo with the Bulgarian bookings, as the restricted app role (proving
that role has the DML it needs, and matching exactly what the cron will do). The
reset script refuses unless the database is named `hotel_demo`, then wipes and
reseeds.

```
cd /opt/hotel-demo
sudo -u hotel-demo env $(sudo cat /etc/hotel-demo/hotel-demo.env | grep -v '^#' | xargs) \
    ./venv/bin/python -m scripts.reset_demo          # expect: "Reset hotel_demo: 16 demo reservations."
sudo -u postgres psql hotel_demo -c "SELECT count(*) FROM reservations;"   # expect 16
```

---

## Step 8: Install and start the demo unit

```
sudo cp /opt/hotel-demo/deploy/hotel-demo.service \
        /etc/systemd/system/hotel-demo.service
sudo systemctl daemon-reload          # re-reads unit files only; restarts nothing
sudo systemctl enable --now hotel-demo
sudo systemctl status hotel-demo --no-pager | head -6
```

Confirm it is up on loopback, on the demo port, and nowhere else:

```
curl -fsS http://127.0.0.1:8011/health           # expect {"status":"ok"}
curl -fsS http://127.0.0.1:8011/api/demo-status   # expect {"demo":true}
ss -ltnp | grep -w :8011                           # address must be 127.0.0.1:8011, never 0.0.0.0
```

`{"demo":true}` confirms DEMO_MODE is on. Sanity-check the auth bypass is live and
returns the seeded data with no session:

```
curl -fsS http://127.0.0.1:8011/api/reservations | head -c 200 ; echo   # 200 with a JSON list of bookings
```

`[CHECK AC]`

---

## Step 9: Install the 30-minute reset cron

Reset the demo to clean seeded data every 30 minutes. A system cron drop-in that
runs as the unprivileged `hotel-demo` user (which can read the env file from
Step 5 and write the log dir from Step 2). See docs/demo-reset.md for the
rationale.

```
sudo tee /etc/cron.d/hotel-demo-reset >/dev/null <<'CRON'
# Reset the public hotel demo to clean seeded data every 30 minutes (:00 and :30).
# Runs as hotel-demo. The env file provides the hotel_demo DATABASE_URL; the
# reset script hard-refuses any database not named hotel_demo.
*/30 * * * * hotel-demo cd /opt/hotel-demo && set -a && . /etc/hotel-demo/hotel-demo.env && set +a && /opt/hotel-demo/venv/bin/python -m scripts.reset_demo >> /var/log/hotel-demo/reset.log 2>&1
CRON
sudo chmod 644 /etc/cron.d/hotel-demo-reset
```

Confirm it fires on the next half-hour boundary, then check the log:

```
tail -n 5 /var/log/hotel-demo/reset.log     # a line like "Reset hotel_demo: 16 demo reservations."
```

---

## Step 10: Confirm "done" (loopback only; public URL waits for Step 6/tunnel + Pages)

```
curl -fsS http://127.0.0.1:8011/health                                  # {"status":"ok"}
curl -fsS http://127.0.0.1:8011/api/demo-status                          # {"demo":true}
sudo -u postgres psql hotel_demo -c "SELECT count(*) FROM reservations;" # 16
```

Not reachable on the public IP (run from your laptop, NOT the box). Expect
connection refused or timeout on the demo port, never a response:

```
curl --max-time 5 http://<VPS_PUBLIC_IP>:8011/health   # must FAIL to connect
```

The public HTTPS check (`https://reservations-demo.kaloyanyordanov.dev/`) is
deliberately NOT here: the tunnel route is Step 6 and the frontend is a separate
Pages project. Until both are done, loopback is the only door and that is correct.

Final confirmation that this add-only deploy changed nothing else `[CHECK AC]`:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
curl -fsS -o /dev/null -w "Hotel(real):  %{http_code}\n" https://reservations.kaloyanyordanov.dev/health
# plus voice and drinkingbrothers
```

All still `200`. Because this runbook never touched the tunnel, a shared config,
or any existing unit or database, that is the expected result.

---

## Rollback (return the box to its pre-demo state)

Undo in reverse. Each piece is independent, and none of it touches the real hotel
service, Agent Central, or the tunnel.

```
# Reset cron:
sudo rm -f /etc/cron.d/hotel-demo-reset

# Demo service:
sudo systemctl disable --now hotel-demo
sudo rm -f /etc/systemd/system/hotel-demo.service
sudo systemctl daemon-reload

# Demo database and role (only if fully backing out):
sudo -u postgres dropdb hotel_demo
sudo -u postgres psql -c "DROP ROLE hotel_demo_app;"

# Files, logs, config, and user:
sudo rm -rf /opt/hotel-demo /etc/hotel-demo /var/log/hotel-demo
sudo userdel hotel-demo
```

`[CHECK AC]` after rollback. The real `hotel` database, its role, its service, and
Postgres itself are untouched throughout.
