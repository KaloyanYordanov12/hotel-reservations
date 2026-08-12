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


# --- CORS: demo-only, scoped to the configured frontend origin ----------------
#
# CORS is installed at app import based on the process env, so it cannot be
# monkeypatched onto the singleton app after the fact. Instead we drive the same
# installer main.py uses against a throwaway app, with a Settings built to order.
# That tests the real safety property: the real app (demo off) gets no CORS, and
# demo mode grants access only to the exact configured origin.


def _cors_client(**settings_overrides):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.main import _install_demo_cors

    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    _install_demo_cors(app, _build(**settings_overrides))
    return TestClient(app)


def test_demo_allowed_origins_parsing():
    assert _build(
        demo_frontend_origin="https://a, https://b ,"
    ).demo_allowed_origins == ["https://a", "https://b"]
    assert _build(demo_frontend_origin="").demo_allowed_origins == []
    assert _build().demo_allowed_origins == []


def test_cors_allows_configured_demo_origin_in_demo_mode():
    client = _cors_client(demo_mode="1", demo_frontend_origin="https://demo.example")
    r = client.get("/api/ping", headers={"Origin": "https://demo.example"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://demo.example"


def test_cors_preflight_succeeds_for_demo_origin():
    client = _cors_client(demo_mode="1", demo_frontend_origin="https://demo.example")
    r = client.options(
        "/api/ping",
        headers={
            "Origin": "https://demo.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "https://demo.example"


def test_cors_does_not_allow_an_unlisted_origin():
    client = _cors_client(demo_mode="1", demo_frontend_origin="https://demo.example")
    r = client.get("/api/ping", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") != "https://evil.example"


def test_no_cors_for_the_real_app_even_if_origin_is_set():
    # demo off: the real app installs no CORS at all, whatever the origin var says.
    client = _cors_client(demo_mode="0", demo_frontend_origin="https://demo.example")
    r = client.get("/api/ping", headers={"Origin": "https://demo.example"})
    assert "access-control-allow-origin" not in r.headers


def test_no_cors_in_demo_mode_without_a_configured_origin():
    # Fail-secure: demo on but no origin set grants no cross-origin access.
    client = _cors_client(demo_mode="1", demo_frontend_origin="")
    r = client.get("/api/ping", headers={"Origin": "https://demo.example"})
    assert "access-control-allow-origin" not in r.headers
