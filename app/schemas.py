# Pydantic schemas for reservations.
#
# Validation here rejects only the physically impossible or the unambiguous
# typo, never a judgement call. num_guests is NOT checked against a room's
# standard_occupancy; note is free text and is never validated; there is no
# total_price. See CLAUDE.md and the Step 5 validation philosophy.
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import RoomType


class ReservationCreate(BaseModel):
    room_id: str
    guest_name: str
    guest_phone: str
    check_in: date
    check_out: date
    num_guests: int = Field(ge=1)  # zero people is a slip of the thumb
    parking: bool = False
    deposit_paid: Decimal = Field(default=Decimal("0"), ge=0)  # negative money was not paid
    note: str | None = None

    @model_validator(mode="after")
    def _check_out_after_check_in(self):
        # Time does not run backwards. The valid_dates constraint enforces this
        # in the database too; rejecting here gives an immediate, clear message.
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be after check_in")
        return self


class ReservationUpdate(BaseModel):
    room_id: str | None = None
    guest_name: str | None = None
    guest_phone: str | None = None
    check_in: date | None = None
    check_out: date | None = None
    num_guests: int | None = Field(default=None, ge=1)
    parking: bool | None = None
    deposit_paid: Decimal | None = Field(default=None, ge=0)
    note: str | None = None

    @model_validator(mode="after")
    def _check_out_after_check_in(self):
        # Only checkable when both dates are supplied. A partial update that
        # touches one date is left to the database valid_dates constraint, which
        # sees the stored value.
        if (
            self.check_in is not None
            and self.check_out is not None
            and self.check_out <= self.check_in
        ):
            raise ValueError("check_out must be after check_in")
        return self


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    room_id: str
    guest_name: str
    guest_phone: str
    check_in: date
    check_out: date
    num_guests: int
    parking: bool
    deposit_paid: Decimal
    note: str | None
    created_at: datetime
    updated_at: datetime


# --- availability -----------------------------------------------------------


class RoomAvailability(BaseModel):
    """One room's status for a requested stay. type and standard_occupancy are
    included for display; standard_occupancy is never a limit."""

    room_id: str
    type: RoomType
    standard_occupancy: int
    available: bool
    reservation: ReservationRead | None  # the booking that blocks it, if any


class GridCell(BaseModel):
    date: date
    available: bool
    reservation_id: UUID | None


class GridRoom(BaseModel):
    room_id: str
    type: RoomType
    standard_occupancy: int
    days: list[GridCell]


class AvailabilityGrid(BaseModel):
    days: list[date]
    rooms: list[GridRoom]
