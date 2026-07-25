from pathlib import Path

import pytest

DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@pytest.fixture
def spa_dist():
    """Ensure a built index.html exists for the SPA-serving test.

    In production the real `vite build` output is present. Here we create a
    minimal stub if it is missing (frontend/dist is gitignored, so it is never
    committed) and remove only what we created.
    """
    index = DIST / "index.html"
    created = False
    if not index.exists():
        DIST.mkdir(parents=True, exist_ok=True)
        index.write_text('<!doctype html><div id="root"></div>', encoding="utf-8")
        created = True
    yield index
    if created:
        index.unlink()
        try:
            DIST.rmdir()
        except OSError:
            pass


def test_health_still_returns_json(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_route_is_not_shadowed_by_the_spa(client):
    # A real API route still answers with its own JSON (401 without a session),
    # not the SPA's HTML. This is the guard against the catch-all eating the API.
    response = client.get("/api/reservations")
    assert response.status_code == 401
    assert "text/html" not in response.headers["content-type"]


def test_unmatched_api_path_is_404_not_html(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert "text/html" not in response.headers["content-type"]


def test_non_api_route_serves_index_html(client, spa_dist):
    # A client-side route (survives a refresh) returns the SPA entry point.
    response = client.get("/reservations")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '<div id="root">' in response.text
