from fastapi import Depends, FastAPI
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
