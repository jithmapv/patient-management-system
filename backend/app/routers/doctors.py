from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_doctor
from ..models import (
    Appointment,
    Doctor,
    DoctorAvailability,
)
from ..schemas import (
    AppointmentResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    DoctorResponse,
)


router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)


# ============================================================
# GET ALL DOCTORS / SEARCH BY SPECIALTY
# ============================================================

@router.get(
    "",
    response_model=list[DoctorResponse],
)
def get_doctors(
    specialty: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Doctor)

    if specialty:
        query = query.filter(
            Doctor.specialty.ilike(
                f"%{specialty.strip()}%"
            )
        )

    return (
        query
        .order_by(Doctor.full_name.asc())
        .all()
    )


# ============================================================
# DOCTOR CREATES AVAILABILITY
# ============================================================

@router.post(
    "/me/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_availability(
    payload: AvailabilityCreate,
    current_doctor: Doctor = Depends(
        get_current_doctor
    ),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Validate future availability
    # --------------------------------------------------------

    if payload.start_time <= now:
        raise HTTPException(
            status_code=422,
            detail="Availability must start in the future",
        )

    # schemas.py already validates this,
    # but keeping business validation here is also safe.
    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=422,
            detail="End time must be after start time",
        )

    # --------------------------------------------------------
    # Prevent overlapping availability
    #
    # Example:
    #
    # existing: 09:00 - 10:00
    # new:      09:30 - 10:30
    #
    # -> reject
    #
    # Existing 09:00-10:00
    # New      10:00-11:00
    #
    # -> allowed
    # --------------------------------------------------------

    overlapping_slot = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id
            == current_doctor.id,

            DoctorAvailability.start_time
            < payload.end_time,

            DoctorAvailability.end_time
            > payload.start_time,
        )
        .first()
    )

    if overlapping_slot:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Availability overlaps with "
                "an existing slot"
            ),
        )

    # --------------------------------------------------------
    # Create availability
    # --------------------------------------------------------

    slot = DoctorAvailability(
        doctor_id=current_doctor.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )

    db.add(slot)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Availability slot conflicts "
                "with an existing slot"
            ),
        )

    db.refresh(slot)

    return slot


# ============================================================
# DOCTOR VIEWS OWN SCHEDULE
# ============================================================

@router.get(
    "/me/schedule",
    response_model=list[AppointmentResponse],
)
def doctor_schedule(
    view: Literal["day", "week"] = Query(
        default="day"
    ),
    target_date: date | None = Query(
        default=None,
        alias="date",
    ),
    current_doctor: Doctor = Depends(
        get_current_doctor
    ),
    db: Session = Depends(get_db),
):
    selected_date = (
        target_date
        or datetime.now(timezone.utc).date()
    )

    # --------------------------------------------------------
    # Daily schedule
    # --------------------------------------------------------

    if view == "day":
        start = datetime.combine(
            selected_date,
            time.min,
            tzinfo=timezone.utc,
        )

        end = start + timedelta(days=1)

    # --------------------------------------------------------
    # Weekly schedule
    # Monday -> Sunday
    # --------------------------------------------------------

    else:
        monday = (
            selected_date
            - timedelta(
                days=selected_date.weekday()
            )
        )

        start = datetime.combine(
            monday,
            time.min,
            tzinfo=timezone.utc,
        )

        end = start + timedelta(days=7)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id
            == current_doctor.id,

            Appointment.scheduled_at >= start,
            Appointment.scheduled_at < end,

            # Cancelled appointments should
            # not appear in active schedule.
            Appointment.status == "booked",
        )
        .order_by(
            Appointment.scheduled_at.asc()
        )
        .all()
    )

    return appointments


# ============================================================
# GET DOCTOR AVAILABLE SLOTS
# ============================================================

@router.get(
    "/{doctor_id}/slots",
    response_model=list[AvailabilityResponse],
)
def get_available_slots(
    doctor_id: int,
    slot_date: date | None = Query(
        default=None,
        alias="date",
    ),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Check doctor exists
    # --------------------------------------------------------

    doctor = db.get(
        Doctor,
        doctor_id,
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Only future slots
    # --------------------------------------------------------

    query = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id
            == doctor_id,

            DoctorAvailability.start_time
            > now,
        )
    )

    # --------------------------------------------------------
    # Optional date filter
    #
    # /doctors/1/slots?date=2026-08-20
    # --------------------------------------------------------

    if slot_date:
        start_of_day = datetime.combine(
            slot_date,
            time.min,
            tzinfo=timezone.utc,
        )

        end_of_day = (
            start_of_day
            + timedelta(days=1)
        )

        query = query.filter(
            DoctorAvailability.start_time
            >= start_of_day,

            DoctorAvailability.start_time
            < end_of_day,
        )

    # --------------------------------------------------------
    # Get IDs of actively booked slots
    #
    # Using select() avoids SQLAlchemy warning:
    # "Coercing Subquery object into select()"
    # --------------------------------------------------------

    booked_slot_ids = (
        select(Appointment.slot_id)
        .where(
            Appointment.status == "booked"
        )
    )

    # --------------------------------------------------------
    # Remove booked slots
    # --------------------------------------------------------

    query = query.filter(
        ~DoctorAvailability.id.in_(
            booked_slot_ids
        )
    )

    return (
        query
        .order_by(
            DoctorAvailability.start_time.asc()
        )
        .all()
    )