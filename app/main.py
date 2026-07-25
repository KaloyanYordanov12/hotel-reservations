from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.routers import auth, availability, reservations
from app.routers.auth import require_authenticated

app = FastAPI(title="Hotel Reservations")

# Signed session cookie: HttpOnly (always, set by SessionMiddleware), SameSite
# Lax, 180 day lifetime so she logs in once on her phone and never again. Secure
# is conditional on COOKIE_SECURE, which is True in production. See config.py.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    max_age=180 * 24 * 60 * 60,
    same_site="lax",
    https_only=settings.cookie_secure,
)

# /api/login stays open; everything else under /api requires a session. /health
# is not under /api and stays open for uptime checks.
app.include_router(auth.router)
app.include_router(
    reservations.router, dependencies=[Depends(require_authenticated)]
)
app.include_router(
    availability.router, dependencies=[Depends(require_authenticated)]
)


@app.get("/health")
def health():
    return {"status": "ok"}


# The built React app (frontend/dist) is served by this same FastAPI process, at
# the same origin, so the session cookie just works and there is no second
# service or tunnel route. This catch-all is registered LAST, after /health and
# every /api/* route, so the API is matched first and is never shadowed. It
# serves a real built file when the path points at one, otherwise index.html, so
# a client-side route survives a page refresh. It is unauthenticated on purpose:
# she must be able to load the app in order to log in.
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    # An unmatched API or health path must be a real 404, never HTML.
    if full_path.startswith("api/") or full_path == "health":
        raise HTTPException(status_code=404)
    candidate = (DIST / full_path).resolve()
    # Serve a real built asset when the path points at one, and only if it stays
    # inside DIST (guards against path traversal).
    if full_path and candidate.is_file() and DIST in candidate.parents:
        return FileResponse(candidate)
    index = DIST / "index.html"
    if index.is_file():
        return FileResponse(index)
    raise HTTPException(status_code=404, detail="Frontend not built")
