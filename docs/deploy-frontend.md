# Frontend deploy runbook

Write only. You run every command yourself on the VPS and your laptop. This
assumes the Phase 1 backend is already deployed and `hotel-reservations` is
running on the box (see `docs/deploy.md`). Step 6 taught that service to serve
the built React app from the same FastAPI process at the same origin, so this
step just ships the build; there is no second service.

## The Agent Central rule still holds

Agent Central shares this box. This step is designed to touch nothing it depends
on: no tunnel change, no new service, no port change, no shared config. After the
one command that restarts our own service, confirm Agent Central still answers:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
```

That check is written as `[CHECK AC]` below. If it is not healthy, stop and roll
back.

## No tunnel change. At all.

This is the whole payoff of same-origin serving. The app ships through the
Cloudflare tunnel route that already points `reservations.kaloyanyordanov.dev` at
`127.0.0.1:8010`. Do NOT add a public hostname, do NOT edit any cloudflared
`config.yml`, do NOT reload or restart cloudflared. If a step below seems to need
a tunnel change, it does not; stop and re-read.

## Build strategy: my recommendation

The box has no Node installed, and this is a public portfolio repo. Of the two
options in the brief:

- Build on the box (`npm ci && npm run build`): keeps the repo clean, but installs
  the Node and npm toolchain plus `node_modules` on the machine that also serves
  Agent Central, adds a build step to every deploy, and lets a deploy fail on an
  npm hiccup.
- Commit `dist` to git: keeps the box Node-free, but checks minified build bundles
  into a public portfolio repo (ugly to read, noisy diffs) and fights the `dist`
  gitignore on every build.

I recommend neither exactly: build locally and ship the built `dist` to the box
out of band with rsync, keeping `dist` gitignored and the box Node-free. The
exact bytes you tested locally are what serve, the box stays minimal, and the
repo stays clean. Tradeoff: `dist` is not version controlled (it is a derived
artifact whose source is), so you must rebuild and reship it whenever the
frontend changes or a stale UI ships. The checklist at the end makes that a
habit. If you would rather have `dist` in git for a one-command `git pull` deploy,
say so and I will wire that instead.

---

## Deploy steps

Placeholders to settle first: `<VPS_USER>`, `<VPS_HOST>`, `<VPS_PUBLIC_IP>`.

### 0. Baseline
```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
curl -fsS https://reservations.kaloyanyordanov.dev/health     # backend already live: {"status":"ok"}
```

### 1. Locally: build and sanity check
On your laptop, in the repo root:
```
cd frontend
npm ci
npm run build            # produces frontend/dist
cd ..
```
Optional local confirmation that the same FastAPI app serves it (no Vite):
```
venv\Scripts\activate
uvicorn app.main:app --port 8000
# open http://localhost:8000/  -> the app loads, and /grid survives a refresh
```

### 2. Push the code
The Step 6 backend change (serving `dist`) has to be on the box. Push it now so
the box can pull it in step 3:
```
git push
```

### 3. On the box: pull the latest code
```
ssh <VPS_USER>@<VPS_HOST>
cd /opt/hotel-reservations
sudo -u hotel git pull
exit
```
`[CHECK AC]`

### 4. Ship the built dist to the box
From your laptop (NOT the box), copy the local build into the box's repo path
that the service reads (`frontend/dist`):
```
rsync -av --delete frontend/dist/ <VPS_USER>@<VPS_HOST>:/opt/hotel-reservations/frontend/dist/
```
`--delete` clears stale hashed assets from previous builds. If rsync is not
available on your laptop, clear and scp instead:
```
ssh <VPS_USER>@<VPS_HOST> "rm -rf /opt/hotel-reservations/frontend/dist"
scp -r frontend/dist <VPS_USER>@<VPS_HOST>:/opt/hotel-reservations/frontend/dist
```
Then make sure the service user can read it:
```
ssh <VPS_USER>@<VPS_HOST> "sudo chown -R hotel:hotel /opt/hotel-reservations/frontend/dist"
```

### 5. Restart our service (not Agent Central)
`hotel-reservations` is our own systemd unit; restarting it loads the new
serve_spa code. This does not touch Agent Central or the tunnel.
```
ssh <VPS_USER>@<VPS_HOST> "sudo systemctl restart hotel-reservations && systemctl status hotel-reservations --no-pager | head -5"
```
`[CHECK AC]`

### 6. Verify (done when)
```
curl -fsS https://reservations.kaloyanyordanov.dev/health                                          # {"status":"ok"}
curl -fsS -o /dev/null -w "root: %{http_code} %{content_type}\n" https://reservations.kaloyanyordanov.dev/
curl -fsS -o /dev/null -w "grid: %{http_code} %{content_type}\n" https://reservations.kaloyanyordanov.dev/grid
```
Expect `text/html` for `/` and `/grid` (a refresh on `/grid` still loads the app).
Then, from your phone: open `https://reservations.kaloyanyordanov.dev`, log in,
and search availability. That is the done condition.

Confirm it is still NOT reachable on the public IP (run from your laptop):
```
curl --max-time 5 http://<VPS_PUBLIC_IP>:8010/health     # must FAIL to connect
```
`[CHECK AC]`

---

## Rollback

The frontend is only static files served by the already-running service, so
backing out is small and never touches the tunnel.

- Roll the code back and restart:
```
ssh <VPS_USER>@<VPS_HOST> "cd /opt/hotel-reservations && sudo -u hotel git checkout <PREVIOUS_GOOD_COMMIT> && sudo systemctl restart hotel-reservations"
```
- Or, if only the SPA misbehaves, remove `dist` so the service falls back to
  API-only (non-API routes then return a 404 "Frontend not built", which is
  harmless to the API and to Agent Central):
```
ssh <VPS_USER>@<VPS_HOST> "rm -rf /opt/hotel-reservations/frontend/dist && sudo systemctl restart hotel-reservations"
```
`[CHECK AC]` after either.

---

## Before every future frontend deploy

1. `cd frontend && npm ci && npm run build`
2. `git push` (only if code changed)
3. box: `sudo -u hotel git pull` (only if code changed)
4. `rsync -av --delete frontend/dist/ <VPS_USER>@<VPS_HOST>:/opt/hotel-reservations/frontend/dist/`
5. `sudo systemctl restart hotel-reservations`
6. verify, and `[CHECK AC]`
