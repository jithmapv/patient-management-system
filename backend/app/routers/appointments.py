from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_patient
from ..models import (
    Appointment,
    Doctor,
    DoctorAvailability,
    Patient,
)
from ..schemas import (
    AppointmentCreate,
    AppointmentResponse,
)


router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
)


# ============================================================
# BOOK APPOINTMENT
# ============================================================

@router.post(
    "",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def book_appointment(
    payload: AppointmentCreate,
    current_patient: Patient = Depends(
        get_current_patient
    ),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Check doctor exists
    # --------------------------------------------------------

    doctor = db.get(
        Doctor,
        payload.doctor_id,
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    # --------------------------------------------------------
    # Check availability slot exists
    # --------------------------------------------------------

    slot = db.get(
        DoctorAvailability,
        payload.slot_id,
    )

    if not slot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Availability slot not found",
        )

    # --------------------------------------------------------
    # Slot must belong to selected doctor
    # --------------------------------------------------------

    if slot.doctor_id != doctor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Slot does not belong "
                "to this doctor"
            ),
        )

    # --------------------------------------------------------
    # Prevent booking past slot
    # --------------------------------------------------------

    if (
        slot.start_time
        <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=422,
            detail="Cannot book a past slot",
        )

    # --------------------------------------------------------
    # Application-level double booking check
    # --------------------------------------------------------

    existing_booking = (
        db.query(Appointment)
        .filter(
            Appointment.slot_id == slot.id,
            Appointment.status == "booked",
        )
        .first()
    )

    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This slot is already booked",
        )

    # --------------------------------------------------------
    # Create appointment
    # --------------------------------------------------------

    appointment = Appointment(
        patient_id=current_patient.id,
        doctor_id=doctor.id,
        slot_id=slot.id,
        scheduled_at=slot.start_time,
        status="booked",
    )

    db.add(appointment)

    try:
        db.commit()

    except IntegrityError:
        # ----------------------------------------------------
        # Important:
        #
        # Two patients could attempt booking at
        # exactly the same time.
        #
        # PostgreSQL unique constraint becomes
        # the final protection.
        # ----------------------------------------------------

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This slot was booked "
                "by another patient"
            ),
        )

    db.refresh(appointment)

    return appointment


# ============================================================
# PATIENT VIEWS OWN UPCOMING APPOINTMENTS
# ============================================================

@router.get(
    "/me",
    response_model=list[AppointmentResponse],
)
def get_my_appointments(
    current_patient: Patient = Depends(
        get_current_patient
    ),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)

    # --------------------------------------------------------
    # Requirement:
    #
    # Patient should see UPCOMING appointments.
    #
    # Therefore:
    #
    # - only their appointments
    # - only future appointments
    # - only status=booked
    #
    # Cancelled and completed appointments are excluded.
    # --------------------------------------------------------

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.patient_id
            == current_patient.id,

            Appointment.scheduled_at > now,

            Appointment.status == "booked",
        )
        .order_by(
            Appointment.scheduled_at.asc()
        )
        .all()
    )

    return appointments


# ============================================================
# CANCEL APPOINTMENT
# ============================================================

@router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentResponse,
)
def cancel_appointment(
    appointment_id: int,
    current_patient: Patient = Depends(
        get_current_patient
    ),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Find appointment
    # --------------------------------------------------------

    appointment = db.get(
        Appointment,
        appointment_id,
    )

    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found",
        )

    # --------------------------------------------------------
    # Prevent patient cancelling another patient's appointment
    # --------------------------------------------------------

    if (
        appointment.patient_id
        != current_patient.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You cannot cancel another "
                "patient's appointment"
            ),
        )

    # --------------------------------------------------------
    # Prevent cancelling cancelled/completed appointment
    # --------------------------------------------------------

    if appointment.status != "booked":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Appointment is already "
                f"{appointment.status}"
            ),
        )

    # --------------------------------------------------------
    # Prevent cancellation after appointment time
    # --------------------------------------------------------

    if (
        appointment.scheduled_at
        <= datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "Past appointments cannot "
                "be cancelled"
            ),
        )

    # --------------------------------------------------------
    # Cancel
    #
    # We do NOT delete the appointment.
    # Keeping it gives us appointment history.
    # --------------------------------------------------------

    appointment.status = "cancelled"

    try:
        db.commit()

    except Exception:
        db.rollback()
        raise

    db.refresh(appointment)

    return appointment