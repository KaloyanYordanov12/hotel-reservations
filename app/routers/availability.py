"""Availability: the primary screen my mother reads while on the phone.

Both endpoints answer in one query with no N+1, and both use the same half-open
overlap logic as the exclusion constraint (existing.check_in < requested.check_out
AND requested.check_in < existing.check_out) so availability can never disagree
with what a booking is actually allowed to do. Same-day turnover reads as free.
"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Reservation, Room
from app.schemas import (
    AvailabilityGrid,
    GridCell,
    GridRoom,
    ReservationRead,
    RoomAvailability,
)

router = APIRouter(prefix="/api/availability", tags=["availability"])


def _require_range(start: date, end: date) -> None:
    if end <= start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="check_out must be after check_in",
        )


@router.get("", response_model=list[RoomAvailability])
def availability(
    check_in: date = Query(...),
    check_out: date = Query(...),
    db: Session = Depends(get_db),
):
    _require_range(check_in, check_out)

    # One row per room via DISTINCT ON: the earliest reservation overlapping the
    # requested stay, or NULL when the room is free. display_order is unique per
    # room, so DISTINCT ON it yields one row per room and sorts them for display.
    stmt = (
        select(Room, Reservation)
        .outerjoin(
            Reservation,
            and_(
                Reservation.room_id == Room.id,
                Reservation.check_in < check_out,
                check_in < Reservation.check_out,
            ),
        )
        .order_by(Room.display_order, Reservation.check_in)
        .distinct(Room.display_order)
    )

    return [
        RoomAvailability(
            room_id=room.id,
            type=room.type,
            standard_occupancy=room.standard_occupancy,
            display_order=room.display_order,
            available=reservation is None,
            reservation=(
                ReservationRead.model_validate(reservation)
                if reservation is not None
                else None
            ),
        )
        for room, reservation in db.execute(stmt).all()
    ]


@router.get("/grid", response_model=AvailabilityGrid)
def availability_grid(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    db: Session = Depends(get_db),
):
    _require_range(from_, to)

    # Same underlying query, different shape: every reservation overlapping the
    # window, joined to its room. A room with none appears once with NULL.
    rows = db.execute(
        select(Room, Reservation)
        .outerjoin(
            Reservation,
            and_(
                Reservation.room_id == Room.id,
                Reservation.check_in < to,
                from_ < Reservation.check_out,
            ),
        )
        .order_by(Room.display_order, Reservation.check_in)
    ).all()

    rooms: dict[str, tuple[Room, list[Reservation]]] = {}
    for room, reservation in rows:
        entry = rooms.setdefault(room.id, (room, []))
        if reservation is not None:
            entry[1].append(reservation)

    days: list[date] = []
    day = from_
    while day < to:  # each day is a night; the window is half-open [from, to)
        days.append(day)
        day += timedelta(days=1)

    grid_rooms = []
    for room, reservations in rooms.values():
        cells = []
        for night in days:
            covering = next(
                (r for r in reservations if r.check_in <= night < r.check_out),
                None,
            )
            cells.append(
                GridCell(
                    date=night,
                    available=covering is None,
                    reservation_id=covering.id if covering is not None else None,
                )
            )
        grid_rooms.append(
            GridRoom(
                room_id=room.id,
                type=room.type,
                standard_occupancy=room.standard_occupancy,
                display_order=room.display_order,
                days=cells,
            )
        )

    return AvailabilityGrid(days=days, rooms=grid_rooms)
