from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
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


def _install_demo_cors(app: FastAPI, settings) -> None:
    """Allow the demo frontend's origin to call this backend, in demo mode ONLY.

    The demo frontend is a separate Cloudflare Pages project on its own origin, so
    its browser calls are cross-origin and need CORS response headers. This is
    added ONLY when DEMO_MODE is on AND DEMO_FRONTEND_ORIGIN is set, and only for
    those exact origins. The real app calls its API same-origin, adds no CORS
    middleware at all, and is unaffected. Fail-secure: demo mode without a
    configured origin grants no cross-origin access.
    """
    if not (settings.demo_mode and settings.demo_allowed_origins):
        return
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.demo_allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        # The frontend fetch sends credentials: "include"; a credentialed
        # cross-origin request needs this true AND a specific (non-wildcard)
        # origin, which we have. The demo sets no cookies, so this grants nothing
        # beyond letting the browser read the response from the trusted origin.
        allow_credentials=True,
    )


# Added at import: reflects this process's env. The demo deployment sets DEMO_MODE
# and DEMO_FRONTEND_ORIGIN and gets CORS; the real app sets neither and does not.
_install_demo_cors(app, settings)

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
