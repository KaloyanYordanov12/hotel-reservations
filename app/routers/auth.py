"""Single shared password auth.

One password, one signed session cookie. Not a user table, not OAuth, not JWT.
The session cookie is signed and managed by Starlette's SessionMiddleware (see
main.py); this module verifies the password, marks the session authenticated,
and guards the protected routes.
"""
import time
from collections import defaultdict

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.schemas import LoginRequest

router = APIRouter(prefix="/api", tags=["auth"])

# In-memory rate limit: five attempts per minute per IP. In-memory is fine; this
# runs as a single uvicorn process for one user, and the limit only exists to
# blunt brute force, not to coordinate across machines.
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 60.0
_attempts: dict[str, list[float]] = defaultdict(list)


def reset_rate_limit() -> None:
    """Clear the attempt log. Used by tests so they do not trip each other."""
    _attempts.clear()


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    recent = [t for t in _attempts[ip] if now - t < _WINDOW_SECONDS]
    _attempts[ip] = recent
    if len(recent) >= _MAX_ATTEMPTS:
        return True
    recent.append(now)
    return False


def _password_ok(password: str) -> bool:
    # config.py validates APP_PASSWORD_HASH is a parseable bcrypt hash at startup,
    # so this checkpw can no longer receive a malformed hash and the except is
    # unreachable in practice. It is kept so that if that startup check is ever
    # weakened, a bad hash still yields a failed login rather than a 500.
    try:
        return bcrypt.checkpw(password.encode(), settings.app_password_hash.encode())
    except ValueError:
        return False


def require_authenticated(request: Request) -> None:
    """Guard for the protected routes. 401 unless the session is authenticated.

    In demo mode (the public, login-less deployment) every request is let
    through as the demo user. DEMO_MODE is fail-secure in config.py: it is off
    unless explicitly turned on, so the real app is unaffected and this branch
    is dead code there. This is the ONLY place auth changes for the demo; the
    login endpoint still exists, it is simply not needed.
    """
    if settings.demo_mode:
        return
    if not request.session.get("authenticated"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )


@router.get("/demo-status")
def demo_status():
    """Public. Lets the frontend decide whether to show the demo banner. It
    reveals only whether this deployment is the demo, which is not a secret."""
    return {"demo": settings.demo_mode}


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    ip = request.client.host if request.client else "unknown"
    if _rate_limited(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Wait a minute and try again.",
        )
    if not _password_ok(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
        )
    request.session["authenticated"] = True
    return {"status": "ok"}


@router.post("/logout", dependencies=[Depends(require_authenticated)])
def logout(request: Request):
    request.session.clear()
    return {"status": "ok"}
