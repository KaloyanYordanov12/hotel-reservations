# Deploy runbook: public hotel DEMO frontend (same-origin)

Write only. You run every command on the VPS and your laptop yourself; nothing
here has been run for you. This assumes the demo BACKEND from `docs/deploy-demo.md`
is deployed and `hotel-demo` is running on the box (uvicorn on `127.0.0.1:8011`).

The demo backend serves the built SPA from `/opt/hotel-demo/frontend/dist` through
the same catch-all route the real app uses (`app/main.py` `serve_spa`), so the demo
frontend is same-origin, exactly like the real hotel: the SPA and `/api` both live
on `reservations-demo.kaloyanyordanov.dev`. There is no second service.

This supersedes the earlier "separate Cloudflare Pages project" plan for the demo
frontend. Because the demo backend serves the SPA itself, there is no second
origin, so `VITE_API_URL`, `DEMO_FRONTEND_ORIGIN`, and the demo CORS are all
unnecessary here. (The CORS code stays harmless and dormant: it does nothing
unless `DEMO_FRONTEND_ORIGIN` is set, which it should not be for same-origin.)

## The Agent Central rule still holds

Agent Central shares this box. This step is designed to touch nothing it depends
on: no tunnel change, no new service, no port change, no shared config. After the
one command that restarts our own demo service, confirm Agent Central still
answers:

```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
```

That check is written as `[CHECK AC]` below. If it is not healthy, stop and roll
back.

## No tunnel change. At all.

This is the payoff of same-origin serving. The SPA ships through the demo's own
tunnel route (`reservations-demo.kaloyanyordanov.dev` -> `127.0.0.1:8011`) that the
Step 6 tunnel runbook adds. Do NOT add a public hostname, do NOT edit any
cloudflared `config.yml`, do NOT reload or restart cloudflared here. If the tunnel
route is not in place yet, the public HTTPS checks below will not resolve; verify
on loopback until Step 6 is done.

## Build strategy

Same as the real app (see `docs/deploy-frontend.md`): build locally and ship the
built `dist` to the box with rsync, keeping the box Node-free and `dist`
gitignored. The exact bytes you tested locally are what serve. `dist` is a derived
artifact, so rebuild and reship whenever the frontend changes.

---

## Deploy steps

Placeholders to settle first: `<VPS_USER>`, `<VPS_HOST>`, `<VPS_PUBLIC_IP>`.

### 0. Baseline
```
curl -fsS -o /dev/null -w "AgentCentral: %{http_code}\n" https://agentcentral.kaloyanyordanov.dev/
ssh <VPS_USER>@<VPS_HOST> "curl -fsS http://127.0.0.1:8011/api/demo-status"   # {"demo":true} (backend already live)
```

### 1. Locally: build with VITE_API_URL UNSET (empty)
On your laptop, in the repo root. The build MUST NOT set `VITE_API_URL`, so
`api.js` calls `/api` relative and same-origin, which is correct for the demo
because the demo backend serves both the SPA and `/api` on the same host.
```
cd frontend
npm ci
npm run build            # produces frontend/dist
cd ..
```
Confirm the build did not bake in an absolute API base (it should not, with
`VITE_API_URL` unset):
```
grep -r "reservations-demo.kaloyanyordanov.dev" frontend/dist && echo "UNEXPECTED: an API base was baked in" || echo "good: relative same-origin API calls"
```
If you keep a laptop `.env` or shell export that sets `VITE_API_URL`, clear it for
this build; otherwise Vite would bake that origin into the bundle.

The demo backend already contains the SPA-serving route (identical to the real
app), so no backend code change or `git pull` on the box is needed for this step:
you are only placing files.

### 2. Ship the built dist to the demo checkout
From your laptop (NOT the box), copy the local build into the demo's own path that
the demo service reads (`/opt/hotel-demo/frontend/dist`):
```
rsync -av --delete frontend/dist/ <VPS_USER>@<VPS_HOST>:/opt/hotel-demo/frontend/dist/
```
`--delete` clears stale hashed assets from previous builds. If rsync is not
available on your laptop, clear and scp instead:
```
ssh <VPS_USER>@<VPS_HOST> "rm -rf /opt/hotel-demo/frontend/dist"
scp -r frontend/dist <VPS_USER>@<VPS_HOST>:/opt/hotel-demo/frontend/dist
```
Then make sure the demo service user can read it:
```
ssh <VPS_USER>@<VPS_HOST> "sudo chown -R hotel-demo:hotel-demo /opt/hotel-demo/frontend/dist"
```
This writes only under `/opt/hotel-demo`. It never touches `/opt/hotel-reservations`.

### 3. Restart the demo service (not the real app, not Agent Central)
`hotel-demo` is our own systemd unit; restarting it makes `serve_spa` pick up the
new `dist`. This does not touch the real `hotel-reservations` service, Agent
Central, or the tunnel.
```
ssh <VPS_USER>@<VPS_HOST> "sudo systemctl restart hotel-demo && systemctl status hotel-demo --no-pager | head -5"
```
`[CHECK AC]`

### 4. Verify (done when)
Loopback always works, even before the tunnel route exists:
```
ssh <VPS_USER>@<VPS_HOST> 'curl -fsS -o /dev/null -w "root: %{http_code} %{content_type}\n" http://127.0.0.1:8011/'   # 200 text/html
```
Public, once the Step 6 tunnel route is in place:
```
curl -fsS https://reservations-demo.kaloyanyordanov.dev/health                                                       # {"status":"ok"}
curl -fsS -o /dev/null -w "root: %{http_code} %{content_type}\n" https://reservations-demo.kaloyanyordanov.dev/        # 200 text/html
curl -fsS -o /dev/null -w "grid: %{http_code} %{content_type}\n" https://reservations-demo.kaloyanyordanov.dev/grid    # 200 text/html
```
Expect `text/html` for `/` and `/grid` (a refresh on `/grid` still loads the app).
Confirm the SPA is actually served, not the "Frontend not built" fallback:
```
curl -fsS https://reservations-demo.kaloyanyordanov.dev/ | grep -qi "Frontend not built" \
  && echo "STILL NOT BUILT: dist missing or unreadable" \
  || echo "SPA served (good)"
```
Then, from your phone or laptop browser: open
`https://reservations-demo.kaloyanyordanov.dev`. It should load the app directly
with NO login, show the demo banner, and list the seeded Bulgarian bookings. That
is the done condition.

Confirm it is still NOT reachable on the public IP (run from your laptop):
```
curl --max-time 5 http://<VPS_PUBLIC_IP>:8011/     # must FAIL to connect
```
`[CHECK AC]`

---

## Rollback

The frontend is only static files served by the already-running demo service, so
backing out is small and never touches the tunnel or the real app.

- Remove `dist` so the demo service falls back to API-only. Non-API routes then
  return a 404 "Frontend not built", which is harmless to the API and to Agent
  Central:
```
ssh <VPS_USER>@<VPS_HOST> "rm -rf /opt/hotel-demo/frontend/dist && sudo systemctl restart hotel-demo"
```
`[CHECK AC]` after.

---

## Before every future demo frontend deploy

1. `cd frontend && npm ci && npm run build`  (with `VITE_API_URL` unset)
2. `rsync -av --delete frontend/dist/ <VPS_USER>@<VPS_HOST>:/opt/hotel-demo/frontend/dist/`
3. `ssh <VPS_USER>@<VPS_HOST> "sudo chown -R hotel-demo:hotel-demo /opt/hotel-demo/frontend/dist"`
4. `sudo systemctl restart hotel-demo`
5. verify, and `[CHECK AC]`
