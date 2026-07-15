"""Reservations CRUD.

The no-double-booking rule and the date-order rule live in the database as the
constraints no_double_booking and valid_dates. This layer does not re-implement
them; it catches the IntegrityError they raise and translates it into a response
my mother can read on her phone: 409 for a clash, 422 for backwards dates.
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Reservation, Room
from app.schemas import ReservationCreate, ReservationRead, ReservationUpdate

router = APIRouter(prefix="/api/reservations", tags=["reservations"])


def _require_room(db: Session, room_id: str) -> None:
    """404 if the room does not exist. A missing room is a typo, not a booking."""
    if db.get(Room, room_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Room {room_id} does not exist",
        )


def _find_clash(db, room_id, check_in, check_out, exclude_id=None):
    """The reservation that blocks [check_in, check_out) for this room, if any.

    Uses the same half-open overlap logic as the exclusion constraint
    (existing.check_in < new.check_out AND new.check_in < existing.check_out) so
    the message can never disagree with what the database enforced.
    """
    stmt = select(Reservation).where(
        Reservation.room_id == room_id,
        Reservation.check_in < check_out,
        check_in < Reservation.check_out,
    )
    if exclude_id is not None:
        stmt = stmt.where(Reservation.id != exclude_id)
    return db.scalars(stmt).first()


def _translate_integrity_error(db, error, room_id, check_in, check_out, exclude_id=None):
    """Turn a constraint violation into a 409 or 422. Never let a raw 500 escape."""
    db.rollback()
    constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)

    if constraint == "no_double_booking":
        clash = _find_clash(db, room_id, check_in, check_out, exclude_id)
        detail = {
            "error": "double_booking",
            "room_id": room_id,
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
        }
        if clash is not None:
            detail["message"] = (
                f"Room {room_id} is already booked from "
                f"{clash.check_in.isoformat()} to {clash.check_out.isoformat()} "
                f"by {clash.guest_name}."
            )
            detail["conflict"] = {
                "id": str(clash.id),
                "guest_name": clash.guest_name,
                "check_in": clash.check_in.isoformat(),
                "check_out": clash.check_out.isoformat(),
            }
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    if constraint == "valid_dates":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="check_out must be after check_in",
        )

    raise error


@router.post("", response_model=ReservationRead, status_code=status.HTTP_201_CREATED)
def create_reservation(payload: ReservationCreate, db: Session = Depends(get_db)):
    _require_room(db, payload.room_id)
    reservation = Reservation(**payload.model_dump())
    db.add(reservation)
    try:
        db.commit()
    except IntegrityError as error:
        _translate_integrity_error(
            db, error, payload.room_id, payload.check_in, payload.check_out
        )
    db.refresh(reservation)
    return reservation


@router.get("", response_model=list[ReservationRead])
def list_reservations(
    db: Session = Depends(get_db),
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None, alias="to"),
    deposit_paid: bool | None = Query(None),
):
    stmt = select(Reservation)
    # from/to bound a half-open window [from, to) and return reservations that
    # overlap it, matching the convention used everywhere else in the system.
    if from_ is not None:
        stmt = stmt.where(Reservation.check_out > from_)
    if to is not None:
        stmt = stmt.where(Reservation.check_in < to)
    # deposit_paid is a boolean filter, not the stored amount: false means "still
    # owes a deposit" (amount is 0), true means "has paid something".
    if deposit_paid is False:
        stmt = stmt.where(Reservation.deposit_paid == 0)
    elif deposit_paid is True:
        stmt = stmt.where(Reservation.deposit_paid > 0)
    stmt = stmt.order_by(Reservation.check_in)
    return db.scalars(stmt).all()


@router.get("/{reservation_id}", response_model=ReservationRead)
def get_reservation(reservation_id: UUID, db: Session = Depends(get_db)):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    return reservation


@router.patch("/{reservation_id}", response_model=ReservationRead)
def update_reservation(
    reservation_id: UUID, payload: ReservationUpdate, db: Session = Depends(get_db)
):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )

    updates = payload.model_dump(exclude_unset=True)
    if "room_id" in updates:
        _require_room(db, updates["room_id"])
    for field, value in updates.items():
        setattr(reservation, field, value)

    # Capture the effective values before the commit so the conflict message
    # survives the rollback that a violation triggers.
    room_id = reservation.room_id
    check_in = reservation.check_in
    check_out = reservation.check_out
    try:
        db.commit()
    except IntegrityError as error:
        _translate_integrity_error(
            db, error, room_id, check_in, check_out, exclude_id=reservation_id
        )
    db.refresh(reservation)
    return reservation


@router.delete("/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reservation(reservation_id: UUID, db: Session = Depends(get_db)):
    reservation = db.get(Reservation, reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found"
        )
    db.delete(reservation)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
