from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


# =========================================================
# Patient Schemas
# =========================================================

class PatientRegister(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=120,
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=128,
    )


class PatientResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# Doctor Schemas
# =========================================================

class DoctorRegister(BaseModel):
    full_name: str = Field(
        min_length=2,
        max_length=120,
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=128,
    )

    specialty: str = Field(
        min_length=2,
        max_length=120,
    )


class DoctorResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    specialty: str

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# Login / Authentication
# =========================================================

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

    role: Literal[
        "patient",
        "doctor",
    ]


# =========================================================
# Doctor Availability
# =========================================================

class AvailabilityCreate(BaseModel):
    start_time: datetime
    end_time: datetime


class AvailabilityResponse(BaseModel):
    id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# Appointment
# =========================================================

class AppointmentCreate(BaseModel):
    doctor_id: int
    slot_id: int


class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    slot_id: int

    scheduled_at: datetime

    status: Literal[
        "booked",
        "cancelled",
        "completed",
    ]

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )