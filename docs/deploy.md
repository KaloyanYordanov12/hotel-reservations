# Deploy runbook: hotel reservations backend

Backend only. No frontend. You run every command on the VPS yourself; nothing
here has been run for you.

## The one rule that matters

The VPS already serves Agent Central at `agentcentral.kaloyanyordanov.dev`. This
deploy is ADD ONLY. It never modifies, restarts, or reconfigures an existing
service, unit, or tunnel route. If a step below seems to require touching Agent
Central, stop and do not improvise.

After every step marked `[CHECK AC]`, confirm Agent Central still answers before
continuing:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
```

Expect `200` (adjust the path if that is not Agent Central's health URL). If it
is not healthy, stop and roll back (see the end of this file).

Placeholders to settle before you start:

- `RESERVATIONS_DOMAIN` (suggested `reservations.kaloyanyordanov.dev`)
- `APP_PORT` (this runbook uses `8001`; confirm it is free in step 1)

---

## Step 0: Record the current state

So rollback has something to return to.

```
free -h
df -h /
ss -ltnp                        # note which ports and services are already up
systemctl list-units --type=service --state=running
cloudflared tunnel list         # note the tunnel name/id serving Agent Central
```

Back up the cloudflared config before anything touches it, and record the path:

```
sudo mkdir -p /root/agentcentral-backups
sudo cp -a /etc/cloudflared /root/agentcentral-backups/cloudflared-$(date +%Y%m%d-%H%M%S)
ls -d /root/agentcentral-backups/cloudflared-*   # <-- record this path
```

`[CHECK AC]`

---

## Step 1: Version checks. STOP if either differs.

Local dev is Python 3.13 and Postgres 16. A mismatch surfaces here, not silently.

```
python3.13 --version            # expect Python 3.13.x
psql --version                  # expect psql (PostgreSQL) 16.x, if Postgres exists
ss -ltnp | grep -w :8001 || echo "8001 is free"
```

STOP conditions, do not work around them:

- No `python3.13` on the box: stop and tell me. Do not deploy on 3.12 or 3.14.
- Postgres is present but not major 16: stop and tell me. Do not upgrade or
  reconfigure the existing cluster (it may be shared), and do not run the Step 4
  exclusion-constraint matrix against a major it was never tested on.
- `8001` is taken: pick another free port and use it consistently in the unit
  file and the tunnel target below.

If Postgres is not installed at all, that is fine to add (it is a new service,
not a change to Agent Central); install `postgresql-16` and `postgresql-16` 's
contrib package in step 4.

---

## Step 2: Service user and directories

```
sudo useradd --system --home /opt/hotel-reservations --shell /usr/sbin/nologin hotel
sudo mkdir -p /opt/hotel-reservations /etc/hotel-reservations
sudo chown hotel:hotel /opt/hotel-reservations
```

---

## Step 3: Code, venv, dependencies

```
sudo -u hotel git clone <THIS_REPO_URL> /opt/hotel-reservations
cd /opt/hotel-reservations
sudo -u hotel python3.13 -m venv venv
sudo -u hotel ./venv/bin/python --version         # must report 3.13.x
sudo -u hotel ./venv/bin/pip install -r requirements.txt
```

The lock resolves the same on this Linux box as it was compiled for. Do not
recompile it here.

`[CHECK AC]`

---

## Step 4: Postgres role and database (ADD ONLY)

If Postgres is absent, install it first (new service, does not touch Agent
Central). `btree_gist` (needed by the exclusion constraint) ships in the contrib
package, so install that too:

```
sudo apt-get install -y postgresql-16 postgresql-contrib-16
```

Create a dedicated role and database. Nothing here touches any existing database:

```
# Choose a strong DB password and keep it for the env file in step 5.
sudo -u postgres psql -c "CREATE ROLE hotel LOGIN PASSWORD 'CHANGE_ME_DB_PASSWORD';"
sudo -u postgres createdb -O hotel hotel
```

Postgres listens on `127.0.0.1:5432` by default. Do not change `listen_addresses`.

`[CHECK AC]`

---

## Step 5: The EnvironmentFile (secrets)

```
sudo cp /opt/hotel-reservations/deploy/hotel-reservations.env.example \
        /etc/hotel-reservations/hotel-reservations.env
sudo chmod 600 /etc/hotel-reservations/hotel-reservations.env
sudo chown root:root /etc/hotel-reservations/hotel-reservations.env
```

Now edit `/etc/hotel-reservations/hotel-reservations.env` and set real values:

- `DATABASE_URL`: the password you chose in step 4.
- `TEST_DATABASE_URL`: same host, the `hotel_test` name. It is never connected to
  at runtime, but the app refuses to start without it (see "known wart" below).
- `SESSION_SECRET`: `python3.13 -c "import secrets; print(secrets.token_urlsafe(32))"`
- `APP_PASSWORD_HASH`: `cd /opt/hotel-reservations && sudo -u hotel ./venv/bin/python scripts/hash_password.py`
- `COOKIE_SECURE`: leave `True`.

---

## Step 6: Migrations

Run Alembic with the same env the service will use. This creates both tables,
seeds the 10 rooms, and adds the exclusion constraint and `btree_gist`.

```
cd /opt/hotel-reservations
sudo -u hotel env $(sudo cat /etc/hotel-reservations/hotel-reservations.env | grep -v '^#' | xargs) \
    ./venv/bin/alembic upgrade head
sudo -u postgres psql hotel -c "SELECT count(*) FROM rooms;"   # expect 10
```

---

## Step 7: Install and start the unit

```
sudo cp /opt/hotel-reservations/deploy/hotel-reservations.service \
        /etc/systemd/system/hotel-reservations.service
sudo systemctl daemon-reload          # re-reads unit files only; restarts nothing
sudo systemctl enable --now hotel-reservations
sudo systemctl status hotel-reservations --no-pager
```

Confirm it is up on loopback and nowhere else:

```
curl -fsS http://127.0.0.1:8001/health          # expect {"status":"ok"}
ss -ltnp | grep -w :8001                          # address must be 127.0.0.1:8001, never 0.0.0.0
```

`[CHECK AC]`

---

## Step 8: Cloudflare tunnel route (the risky one)

The goal is one new public hostname pointing at `http://127.0.0.1:8001`. How you
add it depends on how the existing tunnel is configured. Prefer the path that
does NOT touch the running cloudflared service.

Find out which it is:

```
cloudflared tunnel list
cat /etc/cloudflared/config.yml 2>/dev/null || echo "no local ingress file"
```

### Path A (preferred): remotely managed tunnel

If there is no local `config.yml` with `ingress:` rules, the tunnel is managed
from the Cloudflare Zero Trust dashboard. Add the route there, which requires NO
local change and NO restart of cloudflared:

- Zero Trust > Networks > Tunnels > (the tunnel serving Agent Central) >
  Public Hostname > Add a public hostname.
- Subdomain/domain: `RESERVATIONS_DOMAIN`.
- Service: `HTTP` -> `localhost:8001`.

This is purely additive and does not touch Agent Central's route.

### Path B: locally managed `config.yml`

If `/etc/cloudflared/config.yml` has `ingress:` rules, you already backed it up
in step 0. Add ONE new rule ABOVE the final catch-all (`service: http_status:404`),
leaving every existing rule untouched:

```
  - hostname: RESERVATIONS_DOMAIN
    service: http://127.0.0.1:8001
```

Then create the DNS route and reload cloudflared. Reloading is the one moment
this deploy touches a shared service, so do it deliberately:

```
cloudflared tunnel route dns <TUNNEL_NAME> RESERVATIONS_DOMAIN
sudo systemctl reload cloudflared     # reload, not restart, if supported
```

If `reload` is not supported and only `restart` is, STOP and tell me before
running it; a restart briefly drops Agent Central and I want to choose the
moment.

`[CHECK AC]`  (immediately, both after adding the route and after any reload)

---

## Step 9: Confirm "done"

```
# HTTPS on the real domain:
curl -fsS https://RESERVATIONS_DOMAIN/health           # expect {"status":"ok"}

# Not reachable on the public IP (run from your laptop, NOT the box).
# Expect connection refused or timeout, never a response:
curl --max-time 5 http://<VPS_PUBLIC_IP>:8001/health   # must FAIL to connect
```

- Log in from your phone against `https://RESERVATIONS_DOMAIN` (the password you
  hashed in step 5).
- Run the restore drill in `docs/backup.md` at least once.

Agent Central final check `[CHECK AC]`.

---

## Rollback (return the box to its current state)

Undo in reverse. Each piece is independent.

```
# Tunnel route:
#  Path A: delete the public hostname in the Zero Trust dashboard.
#  Path B: restore the backed-up config and reload:
sudo cp -a /root/agentcentral-backups/cloudflared-<STAMP>/. /etc/cloudflared/
sudo systemctl reload cloudflared        # STOP and ask me first if only restart is available

# App service:
sudo systemctl disable --now hotel-reservations
sudo rm /etc/systemd/system/hotel-reservations.service
sudo systemctl daemon-reload

# Database (only if you are fully backing out):
sudo -u postgres dropdb hotel
sudo -u postgres psql -c "DROP ROLE hotel;"

# Files and user:
sudo rm -rf /opt/hotel-reservations /etc/hotel-reservations
sudo userdel hotel
```

`[CHECK AC]` after the tunnel step. Postgres itself, if you installed it fresh,
can be left in place; it listens only on loopback and serves nothing else.

---

## Known wart (flagged, not worked around here)

`app/config.py` lists `test_database_url` as a required setting, so the app will
not start in production unless `TEST_DATABASE_URL` is set, even though production
never connects to it. The env template sets it to a same-host value to satisfy
the check. This is a code smell worth a small future commit (make it optional, or
move test-only settings out of the production Settings), but it is a code change,
not a deploy change, so it is out of scope for this step.
