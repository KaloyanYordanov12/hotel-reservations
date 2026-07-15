# SQLAlchemy models for rooms and reservations.
#
# There is no total_price column and there never will be. deposit_paid is
# Numeric(10, 2) and must arrive in Python as Decimal. standard_occupancy is a
# display value only; it is deliberately NOT named capacity and is never used in
# any rejection path. See CLAUDE.md and the Phase 1 brief.
import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    TIMESTAMP,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class RoomType(str, enum.Enum):
    double = "double"
    triple = "triple"
    apartment = "apartment"
    studio = "studio"


class Room(Base):
    __tablename__ = "rooms"

    # Natural key: "3.3", "A11". Not a surrogate integer.
    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[RoomType] = mapped_column(
        Enum(RoomType, name="room_type"), nullable=False
    )
    standard_occupancy: Mapped[int] = mapped_column(Integer, nullable=False)
    # Display only, like standard_occupancy. It sorts the rooms into a sensible
    # order for the screen (string order puts A11 before A3). It appears in no
    # rejection path.
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)


class Reservation(Base):
    __tablename__ = "reservations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    room_id: Mapped[str] = mapped_column(
        String, ForeignKey("rooms.id"), nullable=False, index=True
    )
    guest_name: Mapped[str] = mapped_column(String, nullable=False)
    guest_phone: Mapped[str] = mapped_column(String, nullable=False)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    num_guests: Mapped[int] = mapped_column(Integer, nullable=False)
    parking: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    deposit_paid: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0"), server_default=text("0")
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
