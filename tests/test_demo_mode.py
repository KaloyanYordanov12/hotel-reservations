"""DEMO_MODE is fail-secure: auth is disabled ONLY when it is explicitly on.

The same codebase runs my mother's real app and the public demo. These tests
are the safety net that proves a wrong or missing DEMO_MODE never strips auth
off the real deployment. The demo bypass lives in require_authenticated; here we
drive it through a real protected route.
"""
import pytest

from app.config import Settings, settings

from tests.test_config import _VALID


def _build(**overrides) -> Settings:
    return Settings(**{**_VALID, **overrides})


# --- the parser: only explicit true tokens turn demo on ----------------------


@pytest.mark.parametrize("value", ["1", "true", "TRUE", "True", "yes", "  yes  "])
def test_explicit_true_values_enable_demo(value):
    assert _build(demo_mode=value).demo_mode is True


@pytest.mark.parametrize(
    "value", ["0", "false", "False", "no", "off", "", "  ", "banana", "2"]
)
def test_everything_else_is_off(value):
    # Fail secure: anything that is not an explicit true token reads as OFF,
    # including garbage that pydantic's bool coercion would otherwise reject.
    assert _build(demo_mode=value).demo_mode is False


def test_unset_defaults_off():
    # No DEMO_MODE passed at all: the field default (False) stands, auth on.
    assert _build().demo_mode is False


# --- the guard: bypass only when demo is on ----------------------------------


def test_unset_demo_mode_still_401(auth_client):
    # The real app, unchanged: no session, protected route rejects.
    assert settings.demo_mode is False
    assert auth_client.get("/api/reservations").status_code == 401


@pytest.mark.parametrize("value", [False, "0", "false", ""])
def test_falsey_demo_mode_still_401(auth_client, monkeypatch, value):
    # Whatever a misconfigured env resolves to, if it is not truly on the login
    # wall stays up. We resolve the value through the same parser the app uses,
    # then assert the guard still blocks.
    monkeypatch.setattr(settings, "demo_mode", _build(demo_mode=value).demo_mode)
    assert settings.demo_mode is False
    assert auth_client.get("/api/reservations").status_code == 401


def test_demo_mode_on_reaches_protected_route_without_session(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    # No login call anywhere: the guard lets it through as the demo user.
    assert auth_client.get("/api/reservations").status_code == 200


# --- the public status endpoint ----------------------------------------------


def test_demo_status_reports_off_by_default(auth_client):
    assert auth_client.get("/api/demo-status").json() == {"demo": False}


def test_demo_status_reports_on_in_demo_mode(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    assert auth_client.get("/api/demo-status").json() == {"demo": True}


def test_demo_status_is_public_without_session(auth_client):
    # It must be reachable so the frontend can decide to show the banner before
    # anyone logs in. It is not under the auth guard.
    assert auth_client.get("/api/demo-status").status_code == 200
