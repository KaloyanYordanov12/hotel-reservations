def _book(api_client, **overrides):
    body = {
        "room_id": "3.3",
        "guest_name": "Ivan Petrov",
        "guest_phone": "+359888123456",
        "check_in": "2026-08-10",
        "check_out": "2026-08-15",
        "num_guests": 2,
    }
    body.update(overrides)
    response = api_client.post("/api/reservations", json=body)
    assert response.status_code == 201
    return response.json()


def _by_room(entries):
    return {entry["room_id"]: entry for entry in entries}


# --- point-in-range availability --------------------------------------------


DISPLAY_ORDER = ["3.2", "3.3", "3.4", "4.1", "4.2", "4.3", "4.4", "A3", "A8", "A11"]


def test_availability_returns_rooms_in_display_order(api_client):
    entries = api_client.get(
        "/api/availability",
        params={"check_in": "2026-08-10", "check_out": "2026-08-15"},
    ).json()
    assert [entry["room_id"] for entry in entries] == DISPLAY_ORDER
    assert [entry["display_order"] for entry in entries] == list(range(1, 11))


def test_grid_returns_rooms_in_display_order(api_client):
    grid = api_client.get(
        "/api/availability/grid", params={"from": "2026-08-10", "to": "2026-08-12"}
    ).json()
    assert [room["room_id"] for room in grid["rooms"]] == DISPLAY_ORDER
    assert [room["display_order"] for room in grid["rooms"]] == list(range(1, 11))


def test_all_rooms_free_on_empty_range(api_client):
    entries = api_client.get(
        "/api/availability",
        params={"check_in": "2026-08-10", "check_out": "2026-08-15"},
    ).json()
    assert len(entries) == 10
    assert all(entry["available"] for entry in entries)
    assert all(entry["reservation"] is None for entry in entries)


def test_booked_room_is_flagged(api_client):
    reservation = _book(api_client)
    entries = _by_room(
        api_client.get(
            "/api/availability",
            params={"check_in": "2026-08-10", "check_out": "2026-08-15"},
        ).json()
    )
    assert entries["3.3"]["available"] is False
    assert entries["3.3"]["reservation"]["id"] == reservation["id"]
    assert entries["3.4"]["available"] is True
    assert entries["3.4"]["reservation"] is None


def test_same_day_turnover_shows_room_free(api_client):
    # Existing guest checks out on 08-10; a new stay starting 08-10 does not clash.
    _book(api_client, check_in="2026-08-05", check_out="2026-08-10")
    entries = _by_room(
        api_client.get(
            "/api/availability",
            params={"check_in": "2026-08-10", "check_out": "2026-08-15"},
        ).json()
    )
    assert entries["3.3"]["available"] is True
    assert entries["3.3"]["reservation"] is None


def test_type_and_standard_occupancy_present(api_client):
    entries = _by_room(
        api_client.get(
            "/api/availability",
            params={"check_in": "2026-08-10", "check_out": "2026-08-15"},
        ).json()
    )
    assert entries["3.3"]["type"] == "double"
    assert entries["3.3"]["standard_occupancy"] == 2
    assert entries["A3"]["type"] == "apartment"
    assert entries["A3"]["standard_occupancy"] == 4


def test_availability_rejects_backwards_range(api_client):
    response = api_client.get(
        "/api/availability",
        params={"check_in": "2026-08-15", "check_out": "2026-08-10"},
    )
    assert response.status_code == 422


# --- grid -------------------------------------------------------------------


def test_grid_marks_booked_nights(api_client):
    reservation = _book(api_client, check_in="2026-08-11", check_out="2026-08-13")
    grid = api_client.get(
        "/api/availability/grid", params={"from": "2026-08-10", "to": "2026-08-14"}
    ).json()

    assert grid["days"] == ["2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"]

    rooms = {room["room_id"]: room for room in grid["rooms"]}
    assert len(rooms) == 10

    cells = {cell["date"]: cell for cell in rooms["3.3"]["days"]}
    assert cells["2026-08-10"]["available"] is True
    assert cells["2026-08-11"]["available"] is False
    assert cells["2026-08-12"]["available"] is False
    assert cells["2026-08-13"]["available"] is True  # checkout day is free again
    assert cells["2026-08-11"]["reservation_id"] == reservation["id"]

    # A room with no bookings is free every night.
    assert all(cell["available"] for cell in rooms["3.4"]["days"])


def test_grid_includes_type_and_standard_occupancy(api_client):
    grid = api_client.get(
        "/api/availability/grid", params={"from": "2026-08-10", "to": "2026-08-12"}
    ).json()
    rooms = {room["room_id"]: room for room in grid["rooms"]}
    assert rooms["3.2"]["type"] == "triple"
    assert rooms["3.2"]["standard_occupancy"] == 3


def test_grid_rejects_backwards_range(api_client):
    response = api_client.get(
        "/api/availability/grid", params={"from": "2026-08-15", "to": "2026-08-10"}
    )
    assert response.status_code == 422
