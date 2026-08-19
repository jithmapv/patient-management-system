from datetime import date, datetime, time, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_doctor
from ..models import (
    Appointment,
    Doctor,
    DoctorAvailability
)
from ..schemas import (
    AppointmentResponse,
    AvailabilityCreate,
    AvailabilityResponse,
    DoctorResponse
)

router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"]
)


# =========================================================
# Search / List Doctors
# =========================================================

@router.get(
    "",
    response_model=list[DoctorResponse]
)
def get_doctors(
    specialty: str | None = Query(default=None),
    db: Session = Depends(get_db)
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


# =========================================================
# Get Available Slots
# =========================================================

@router.get(
    "/{doctor_id}/slots",
    response_model=list[AvailabilityResponse]
)
def get_available_slots(
    doctor_id: int,
    slot_date: date | None = Query(
        default=None,
        alias="date"
    ),
    db: Session = Depends(get_db)
):
    doctor = db.get(
        Doctor,
        doctor_id
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    now = datetime.now(timezone.utc)

    query = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id == doctor_id,
            DoctorAvailability.start_time > now
        )
    )

    # Optional filtering by date
    if slot_date:
        start_of_day = datetime.combine(
            slot_date,
            time.min,
            tzinfo=timezone.utc
        )

        end_of_day = (
            start_of_day
            + timedelta(days=1)
        )

        query = query.filter(
            DoctorAvailability.start_time >= start_of_day,
            DoctorAvailability.start_time < end_of_day
        )

    # Get currently booked slot IDs
    booked_slot_ids = (
        db.query(Appointment.slot_id)
        .filter(
            Appointment.status == "booked"
        )
        .subquery()
    )

    # Exclude booked slots
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


# =========================================================
# Doctor Creates Availability
# =========================================================

@router.post(
    "/me/availability",
    response_model=AvailabilityResponse,
    status_code=status.HTTP_201_CREATED
)
def create_availability(
    payload: AvailabilityCreate,
    current_doctor: Doctor = Depends(
        get_current_doctor
    ),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)

    if payload.start_time <= now:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Availability must start in the future"
        )

    if payload.end_time <= payload.start_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="End time must be after start time"
        )

    existing_slot = (
        db.query(DoctorAvailability)
        .filter(
            DoctorAvailability.doctor_id
            == current_doctor.id,

            DoctorAvailability.start_time
            == payload.start_time
        )
        .first()
    )

    if existing_slot:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Availability slot already exists"
        )

    slot = DoctorAvailability(
        doctor_id=current_doctor.id,
        start_time=payload.start_time,
        end_time=payload.end_time
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    return slot


# =========================================================
# Doctor Views Own Schedule
# =========================================================

@router.get(
    "/me/schedule",
    response_model=list[AppointmentResponse]
)
def doctor_schedule(
    view: Literal["day", "week"] = Query(
        default="day"
    ),

    target_date: date | None = Query(
        default=None,
        alias="date"
    ),

    current_doctor: Doctor = Depends(
        get_current_doctor
    ),

    db: Session = Depends(get_db)
):
    selected_date = (
        target_date
        or datetime.now(timezone.utc).date()
    )

    if view == "day":

        start = datetime.combine(
            selected_date,
            time.min,
            tzinfo=timezone.utc
        )

        end = start + timedelta(days=1)

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
            tzinfo=timezone.utc
        )

        end = start + timedelta(days=7)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id
            == current_doctor.id,

            Appointment.scheduled_at >= start,
            Appointment.scheduled_at < end,

            Appointment.status == "booked"
        )
        .order_by(
            Appointment.scheduled_at.asc()
        )
        .all()
    )

    return appointments