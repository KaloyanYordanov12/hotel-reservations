# Deploy runbook: public hotel DEMO backend + frontend

Write only. You run every command on the VPS and your laptop yourself; nothing
here has been run for you. This deploys the public, no-login demo as a SEPARATE
service against a SEPARATE database, alongside the real app, touching neither it
nor Agent Central.

This runbook stops BEFORE the Cloudflare tunnel. Adding
`reservations-demo.kaloyanyordanov.dev` to the tunnel is Step 6 of the brief and
has its own runbook; until that is done the demo is reachable only on the box's
loopback, which is exactly what we want here.

## The one rule that matters

The VPS already serves Agent Central, the real hotel (`reservations....`), voice,
and drinkingbrothers. This deploy is ADD ONLY. It never modifies, restarts, or
reconfigures an existing service, unit, database, tunnel, or route. If a step
seems to require touching any of them, STOP and do not improvise.

After every step marked `[CHECK AC]`, confirm the existing sites still answer:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
curl -fsS -o /dev/null -w "Hotel(real):  %{http_code}\n" https://reservations.kaloyanyordanov.dev/health
# plus voice and drinkingbrothers at their known URLs
```

Expect `200` from each. If any is unhealthy, STOP and roll back (see the end).

## Placeholders to settle before you start

- `DEMO_DOMAIN` = `reservations-demo.kaloyanyordanov.dev` (used only in Step 6; noted here for context)
- `DEMO_PORT` = `8011` (this runbook uses 8011; confirm it is free in Step 1)
- `<THIS_REPO_URL>`, `<VPS_USER>`, `<VPS_HOST>`, `<VPS_PUBLIC_IP>`

## Read this before Step 6 (frontend): the VITE_API_URL question

The brief says to build the demo frontend with `VITE_API_URL` pointing at the demo
subdomain. The code does not work that way, and I did not change it, so here is the
honest picture:

- The real frontend is served BY the FastAPI process itself, from `frontend/dist`,
  at the same origin (see `docs/deploy-frontend.md` and `app/main.py`'s SPA
  catch-all). `frontend/src/api.js` calls `/api` as a RELATIVE, same-origin path.
  There is no `VITE_API_URL` anywhere in the code; nothing reads it.
- Mirroring "how the real frontend is served" (which the brief offers as the
  option) means the demo backend serves its OWN `frontend/dist` at
  `DEMO_DOMAIN`. Because the SPA and its `/api` live on the same origin, the
  relative calls just work and `VITE_API_URL` is unnecessary.
- So this runbook does NOT set `VITE_API_URL`. Setting it would be a no-op, and
  making the frontend actually consume it (to serve the demo UI from a different
  origin than its API, e.g. Cloudflare Pages) would require a code change to
  `api.js`, which is out of scope for a deploy runbook and would touch the shared
  codebase the real app runs on.

If you do want a separate-origin demo frontend later, say so and I will wire the
`VITE_API_URL` support into `api.js` as its own commit first. For now: same
origin, no VITE_API_URL, matching the real deploy exactly.

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

## Step 4: Postgres role and database for the demo (ADD ONLY)

A SEPARATE role and a SEPARATE database. Nothing here touches the real `hotel`
role or the real `hotel` database. Postgres and its contrib package (which
provides `btree_gist`) are already installed from the real deploy.

```
# Choose a strong password, distinct from the real DB password; keep it for Step 5.
sudo -u postgres psql -c "CREATE ROLE hotel_demo LOGIN PASSWORD 'CHANGE_ME_DEMO_DB_PASSWORD';"
sudo -u postgres createdb -O hotel_demo hotel_demo
```

Isolation: `hotel_demo` owns only the `hotel_demo` database and has no privileges
on the real `hotel` database's tables. As belt-and-braces, deny it even the
ability to connect to the real database:

```
sudo -u postgres psql -c "REVOKE CONNECT ON DATABASE hotel FROM hotel_demo;"
```

Confirm the demo role cannot reach the real data (this must FAIL):

```
sudo -u postgres psql "postgresql://hotel_demo:CHANGE_ME_DEMO_DB_PASSWORD@127.0.0.1:5432/hotel" -c "select 1" \
  && echo "PROBLEM: demo role reached the real DB" || echo "good: demo role cannot reach the real DB"
```

`btree_gist` is a trusted extension in Postgres 16, so the `hotel_demo` database
owner can create it during migrations without superuser (the migration runs
`CREATE EXTENSION IF NOT EXISTS btree_gist`). No superuser step is needed here.

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

- `DATABASE_URL`: the demo DB password from Step 4. It must name `hotel_demo`,
  never `hotel`. (The reset script hard-refuses any other database name.)
- `DEMO_MODE`: leave `1`. This is what makes it the demo.
- `SESSION_SECRET`: `python3.13 -c "import secrets; print(secrets.token_urlsafe(32))"`
- `APP_PASSWORD_HASH`: a throwaway hash, required to boot even though login is
  bypassed: `cd /opt/hotel-demo && sudo -u hotel-demo ./venv/bin/python scripts/hash_password.py`
- `COOKIE_SECURE`: leave `True`.

---

## Step 6: Migrations against hotel_demo

Run Alembic with the demo env. This creates both tables, seeds the 10 rooms, and
adds `btree_gist` plus the exclusion constraint, so the schema is identical to the
real database and the double-booking rejection demos correctly.

```
cd /opt/hotel-demo
sudo -u hotel-demo env $(sudo cat /etc/hotel-demo/hotel-demo.env | grep -v '^#' | xargs) \
    ./venv/bin/alembic upgrade head
sudo -u postgres psql hotel_demo -c "SELECT count(*) FROM rooms;"                 # expect 10
sudo -u postgres psql hotel_demo -c "\d reservations" | grep no_double_booking    # constraint present
```

---

## Step 7: Install and start the demo unit

```
sudo cp /opt/hotel-demo/deploy/hotel-demo.service \
        /etc/systemd/system/hotel-demo.service
sudo systemctl daemon-reload          # re-reads unit files only; restarts nothing
sudo systemctl enable --now hotel-demo
sudo systemctl status hotel-demo --no-pager | head -6
```

Confirm it is up on loopback, on the demo port, and nowhere else:

```
curl -fsS http://127.0.0.1:8011/health          # expect {"status":"ok"}
curl -fsS http://127.0.0.1:8011/api/demo-status  # expect {"demo":true}
ss -ltnp | grep -w :8011                          # address must be 127.0.0.1:8011, never 0.0.0.0
```

`{"demo":true}` confirms DEMO_MODE is on. Sanity-check the auth bypass is live
(no session, still 200):

```
curl -fsS -o /dev/null -w "reservations: %{http_code}\n" http://127.0.0.1:8011/api/reservations   # expect 200
```

`[CHECK AC]`

---

## Step 8: Build and ship the demo frontend (same-origin, mirrors the real app)

Read the "VITE_API_URL question" note near the top first. We build normally and
serve the built `dist` from the demo's own FastAPI process, exactly as the real
app does. No `VITE_API_URL`, no second frontend service, no tunnel change here.

On your laptop, in the repo root:

```
cd frontend
npm ci
npm run build            # produces frontend/dist (includes the demo banner, gated on /api/demo-status)
cd ..
```

Ship the built `dist` into the DEMO checkout's path that the demo service reads:

```
rsync -av --delete frontend/dist/ <VPS_USER>@<VPS_HOST>:/opt/hotel-demo/frontend/dist/
ssh <VPS_USER>@<VPS_HOST> "sudo chown -R hotel-demo:hotel-demo /opt/hotel-demo/frontend/dist"
```

`--delete` clears stale hashed assets. If rsync is unavailable, `rm -rf` the
remote `dist` and `scp -r` it instead (see docs/deploy-frontend.md for that form).

Restart ONLY the demo service to pick up the files:

```
ssh <VPS_USER>@<VPS_HOST> "sudo systemctl restart hotel-demo && systemctl status hotel-demo --no-pager | head -5"
```

The demo banner appears because the frontend fetches `/api/demo-status` and the
demo backend returns `{"demo":true}`. On the real app that endpoint returns
`{"demo":false}` and the banner stays hidden, so the same `dist` is safe
everywhere.

`[CHECK AC]`

---

## Step 9: Seed hotel_demo once (initial data)

Populate the demo with the Bulgarian bookings so it looks alive from the first
visit. The reset script is the guarded entrypoint: it refuses unless the database
is named `hotel_demo`, then wipes and reseeds. Running it once here is the initial
seed.

```
cd /opt/hotel-demo
sudo -u hotel-demo env $(sudo cat /etc/hotel-demo/hotel-demo.env | grep -v '^#' | xargs) \
    ./venv/bin/python -m scripts.reset_demo          # expect: "Reset hotel_demo: 16 demo reservations."
sudo -u postgres psql hotel_demo -c "SELECT count(*) FROM reservations;"   # expect 16
```

---

## Step 10: Install the 30-minute reset cron

Reset the demo to clean seeded data every 30 minutes. This uses a system cron
drop-in that runs as the unprivileged `hotel-demo` user (which can read the env
file from Step 5 and write the log dir from Step 2). See docs/demo-reset.md for
the rationale.

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

## Step 11: Confirm "done" (loopback only; public URL waits for Step 6/tunnel)

```
curl -fsS http://127.0.0.1:8011/health                                  # {"status":"ok"}
curl -fsS http://127.0.0.1:8011/api/demo-status                          # {"demo":true}
curl -fsS -o /dev/null -w "root: %{http_code} %{content_type}\n" http://127.0.0.1:8011/   # text/html
sudo -u postgres psql hotel_demo -c "SELECT count(*) FROM reservations;" # 16
```

Not reachable on the public IP (run from your laptop, NOT the box). Expect
connection refused or timeout on the demo port, never a response:

```
curl --max-time 5 http://<VPS_PUBLIC_IP>:8011/health   # must FAIL to connect
```

The public HTTPS check (`https://reservations-demo.kaloyanyordanov.dev/`) is
deliberately NOT here: the tunnel route is Step 6. Until then, loopback is the
only door and that is correct.

Final confirmation that this add-only deploy changed nothing else `[CHECK AC]`:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
curl -fsS -o /dev/null -w "Hotel(real):  %{http_code}\n" https://reservations.kaloyanyordanov.dev/health
# plus voice and drinkingbrothers
```

All still `200`. Because this runbook never touched the tunnel, a shared config,
or any existing unit, that is the expected result.

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
sudo -u postgres psql -c "DROP ROLE hotel_demo;"

# Files, logs, config, and user:
sudo rm -rf /opt/hotel-demo /etc/hotel-demo /var/log/hotel-demo
sudo userdel hotel-demo
```

`[CHECK AC]` after rollback. The real `hotel` database, its role, its service, and
Postgres itself are untouched throughout.
