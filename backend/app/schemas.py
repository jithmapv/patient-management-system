from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
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
        min_length=8,
        max_length=128,
    )

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str):
        value = value.strip()

        if not value:
            raise ValueError(
                "Full name cannot be empty"
            )

        return value


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
        min_length=8,
        max_length=128,
    )

    specialty: str = Field(
        min_length=2,
        max_length=120,
    )

    @field_validator(
        "full_name",
        "specialty"
    )
    @classmethod
    def validate_text_fields(
        cls,
        value: str
    ):
        value = value.strip()

        if not value:
            raise ValueError(
                "Value cannot be empty"
            )

        return value


class DoctorResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    specialty: str

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# Authentication Schemas
# =========================================================

class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )


class TokenResponse(BaseModel):
    access_token: str

    token_type: str = "bearer"

    role: Literal[
        "patient",
        "doctor",
    ]


# =========================================================
# Doctor Availability Schemas
# =========================================================

class AvailabilityCreate(BaseModel):
    start_time: datetime
    end_time: datetime

    @model_validator(mode="after")
    def validate_availability(self):

        # Require timezone-aware datetime
        if self.start_time.tzinfo is None:
            raise ValueError(
                "start_time must include timezone information"
            )

        if self.end_time.tzinfo is None:
            raise ValueError(
                "end_time must include timezone information"
            )

        # End must be later than start
        if self.end_time <= self.start_time:
            raise ValueError(
                "end_time must be after start_time"
            )

        return self


class AvailabilityResponse(BaseModel):
    id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


# =========================================================
# Appointment Schemas
# =========================================================

class AppointmentCreate(BaseModel):
    doctor_id: int = Field(
        gt=0
    )

    slot_id: int = Field(
        gt=0
    )


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