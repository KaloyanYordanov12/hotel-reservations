from app.config import settings

from tests.conftest import TEST_PASSWORD


def test_health_is_open_without_auth(auth_client):
    assert auth_client.get("/health").status_code == 200


def test_unauthenticated_request_is_401(auth_client):
    assert auth_client.get("/api/reservations").status_code == 401


def test_login_then_request_succeeds(auth_client):
    assert auth_client.post("/api/login", json={"password": TEST_PASSWORD}).status_code == 200
    assert auth_client.get("/api/reservations").status_code == 200


def test_bad_password_is_401(auth_client):
    assert auth_client.post("/api/login", json={"password": "wrong"}).status_code == 401


def test_session_cookie_returned_and_sent_on_next_request(auth_client):
    # The COOKIE_SECURE=False case. If the cookie were Secure, httpx would store
    # it against http://testserver and then silently never send it, and the
    # request below would be 401. This asserts the conditional works.
    assert settings.cookie_secure is False

    login = auth_client.post("/api/login", json={"password": TEST_PASSWORD})
    assert login.status_code == 200
    assert "session" in auth_client.cookies

    assert auth_client.get("/api/reservations").status_code == 200


def test_logout_clears_session(auth_client):
    auth_client.post("/api/login", json={"password": TEST_PASSWORD})
    assert auth_client.get("/api/reservations").status_code == 200

    assert auth_client.post("/api/logout").status_code == 200
    assert auth_client.get("/api/reservations").status_code == 401


def test_logout_requires_auth(auth_client):
    assert auth_client.post("/api/logout").status_code == 401


def test_rate_limited_after_five_attempts(auth_client):
    for _ in range(5):
        assert auth_client.post("/api/login", json={"password": "wrong"}).status_code == 401
    assert auth_client.post("/api/login", json={"password": "wrong"}).status_code == 429
