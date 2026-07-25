# Hotel Reservations - Phase 2 Brief: React Frontend

The backend is deployed and live at `reservations.kaloyanyordanov.dev`. This phase builds the interface my mother actually uses. Read `CLAUDE.md` first; every standing rule there still applies, and this brief adds frontend-specific ones.

## Who this is for, and the one thing that matters

The only user is my mother. She opens this on her phone, usually while already on the phone with a guest who is asking "do you have anything free from the 20th to the 24th?" Every decision in this phase serves that one moment: she needs to answer that question in seconds, one-handed, on a small screen.

The system this replaces is a paper notebook. A notebook is instant, never argues, and never shows a spinner. If this app is slower or fussier than flipping to a page, she goes back to the notebook and never opens it again. Speed and clarity beat everything, including looking impressive. It can be both, and it should be, but when they conflict, fast and legible wins.

## The shape, decided. Do not relitigate.

- **Primary screen is a date-range search, not a grid.** Two date fields, prefilled, and a list of which rooms are free for that range. This is the on-the-phone moment. A guest asks a question with two dates in it; she reads back an answer, she does not scan a grid and compute it. This maps onto `GET /api/availability?check_in=&check_out=`, which already returns free/booked per room in one query.
- **The grid is a SECOND tab, for planning at the laptop.** "What does next week look like overall" is a real question, just not the phone-with-a-guest one. On a laptop's width the grid is genuinely useful; on a 380px phone it is a horizontal-scrolling squint. It maps onto `GET /api/availability/grid?from=&to=`.
- **Booking is a continuation of search.** She searches a range, sees room 3.3 is free, taps it, and the booking form opens with the dates and room ALREADY filled in. She types only the guest name and phone. The fewest possible taps, because the search she just did carries its context into the form. Booking is not a separate destination she navigates to; it falls out of the thing she was already doing.

## Stack, decided

- **Vite + React.** Not Next.js. There is a separate FastAPI backend, so there is no server-rendering need, no server components, no framework routing layer to fight. Vite builds plain static files, which is exactly what we want to serve. Do not introduce Next.js, Remix, or any meta-framework.
- **Plain React with hooks.** No Redux, no MobX, no state-management library. This app has one user and a handful of screens. `useState`, `useReducer`, and the URL are enough. Do not add a state library.
- **React Router** for the two or three routes (search, grid, maybe a reservations list). That is the one routing dependency, and it earns its place.
- **Fetch, or a thin wrapper, for API calls.** Not axios unless you make the case. A small `api.js` that wraps `fetch`, handles the session cookie (it is sent automatically, same origin, see deployment below), and centralizes error handling.
- **CSS: your call between plain CSS modules and Tailwind.** If Tailwind, set it up properly with the frontend-design skill's tokens. Do not pull in a component library (MUI, Chakra, Ant). Ten screens do not need one, and they make everything look like everyone else, which is the opposite of what a portfolio piece wants. Read the `frontend-design` skill before writing any component.

## How it is served in production. Read this before Step 1, it shapes everything.

The frontend is built to static files (`vite build` produces a `dist/` folder) and served by the SAME FastAPI app, behind the SAME Cloudflare tunnel, at the SAME origin. Not a second Node process, not a separate subdomain.

Why this matters and is not just tidiness:

- **The session cookie is `SameSite=Lax` and set for `reservations.kaloyanyordanov.dev`.** If the frontend were served from a different origin, the cookie would not be sent with API calls and auth would silently break, which is the exact class of bug that cost an evening in Phase 1. Same origin means the cookie just works, no CORS, no credentials dance.
- **No second process to run, deploy, or keep alive.** FastAPI already runs under systemd. It serves the API under `/api/*` and the built React app for everything else. One service, one tunnel route, done.

So this phase includes a small backend change: FastAPI mounts the built `dist/` as static files and serves `index.html` for any non-API route (so client-side routing works on refresh). That is the only backend code this phase touches, and it is in Step 6.

## Standing rules for this phase

- Every rule in `CLAUDE.md` applies. No em-dashes. One commit per step, working state before each commit. You do not push; I push.
- Do not run `npm install` of anything not named in this brief without stopping to ask. The npm ecosystem is where scope creep and supply-chain risk both live. Every dependency is a decision.
- **Pin dependencies.** `package.json` gets exact versions, no `^` or `~`. Commit `package-lock.json`. The reasoning is identical to the Python lock in Phase 1: the build must resolve the same in three weeks as today.
- The dev server talks to the LOCAL backend (`http://localhost:8000` or wherever Phase 1 runs via uvicorn), through a Vite proxy so the origin looks the same in dev as in prod. Do not point the dev frontend at the live VPS.
- Mobile-first, always. Design the phone layout first, let the laptop layout be the enhancement. Not the other way around.
- Validation philosophy is unchanged and now matters in the UI too: the form NEVER blocks her. `num_guests` has no max. Over-occupancy is fine. The only things the form prevents are the physically impossible (check-out before check-in) and empty required fields. Everything else, she can submit, and the backend is the final judge. If the backend returns a 409 (double-booking) or 422, show it clearly and let her fix it; do not try to prevent it client-side by disabling things.

---

## Step 0: Recon and plan. NO CODE.

Read and report. Write nothing.

1. Confirm the repo state: current branch, clean tree, backend structure.
2. Confirm Node and npm versions available on my machine (`node --version`, `npm --version`). Report them. Flag if Node is older than 20, since Vite and modern React want a current Node.
3. Read the Phase 1 API surface from the routers: list every endpoint the frontend will call, with its method, path, query params, and response shape. Specifically `/api/reservations` (all verbs), `/api/availability`, `/api/availability/grid`, `/api/login`, `/api/logout`. I want the actual contract, read from the code, not assumed.
4. Propose where the frontend lives in the repo: a `frontend/` directory at the root, alongside `app/`. Confirm this does not collide with anything.
5. List the screens you plan to build and the components each needs, at one level of depth. Keep it short. I approve the plan before you build.

Then stop.

---

## Step 1: Scaffold the Vite app

- `npm create vite@latest frontend -- --template react` (JavaScript, not TypeScript, unless you make a short case for TS and I agree; for a solo portfolio app of this size, plain JS is defensible and faster to move in).
- Pin every dependency to an exact version. Remove the `^`s that Vite's template adds.
- One health-check component: fetch `/api/health` through the Vite proxy and render the result, just to prove the dev server, the proxy, and the backend all talk. This is the frontend equivalent of Phase 1's `/health` test: the smallest thing that proves the pipe works.
- Configure the Vite dev proxy so `/api/*` forwards to the local backend, same-origin illusion.
- A `.gitignore` for `node_modules`, `dist`, and the Vite cache.

Done when: `npm run dev` serves the app, the health component shows the backend responding, and `npm run build` produces a `dist/`.

Commit: `feat: scaffold Vite React frontend with dev proxy`

---

## Step 2: The API client and auth gate

- `src/api.js`: a thin wrapper over `fetch`. Every call includes `credentials: "include"` so the session cookie rides along. Centralize: base path, JSON parsing, and error handling that distinguishes 401 (not logged in), 409 (conflict), 422 (validation), and everything else.
- A login screen: one password field, submit to `POST /api/login`. On success, the cookie is set and we route to the search screen. On 401, show "wrong password" plainly.
- An auth gate: if any API call returns 401, route back to login. She logs in once and the 180-day cookie keeps her in, so this is rare, but it must be handled, not crash.
- Do NOT store the password, or any token, in localStorage or anywhere. The cookie is the whole auth mechanism and the browser handles it. There is nothing for the app to hold.

Done when: logging in from the UI works against the local backend, a wrong password shows an error, and hitting a protected screen while logged out sends you to login.

Commit: `feat: API client and password login`

---

## Step 3: The search screen (the primary screen)

This is the one that matters. Build it well.

- Two date inputs: check-in and check-out. Prefill check-in to today and check-out to tomorrow, or today +1, so the common "someone wants tonight" case is one tap.
- On change (or a search button, your call, but consider that fewer taps is better), call `GET /api/availability?check_in=&check_out=`.
- Render the result as a clear list: free rooms grouped or marked distinctly from booked ones. For a free room, show the room id and its type and standard_occupancy (display only, remember, never a limit). For a booked room, showing it as booked with the blocking guest name is useful, she may be looking at whether she can move someone.
- Same-day turnover must read correctly: a room whose previous guest checks out on her check-in date is FREE. The backend already handles this; make sure the UI reflects what the backend says rather than recomputing it.
- Each free room is tappable, and tapping it is what leads into booking (Step 5).
- Fast. This screen opening and answering is the entire product. No heavy spinner for a sub-100ms local call; show results the instant they arrive.

Done when: entering a range shows correct free/booked rooms on a phone-width screen, turnover reads as free, and it is quick.

Commit: `feat: date-range availability search`

---

## Step 4: Reservations list and deposit view

- A screen listing reservations, ordered by check-in, calling `GET /api/reservations` with optional date filters.
- Deposit status visible at a glance: who has paid a deposit and who has not (`deposit_paid` filter on the endpoint, which you built). A simple, unmissable visual distinction, a colored dot or a label, not a subtle one. This is a real task she does: chasing who still owes.
- Each reservation is tappable to edit (Step 5).

Done when: the list shows reservations with clear deposit status, and the "who still owes" view is one tap or filter away.

Commit: `feat: reservations list with deposit status`

---

## Step 5: The booking form (create and edit, one component)

- One form component that handles both creating and editing. Fields: guest name, guest phone, room, check-in, check-out, num_guests, parking, deposit_paid, note.
- **Pre-fill from context.** Reached from the search screen by tapping a free room, it opens with room, check-in, and check-out already set. She types name and phone. Reached from the reservations list, it opens populated with that reservation for editing.
- Client-side validation is MINIMAL, per the standing rule: required fields present, check-out after check-in. Nothing else. `num_guests` has no max. Do not disable submit based on occupancy or any judgment call.
- On submit, `POST` (create) or `PATCH` (edit). Handle the responses honestly:
  - 201/200: success, route back to where she came from.
  - 409: the room got booked out from under her (or she picked a clashing range). Show the conflict message the backend returns, which names the clashing dates and guest, and let her adjust. Do not swallow it.
  - 422: show the field problem.
- Delete: on the edit form, a delete action calling `DELETE /api/reservations/{id}`, with a confirm step, since this is destructive and she might fat-finger it on a phone.

Done when: she can create a booking from a search result in a handful of taps, edit an existing one, and delete with confirmation; conflicts and validation errors show clearly and are recoverable.

Commit: `feat: create, edit, and delete booking form`

---

## Step 6: The grid tab, and serving the build from FastAPI

Two things, because the grid is small and the serving change is the deploy-readiness piece.

**The grid tab:**
- A second tab/route rendering `GET /api/availability/grid?from=&to=`, a room-by-day matrix.
- This one is allowed to be laptop-first. On a phone it can be a reduced or scrollable view; on a laptop it is the wide planning grid. Do not spend the effort here that you spent on the search screen; this is the secondary view.

**Serving the built frontend from FastAPI (the only backend change this phase makes):**
- Mount `frontend/dist` as static files in the FastAPI app.
- Serve `index.html` for any route that is not under `/api/*` and not a real static file, so client-side routing survives a page refresh (she refreshes on `/grid`, she should get the grid, not a 404).
- Keep `/api/*` and `/health` exactly as they are. The catch-all for the SPA must not shadow them; order the routes so the API wins.
- A test: a non-API route returns the `index.html`, and `/api/health` still returns JSON. This guards against the catch-all eating the API, which is the one way this change can break everything.

Done when: `vite build` output is served by the local FastAPI app at `/`, client-side routes survive refresh, and every API route still works.

Commit: `feat: grid view and serve built frontend from FastAPI`

---

## Step 7: Deploy the frontend to the VPS

Write, do not run, the same way Phase 1's deploy step worked. I run it on the box.

- Update `docs/deploy.md` (or a new `docs/deploy-frontend.md`) with the steps: pull the repo on the VPS, `npm ci` and `npm run build` in `frontend/` (or build locally and commit `dist`, your recommendation, state the tradeoff, note that building on the box needs Node installed there which it currently is not).
- No new tunnel route, no cloudflared change. This is the payoff of same-origin: the frontend ships through the route that already exists. This step must not touch the tunnel at all. Say so explicitly in the runbook.
- Restart `hotel-reservations` to pick up the static mount.
- The `[CHECK AC]` discipline still applies for anything that runs on the box, though this step should touch nothing Agent Central depends on.

Done when: the runbook is written and handed to me. I run it, and `https://reservations.kaloyanyordanov.dev` serves the actual app, and my mother can log in and search availability from her phone.

Commit: `chore: frontend deploy runbook`

---

## Out of scope for Phase 2. Do not build.

- No guest-facing anything. This is her internal tool.
- No online booking, no public calendar, no availability shown to anyone but her.
- No notifications, email, or SMS.
- No analytics, no charts, no occupancy dashboards.
- No multi-user, no accounts, no roles. One password, already built.
- No TypeScript migration of the backend, no rewrites.
- No PWA/offline/service-worker work in this phase. A home-screen icon (manifest) is a nice small touch and allowed if cheap, but offline sync is a rabbit hole and out of scope.
- No dark mode unless it is nearly free with your CSS choice.
- No animations beyond what makes state changes legible. She is not here to be delighted, she is here to answer a phone.

## Report format for each step

Same as Phase 1: what you read, what you changed file by file, the test or manual-check output, the commit hash and message, and anything this brief got wrong. Then stop.
