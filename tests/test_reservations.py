from decimal import Decimal

MISSING_UUID = "00000000-0000-0000-0000-000000000000"


def _payload(**overrides):
    body = {
        "room_id": "3.3",
        "guest_name": "Ivan Petrov",
        "guest_phone": "+359888123456",
        "check_in": "2026-08-10",
        "check_out": "2026-08-15",
        "num_guests": 2,
    }
    body.update(overrides)
    return body


# --- create -----------------------------------------------------------------


def test_create_happy_path(api_client):
    response = api_client.post("/api/reservations", json=_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["room_id"] == "3.3"
    assert body["guest_name"] == "Ivan Petrov"
    assert body["parking"] is False
    assert Decimal(str(body["deposit_paid"])) == Decimal("0")
    assert body["id"]
    assert body["created_at"]
    assert body["updated_at"]


def test_create_allows_more_guests_than_standard_occupancy(api_client):
    # Room 3.3 has standard_occupancy 2. She routinely puts more people in a
    # room than it is intended for, and the system must not argue.
    response = api_client.post("/api/reservations", json=_payload(num_guests=6))
    assert response.status_code == 201
    assert response.json()["num_guests"] == 6


def test_create_unknown_room_is_404(api_client):
    response = api_client.post("/api/reservations", json=_payload(room_id="Z9"))
    assert response.status_code == 404


def test_create_zero_guests_is_422(api_client):
    response = api_client.post("/api/reservations", json=_payload(num_guests=0))
    assert response.status_code == 422


def test_create_negative_deposit_is_422(api_client):
    response = api_client.post(
        "/api/reservations", json=_payload(deposit_paid="-5.00")
    )
    assert response.status_code == 422


def test_create_backwards_dates_is_422(api_client):
    response = api_client.post(
        "/api/reservations",
        json=_payload(check_in="2026-08-15", check_out="2026-08-10"),
    )
    assert response.status_code == 422


def test_create_overlap_is_409_with_readable_body(api_client):
    api_client.post("/api/reservations", json=_payload())
    response = api_client.post(
        "/api/reservations",
        json=_payload(check_in="2026-08-12", check_out="2026-08-18"),
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["room_id"] == "3.3"
    assert "2026-08-10" in detail["message"]
    assert "2026-08-15" in detail["message"]


def test_create_same_day_turnover_is_allowed(api_client):
    api_client.post("/api/reservations", json=_payload())
    response = api_client.post(
        "/api/reservations",
        json=_payload(check_in="2026-08-15", check_out="2026-08-20"),
    )
    assert response.status_code == 201


# --- list -------------------------------------------------------------------


def test_list_is_ordered_by_check_in(api_client):
    api_client.post("/api/reservations", json=_payload(check_in="2026-08-20", check_out="2026-08-25"))
    api_client.post("/api/reservations", json=_payload(room_id="3.4", check_in="2026-08-10", check_out="2026-08-15"))
    body = api_client.get("/api/reservations").json()
    assert [r["check_in"] for r in body] == ["2026-08-10", "2026-08-20"]


def test_list_from_to_window(api_client):
    api_client.post("/api/reservations", json=_payload())  # 08-10 to 08-15
    assert len(api_client.get("/api/reservations", params={"from": "2026-08-01", "to": "2026-08-31"}).json()) == 1
    assert len(api_client.get("/api/reservations", params={"from": "2026-08-20"}).json()) == 0
    assert len(api_client.get("/api/reservations", params={"to": "2026-08-05"}).json()) == 0


def test_list_deposit_paid_filter(api_client):
    api_client.post("/api/reservations", json=_payload(room_id="3.3"))  # deposit 0
    api_client.post("/api/reservations", json=_payload(room_id="3.4", deposit_paid="50.00"))

    owes = api_client.get("/api/reservations", params={"deposit_paid": "false"}).json()
    assert [r["room_id"] for r in owes] == ["3.3"]

    paid = api_client.get("/api/reservations", params={"deposit_paid": "true"}).json()
    assert [r["room_id"] for r in paid] == ["3.4"]


# --- get by id --------------------------------------------------------------


def test_get_by_id_found(api_client):
    created = api_client.post("/api/reservations", json=_payload()).json()
    response = api_client.get(f"/api/reservations/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_by_id_not_found(api_client):
    assert api_client.get(f"/api/reservations/{MISSING_UUID}").status_code == 404


# --- update -----------------------------------------------------------------


def test_patch_happy_path(api_client):
    created = api_client.post("/api/reservations", json=_payload()).json()
    response = api_client.patch(
        f"/api/reservations/{created['id']}", json={"deposit_paid": "40.00"}
    )
    assert response.status_code == 200
    assert Decimal(str(response.json()["deposit_paid"])) == Decimal("40.00")


def test_patch_not_found(api_client):
    response = api_client.patch(
        f"/api/reservations/{MISSING_UUID}", json={"deposit_paid": "10.00"}
    )
    assert response.status_code == 404


def test_patch_into_conflict_is_409(api_client):
    first = api_client.post("/api/reservations", json=_payload()).json()  # 08-10 to 08-15
    api_client.post("/api/reservations", json=_payload(check_in="2026-08-20", check_out="2026-08-25"))

    response = api_client.patch(
        f"/api/reservations/{first['id']}", json={"check_out": "2026-08-22"}
    )
    assert response.status_code == 409
    assert response.json()["detail"]["room_id"] == "3.3"


def test_patch_backwards_dates_hits_db_constraint_422(api_client):
    created = api_client.post("/api/reservations", json=_payload()).json()  # check_in 08-10
    # Only check_out is sent, so the schema cannot compare the pair; the database
    # valid_dates constraint catches it and it comes back 422, not 500.
    response = api_client.patch(
        f"/api/reservations/{created['id']}", json={"check_out": "2026-08-08"}
    )
    assert response.status_code == 422


# --- delete -----------------------------------------------------------------


def test_delete_happy_path(api_client):
    created = api_client.post("/api/reservations", json=_payload()).json()
    assert api_client.delete(f"/api/reservations/{created['id']}").status_code == 204
    assert api_client.get(f"/api/reservations/{created['id']}").status_code == 404


def test_delete_not_found(api_client):
    assert api_client.delete(f"/api/reservations/{MISSING_UUID}").status_code == 404
