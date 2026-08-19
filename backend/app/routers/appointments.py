from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_patient
from ..models import (
    Appointment,
    Doctor,
    DoctorAvailability,
    Patient
)
from ..schemas import (
    AppointmentCreate,
    AppointmentResponse
)

router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"]
)


# =========================================================
# Book Appointment
# =========================================================

@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED
)
def book_appointment(
    payload: AppointmentCreate,

    current_patient: Patient = Depends(
        get_current_patient
    ),

    db: Session = Depends(get_db)
):
    # Check doctor
    doctor = db.get(
        Doctor,
        payload.doctor_id
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found"
        )

    # Check availability slot
    slot = db.get(
        DoctorAvailability,
        payload.slot_id
    )

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found"
        )

    # Slot must belong to doctor
    if slot.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slot does not belong to this doctor"
        )

    # Prevent booking past appointment
    if slot.start_time <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot book a past slot"
        )

    # Application-level double booking check
    existing_booking = (
        db.query(Appointment)
        .filter(
            Appointment.slot_id == slot.id,
            Appointment.status == "booked"
        )
        .first()
    )

    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is already booked"
        )

    appointment = Appointment(
        patient_id=current_patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        scheduled_at=slot.start_time,
        status="booked"
    )

    db.add(appointment)

    try:
        db.commit()

    except IntegrityError:
        # Handles two patients booking simultaneously
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot was booked by another patient"
        )

    db.refresh(appointment)

    return appointment


# =========================================================
# Patient Views Own Appointments
# =========================================================

@router.get(
    "/me",
    response_model=list[AppointmentResponse]
)
def get_my_appointments(
    current_patient: Patient = Depends(
        get_current_patient
    ),
    db: Session = Depends(get_db)
):
    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id
            == current_patient.id
        )
        .order_by(
            Appointment.scheduled_at.asc()
        )
        .all()
    )

    return appointments


# =========================================================
# Cancel Appointment
# =========================================================

@router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse
)
def cancel_appointment(
    appointment_id: int,

    current_patient: Patient = Depends(
        get_current_patient
    ),

    db: Session = Depends(get_db)
):
    appointment = db.get(
        Appointment,
        appointment_id
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )

    # Prevent cancelling someone else's appointment
    if appointment.patient_id != current_patient.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You cannot cancel another "
                "patient's appointment"
            )
        )

    # Already cancelled/completed
    if appointment.status != "booked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Appointment is already "
                f"{appointment.status}"
            )
        )

    # Prevent cancelling past appointment
    if (
        appointment.scheduled_at
        <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Past appointments cannot be cancelled"
        )

    appointment.status = "cancelled"

    db.commit()
    db.refresh(appointment)

    return appointment