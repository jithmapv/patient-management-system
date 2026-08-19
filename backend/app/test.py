import os
from datetime import datetime, timedelta, timezone

import pytest


# ============================================================
# TEST DATABASE CONFIGURATION
# ============================================================

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

if not TEST_DATABASE_URL:
    pytest.fail(
        "\nTEST_DATABASE_URL is not configured.\n\n"
        "Create a PostgreSQL test database first:\n"
        "CREATE DATABASE patient_management_test;\n\n"
        "Then in PowerShell:\n"
        '$env:TEST_DATABASE_URL='
        '"postgresql+psycopg2://postgres:root'
        '@localhost:5432/patient_management_test"\n'
    )


# Must be set BEFORE importing app.database / app.main
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session as SQLAlchemySession

from app.database import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Appointment,
    DoctorAvailability,
)


# raise_server_exceptions=False allows us to test HTTP 500 handling
client = TestClient(
    app,
    raise_server_exceptions=False,
)


# ============================================================
# DATABASE RESET
# ============================================================

@pytest.fixture(autouse=True)
def reset_database():
    """
    Every test runs against a clean PostgreSQL database.
    """

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def auth_header(token: str):
    return {
        "Authorization": f"Bearer {token}"
    }


def assert_error(
    response,
    expected_status: int,
    message_contains: str | None = None,
):
    """
    Supports both:
    FastAPI default:
        {"detail": "..."}

    and custom error response:
        {
            "error": {
                "code": "...",
                "message": "..."
            }
        }
    """

    assert response.status_code == expected_status

    if message_contains is None:
        return

    try:
        body = response.json()
    except Exception:
        assert message_contains.lower() in response.text.lower()
        return

    if "error" in body:
        message = str(body["error"])
    else:
        message = str(body.get("detail", body))

    assert message_contains.lower() in message.lower()


def register_patient(
    email="patient@example.com",
    password="Password123",
    full_name="Test Patient",
):
    return client.post(
        "/auth/patients/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
        },
    )


def login_patient(
    email="patient@example.com",
    password="Password123",
):
    response = client.post(
        "/auth/patients/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def register_doctor(
    email="doctor@example.com",
    password="Password123",
    full_name="Dr. Test",
    specialty="Cardiology",
):
    return client.post(
        "/auth/doctors/register",
        json={
            "full_name": full_name,
            "email": email,
            "password": password,
            "specialty": specialty,
        },
    )


def login_doctor(
    email="doctor@example.com",
    password="Password123",
):
    response = client.post(
        "/auth/doctors/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    return response.json()["access_token"]


def create_doctor_with_slot(
    email="doctor@example.com",
    specialty="Cardiology",
    days_from_now=1,
):
    doctor_response = register_doctor(
        email=email,
        specialty=specialty,
    )

    assert doctor_response.status_code == 201

    doctor_id = doctor_response.json()["id"]

    doctor_token = login_doctor(
        email=email
    )

    start_time = (
        datetime.now(timezone.utc)
        + timedelta(days=days_from_now)
    ).replace(
        minute=0,
        second=0,
        microsecond=0,
    )

    end_time = (
        start_time
        + timedelta(minutes=30)
    )

    slot_response = client.post(
        "/doctors/me/availability",
        headers=auth_header(doctor_token),
        json={
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        },
    )

    assert slot_response.status_code == 201

    return {
        "doctor_id": doctor_id,
        "doctor_token": doctor_token,
        "slot_id": slot_response.json()["id"],
        "start_time": start_time,
        "end_time": end_time,
    }


def create_patient_and_book(
    doctor_data,
    email="patient@example.com",
):
    response = register_patient(email=email)
    assert response.status_code == 201

    token = login_patient(email=email)

    booking = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": doctor_data["doctor_id"],
            "slot_id": doctor_data["slot_id"],
        },
    )

    assert booking.status_code == 201

    return token, booking.json()


# ============================================================
# 1. BASIC APPLICATION TESTS
# ============================================================

def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


# ============================================================
# 2. PATIENT REGISTRATION
# ============================================================

def test_patient_registration():
    response = register_patient()

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "Test Patient"
    assert data["email"] == "patient@example.com"

    # Passwords must NEVER be returned
    assert "password" not in data
    assert "password_hash" not in data


def test_invalid_patient_email_rejected():
    response = register_patient(
        email="not-an-email"
    )

    assert response.status_code == 422


def test_short_patient_password_rejected():
    response = register_patient(
        password="1234567"
    )

    assert response.status_code == 422


def test_blank_patient_name_rejected():
    response = register_patient(
        full_name="   "
    )

    assert response.status_code == 422


def test_missing_patient_email_rejected():
    response = client.post(
        "/auth/patients/register",
        json={
            "full_name": "Test Patient",
            "password": "Password123",
        },
    )

    assert response.status_code == 422


def test_duplicate_patient_email_rejected():
    first = register_patient()

    assert first.status_code == 201

    second = register_patient()

    assert_error(
        second,
        409,
        "already registered",
    )


# ============================================================
# 3. DOCTOR REGISTRATION
# ============================================================

def test_doctor_registration():
    response = register_doctor()

    assert response.status_code == 201

    data = response.json()

    assert data["full_name"] == "Dr. Test"
    assert data["specialty"] == "Cardiology"

    assert "password" not in data
    assert "password_hash" not in data


def test_invalid_doctor_email_rejected():
    response = register_doctor(
        email="invalid-email"
    )

    assert response.status_code == 422


def test_short_doctor_password_rejected():
    response = register_doctor(
        password="123"
    )

    assert response.status_code == 422


def test_blank_doctor_name_rejected():
    response = register_doctor(
        full_name="   "
    )

    assert response.status_code == 422


def test_blank_specialty_rejected():
    response = register_doctor(
        specialty="   "
    )

    assert response.status_code == 422


def test_duplicate_email_between_patient_and_doctor():
    patient = register_patient(
        email="same@example.com"
    )

    assert patient.status_code == 201

    doctor = register_doctor(
        email="same@example.com"
    )

    assert_error(
        doctor,
        409,
        "already registered",
    )


# ============================================================
# 4. LOGIN VALIDATION
# ============================================================

def test_patient_login():
    register_patient()

    response = client.post(
        "/auth/patients/login",
        json={
            "email": "patient@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["role"] == "patient"
    assert data["token_type"] == "bearer"
    assert "access_token" in data


def test_patient_wrong_password():
    register_patient()

    response = client.post(
        "/auth/patients/login",
        json={
            "email": "patient@example.com",
            "password": "WrongPassword",
        },
    )

    assert_error(
        response,
        401,
        "invalid email or password",
    )


def test_patient_nonexistent_email():
    response = client.post(
        "/auth/patients/login",
        json={
            "email": "missing@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == 401


def test_blank_login_password_validation():
    response = client.post(
        "/auth/patients/login",
        json={
            "email": "patient@example.com",
            "password": "",
        },
    )

    assert response.status_code == 422


def test_doctor_login():
    register_doctor()

    response = client.post(
        "/auth/doctors/login",
        json={
            "email": "doctor@example.com",
            "password": "Password123",
        },
    )

    assert response.status_code == 200

    assert response.json()["role"] == "doctor"


def test_doctor_wrong_password():
    register_doctor()

    response = client.post(
        "/auth/doctors/login",
        json={
            "email": "doctor@example.com",
            "password": "WrongPassword",
        },
    )

    assert response.status_code == 401


# ============================================================
# 5. AUTHENTICATION / AUTHORIZATION
# ============================================================

def test_invalid_token_rejected():
    response = client.get(
        "/appointments/me",
        headers={
            "Authorization": "Bearer invalid-token"
        },
    )

    assert response.status_code == 401


def test_missing_authentication_rejected():
    response = client.get(
        "/appointments/me"
    )

    # Recommended REST authentication behaviour.
    assert response.status_code == 401


def test_patient_cannot_access_doctor_endpoint():
    register_patient()

    token = login_patient()

    future = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": future.isoformat(),
            "end_time": (
                future + timedelta(minutes=30)
            ).isoformat(),
        },
    )

    assert response.status_code == 403


# ============================================================
# 6. DOCTOR SEARCH
# ============================================================

def test_get_all_doctors():
    register_doctor(
        email="cardio@example.com",
        specialty="Cardiology",
    )

    register_doctor(
        email="neuro@example.com",
        specialty="Neurology",
    )

    response = client.get("/doctors")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_search_doctors_by_specialty():
    register_doctor(
        email="cardio@example.com",
        specialty="Cardiology",
    )

    register_doctor(
        email="neuro@example.com",
        specialty="Neurology",
    )

    response = client.get(
        "/doctors",
        params={
            "specialty": "Cardiology"
        },
    )

    assert response.status_code == 200

    doctors = response.json()

    assert len(doctors) == 1
    assert doctors[0]["specialty"] == "Cardiology"


def test_specialty_search_case_insensitive():
    register_doctor(
        specialty="Cardiology"
    )

    response = client.get(
        "/doctors",
        params={
            "specialty": "cardio"
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


# ============================================================
# 7. DOCTOR AVAILABILITY VALIDATION
# ============================================================

def test_doctor_can_create_future_availability():
    register_doctor()

    token = login_doctor()

    start = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": start.isoformat(),
            "end_time": (
                start + timedelta(minutes=30)
            ).isoformat(),
        },
    )

    assert response.status_code == 201


def test_past_availability_rejected():
    register_doctor()

    token = login_doctor()

    start = (
        datetime.now(timezone.utc)
        - timedelta(hours=2)
    )

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": start.isoformat(),
            "end_time": (
                start + timedelta(minutes=30)
            ).isoformat(),
        },
    )

    assert response.status_code == 422


def test_end_before_start_rejected():
    register_doctor()

    token = login_doctor()

    start = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": start.isoformat(),
            "end_time": (
                start - timedelta(minutes=30)
            ).isoformat(),
        },
    )

    assert response.status_code == 422


def test_equal_start_end_rejected():
    register_doctor()

    token = login_doctor()

    start = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": start.isoformat(),
            "end_time": start.isoformat(),
        },
    )

    assert response.status_code == 422


def test_timezone_required_for_start_time():
    register_doctor()

    token = login_doctor()

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": "2026-09-01T09:00:00",
            "end_time": "2026-09-01T09:30:00+00:00",
        },
    )

    assert response.status_code == 422


def test_timezone_required_for_end_time():
    register_doctor()

    token = login_doctor()

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": "2026-09-01T09:00:00+00:00",
            "end_time": "2026-09-01T09:30:00",
        },
    )

    assert response.status_code == 422


def test_duplicate_availability_rejected():
    data = create_doctor_with_slot()

    response = client.post(
        "/doctors/me/availability",
        headers=auth_header(
            data["doctor_token"]
        ),
        json={
            "start_time": data["start_time"].isoformat(),
            "end_time": data["end_time"].isoformat(),
        },
    )

    assert response.status_code == 409


def test_overlapping_availability_rejected():
    register_doctor()

    token = login_doctor()

    start = (
        datetime.now(timezone.utc)
        + timedelta(days=2)
    ).replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0,
    )

    first = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": start.isoformat(),
            "end_time": (
                start + timedelta(hours=1)
            ).isoformat(),
        },
    )

    assert first.status_code == 201

    # 09:30 - 10:30 overlaps 09:00 - 10:00
    second = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": (
                start + timedelta(minutes=30)
            ).isoformat(),
            "end_time": (
                start
                + timedelta(
                    hours=1,
                    minutes=30,
                )
            ).isoformat(),
        },
    )

    assert response_status(second) == 409


def response_status(response):
    return response.status_code


def test_adjacent_availability_allowed():
    register_doctor()

    token = login_doctor()

    start = (
        datetime.now(timezone.utc)
        + timedelta(days=2)
    ).replace(
        hour=9,
        minute=0,
        second=0,
        microsecond=0,
    )

    first = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": start.isoformat(),
            "end_time": (
                start + timedelta(hours=1)
            ).isoformat(),
        },
    )

    assert first.status_code == 201

    # Starts exactly when previous slot ends.
    second = client.post(
        "/doctors/me/availability",
        headers=auth_header(token),
        json={
            "start_time": (
                start + timedelta(hours=1)
            ).isoformat(),
            "end_time": (
                start + timedelta(hours=2)
            ).isoformat(),
        },
    )

    assert second.status_code == 201


# ============================================================
# 8. VIEW AVAILABLE SLOTS
# ============================================================

def test_available_slots_returned():
    data = create_doctor_with_slot()

    response = client.get(
        f"/doctors/{data['doctor_id']}/slots"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_slots_for_unknown_doctor_return_404():
    response = client.get(
        "/doctors/99999/slots"
    )

    assert response.status_code == 404


# ============================================================
# 9. APPOINTMENT INPUT VALIDATION
# ============================================================

def test_negative_doctor_id_rejected():
    register_patient()

    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": -1,
            "slot_id": 1,
        },
    )

    assert response.status_code == 422


def test_zero_slot_id_rejected():
    register_patient()

    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": 1,
            "slot_id": 0,
        },
    )

    assert response.status_code == 422


def test_missing_slot_id_rejected():
    register_patient()

    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": 1
        },
    )

    assert response.status_code == 422


def test_invalid_json_rejected():
    register_patient()

    token = login_patient()

    response = client.post(
        "/appointments",
        headers={
            **auth_header(token),
            "Content-Type": "application/json",
        },
        content="{invalid-json",
    )

    assert response.status_code == 422


# ============================================================
# 10. BOOKING
# ============================================================

def test_patient_can_book_appointment():
    doctor_data = create_doctor_with_slot()

    token, booking = create_patient_and_book(
        doctor_data
    )

    assert booking["status"] == "booked"
    assert booking["doctor_id"] == doctor_data["doctor_id"]
    assert booking["slot_id"] == doctor_data["slot_id"]


def test_doctor_cannot_book_appointment():
    data = create_doctor_with_slot()

    response = client.post(
        "/appointments",
        headers=auth_header(
            data["doctor_token"]
        ),
        json={
            "doctor_id": data["doctor_id"],
            "slot_id": data["slot_id"],
        },
    )

    assert response.status_code == 403


def test_unknown_doctor_booking_returns_404():
    register_patient()

    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": 99999,
            "slot_id": 1,
        },
    )

    assert response.status_code == 404


def test_unknown_slot_returns_404():
    doctor = register_doctor()
    doctor_id = doctor.json()["id"]

    register_patient()
    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": doctor_id,
            "slot_id": 99999,
        },
    )

    assert response.status_code == 404


def test_slot_must_belong_to_selected_doctor():
    doctor1 = create_doctor_with_slot(
        email="doctor1@example.com"
    )

    doctor2 = register_doctor(
        email="doctor2@example.com"
    )

    doctor2_id = doctor2.json()["id"]

    register_patient()
    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": doctor2_id,
            "slot_id": doctor1["slot_id"],
        },
    )

    assert response.status_code == 400


# ============================================================
# 11. PAST BOOKING VALIDATION
# ============================================================

def test_past_slot_cannot_be_booked():
    doctor = register_doctor()

    doctor_id = doctor.json()["id"]

    # Direct DB insertion because the normal API
    # correctly prevents creating past availability.
    db = SessionLocal()

    past_start = (
        datetime.now(timezone.utc)
        - timedelta(hours=2)
    )

    slot = DoctorAvailability(
        doctor_id=doctor_id,
        start_time=past_start,
        end_time=(
            past_start + timedelta(minutes=30)
        ),
    )

    db.add(slot)
    db.commit()
    db.refresh(slot)

    slot_id = slot.id

    db.close()

    register_patient()

    token = login_patient()

    response = client.post(
        "/appointments",
        headers=auth_header(token),
        json={
            "doctor_id": doctor_id,
            "slot_id": slot_id,
        },
    )

    assert response.status_code == 422


# ============================================================
# 12. DOUBLE BOOKING
# ============================================================

def test_double_booking_prevented_by_api():
    data = create_doctor_with_slot()

    register_patient(
        email="patient1@example.com"
    )

    token1 = login_patient(
        email="patient1@example.com"
    )

    first = client.post(
        "/appointments",
        headers=auth_header(token1),
        json={
            "doctor_id": data["doctor_id"],
            "slot_id": data["slot_id"],
        },
    )

    assert first.status_code == 201

    register_patient(
        email="patient2@example.com"
    )

    token2 = login_patient(
        email="patient2@example.com"
    )

    second = client.post(
        "/appointments",
        headers=auth_header(token2),
        json={
            "doctor_id": data["doctor_id"],
            "slot_id": data["slot_id"],
        },
    )

    assert second.status_code == 409


def test_database_constraint_prevents_double_booking():
    """
    Important test:
    verifies PostgreSQL itself prevents bad data,
    even if API-level checking were bypassed.
    """

    data = create_doctor_with_slot()

    patient1 = register_patient(
        email="patient1@example.com"
    )

    patient2 = register_patient(
        email="patient2@example.com"
    )

    patient1_id = patient1.json()["id"]
    patient2_id = patient2.json()["id"]

    db = SessionLocal()

    first = Appointment(
        patient_id=patient1_id,
        doctor_id=data["doctor_id"],
        slot_id=data["slot_id"],
        scheduled_at=data["start_time"],
        status="booked",
    )

    db.add(first)
    db.commit()

    second = Appointment(
        patient_id=patient2_id,
        doctor_id=data["doctor_id"],
        slot_id=data["slot_id"],
        scheduled_at=data["start_time"],
        status="booked",
    )

    db.add(second)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
    db.close()


def test_booked_slot_disappears_from_available_slots():
    data = create_doctor_with_slot()

    create_patient_and_book(data)

    response = client.get(
        f"/doctors/{data['doctor_id']}/slots"
    )

    assert response.status_code == 200
    assert response.json() == []


# ============================================================
# 13. APPOINTMENT OWNERSHIP
# ============================================================

def test_patient_can_view_own_upcoming_appointments():
    data = create_doctor_with_slot()

    token, _ = create_patient_and_book(data)

    response = client.get(
        "/appointments/me",
        headers=auth_header(token),
    )

    assert response.status_code == 200

    appointments = response.json()

    assert len(appointments) == 1
    assert appointments[0]["status"] == "booked"


def test_patient_does_not_see_other_patient_appointments():
    data = create_doctor_with_slot()

    create_patient_and_book(
        data,
        email="owner@example.com",
    )

    register_patient(
        email="other@example.com"
    )

    other_token = login_patient(
        email="other@example.com"
    )

    response = client.get(
        "/appointments/me",
        headers=auth_header(other_token),
    )

    assert response.status_code == 200
    assert response.json() == []


def test_doctor_cannot_access_patient_appointments():
    data = create_doctor_with_slot()

    response = client.get(
        "/appointments/me",
        headers=auth_header(
            data["doctor_token"]
        ),
    )

    assert response.status_code == 403


# ============================================================
# 14. CANCELLATION
# ============================================================

def test_patient_can_cancel_own_appointment():
    data = create_doctor_with_slot()

    token, booking = create_patient_and_book(data)

    response = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_patient_cannot_cancel_someone_elses_appointment():
    data = create_doctor_with_slot()

    owner_token, booking = create_patient_and_book(
        data,
        email="owner@example.com",
    )

    register_patient(
        email="attacker@example.com"
    )

    attacker_token = login_patient(
        email="attacker@example.com"
    )

    response = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(attacker_token),
    )

    assert response.status_code == 403


def test_nonexistent_appointment_cancel_returns_404():
    register_patient()

    token = login_patient()

    response = client.patch(
        "/appointments/99999/cancel",
        headers=auth_header(token),
    )

    assert response.status_code == 404


def test_cancelled_appointment_cannot_be_cancelled_twice():
    data = create_doctor_with_slot()

    token, booking = create_patient_and_book(data)

    first = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(token),
    )

    assert first.status_code == 200

    second = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(token),
    )

    assert second.status_code == 409


def test_cancelled_slot_becomes_available_again():
    data = create_doctor_with_slot()

    token, booking = create_patient_and_book(
        data,
        email="patient1@example.com",
    )

    cancel = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(token),
    )

    assert cancel.status_code == 200

    response = client.get(
        f"/doctors/{data['doctor_id']}/slots"
    )

    assert response.status_code == 200

    slot_ids = [
        slot["id"]
        for slot in response.json()
    ]

    assert data["slot_id"] in slot_ids


def test_cancelled_slot_can_be_booked_by_another_patient():
    data = create_doctor_with_slot()

    token1, booking = create_patient_and_book(
        data,
        email="patient1@example.com",
    )

    cancel = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(token1),
    )

    assert cancel.status_code == 200

    register_patient(
        email="patient2@example.com"
    )

    token2 = login_patient(
        email="patient2@example.com"
    )

    response = client.post(
        "/appointments",
        headers=auth_header(token2),
        json={
            "doctor_id": data["doctor_id"],
            "slot_id": data["slot_id"],
        },
    )

    assert response.status_code == 201


def test_cancelled_appointment_not_in_upcoming_list():
    """
    Requirement:
    /appointments/me should represent UPCOMING
    active appointments.
    """

    data = create_doctor_with_slot()

    token, booking = create_patient_and_book(data)

    cancel = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(token),
    )

    assert cancel.status_code == 200

    response = client.get(
        "/appointments/me",
        headers=auth_header(token),
    )

    assert response.status_code == 200
    assert response.json() == []


# ============================================================
# 15. DOCTOR DAILY/WEEKLY SCHEDULE
# ============================================================

def test_doctor_can_view_daily_schedule():
    data = create_doctor_with_slot()

    create_patient_and_book(data)

    target_date = (
        data["start_time"]
        .date()
        .isoformat()
    )

    response = client.get(
        "/doctors/me/schedule",
        headers=auth_header(
            data["doctor_token"]
        ),
        params={
            "view": "day",
            "date": target_date,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_doctor_can_view_weekly_schedule():
    data = create_doctor_with_slot()

    create_patient_and_book(data)

    target_date = (
        data["start_time"]
        .date()
        .isoformat()
    )

    response = client.get(
        "/doctors/me/schedule",
        headers=auth_header(
            data["doctor_token"]
        ),
        params={
            "view": "week",
            "date": target_date,
        },
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_patient_cannot_view_doctor_schedule():
    register_patient()

    token = login_patient()

    response = client.get(
        "/doctors/me/schedule",
        headers=auth_header(token),
    )

    assert response.status_code == 403


def test_doctor_cannot_view_other_doctors_schedule():
    doctor1 = create_doctor_with_slot(
        email="doctor1@example.com"
    )

    create_patient_and_book(
        doctor1
    )

    register_doctor(
        email="doctor2@example.com"
    )

    doctor2_token = login_doctor(
        email="doctor2@example.com"
    )

    target_date = (
        doctor1["start_time"]
        .date()
        .isoformat()
    )

    response = client.get(
        "/doctors/me/schedule",
        headers=auth_header(
            doctor2_token
        ),
        params={
            "view": "day",
            "date": target_date,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


def test_invalid_schedule_view_rejected():
    register_doctor()

    token = login_doctor()

    response = client.get(
        "/doctors/me/schedule",
        headers=auth_header(token),
        params={
            "view": "month"
        },
    )

    assert response.status_code == 422


def test_cancelled_appointment_not_in_doctor_schedule():
    data = create_doctor_with_slot()

    patient_token, booking = create_patient_and_book(
        data
    )

    cancel = client.patch(
        f"/appointments/{booking['id']}/cancel",
        headers=auth_header(patient_token),
    )

    assert cancel.status_code == 200

    target_date = (
        data["start_time"]
        .date()
        .isoformat()
    )

    response = client.get(
        "/doctors/me/schedule",
        headers=auth_header(
            data["doctor_token"]
        ),
        params={
            "view": "day",
            "date": target_date,
        },
    )

    assert response.status_code == 200
    assert response.json() == []


# ============================================================
# 16. DATABASE CONSTRAINT TESTS
# ============================================================

def test_database_rejects_invalid_appointment_status():
    doctor_data = create_doctor_with_slot()

    patient = register_patient()

    patient_id = patient.json()["id"]

    db = SessionLocal()

    invalid_appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_data["doctor_id"],
        slot_id=doctor_data["slot_id"],
        scheduled_at=doctor_data["start_time"],
        status="invalid-status",
    )

    db.add(invalid_appointment)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
    db.close()


def test_database_rejects_end_before_start():
    doctor = register_doctor()

    doctor_id = doctor.json()["id"]

    start = (
        datetime.now(timezone.utc)
        + timedelta(days=1)
    )

    db = SessionLocal()

    invalid_slot = DoctorAvailability(
        doctor_id=doctor_id,
        start_time=start,
        end_time=(
            start - timedelta(minutes=30)
        ),
    )

    db.add(invalid_slot)

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()
    db.close()


# ============================================================
# 17. EXCEPTION HANDLING
# ============================================================

def test_validation_error_does_not_return_500():
    response = client.post(
        "/auth/patients/register",
        json={
            "full_name": "",
            "email": "bad-email",
            "password": "1",
        },
    )

    assert response.status_code == 422
    assert response.status_code != 500


def test_duplicate_email_does_not_return_500():
    register_patient()

    response = register_patient()

    assert response.status_code == 409
    assert response.status_code != 500


def test_double_booking_does_not_return_500():
    data = create_doctor_with_slot()

    create_patient_and_book(
        data,
        email="patient1@example.com",
    )

    register_patient(
        email="patient2@example.com"
    )

    token2 = login_patient(
        email="patient2@example.com"
    )

    response = client.post(
        "/appointments",
        headers=auth_header(token2),
        json={
            "doctor_id": data["doctor_id"],
            "slot_id": data["slot_id"],
        },
    )

    assert response.status_code == 409
    assert response.status_code != 500


def test_unexpected_database_error_returns_500_without_leaking_details(
    monkeypatch,
):
    """
    Simulates an unexpected SQLAlchemy failure.

    This verifies the backend returns an HTTP 500 rather
    than exposing Python/database internals to the client.
    """

    def broken_commit(self):
        raise SQLAlchemyError(
            "SECRET DATABASE INTERNAL ERROR"
        )

    # Scope patch to only this request.
    with monkeypatch.context() as patch:
        patch.setattr(
            SQLAlchemySession,
            "commit",
            broken_commit,
        )

        response = register_patient(
            email="database-error@example.com"
        )

    assert response.status_code == 500

    # Do not expose internal exception details
    assert (
        "SECRET DATABASE INTERNAL ERROR"
        not in response.text
    )

    assert TEST_DATABASE_URL not in response.text