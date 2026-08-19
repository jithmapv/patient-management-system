from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..auth import create_access_token, hash_password, verify_password
from ..database import get_db
from ..models import Doctor, Patient
from ..schemas import (
    DoctorRegister,
    DoctorResponse,
    LoginRequest,
    PatientRegister,
    PatientResponse,
    TokenResponse,
)

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


def email_exists(db: Session, email: str) -> bool:
    patient = (
        db.query(Patient)
        .filter(Patient.email == email.lower())
        .first()
    )

    doctor = (
        db.query(Doctor)
        .filter(Doctor.email == email.lower())
        .first()
    )

    return patient is not None or doctor is not None


@router.post(
    "/patients/register",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED
)
def register_patient(
    payload: PatientRegister,
    db: Session = Depends(get_db)
):
    if email_exists(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    patient = Patient(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password)
    )

    db.add(patient)
    db.commit()
    db.refresh(patient)

    return patient


@router.post(
    "/doctors/register",
    response_model=DoctorResponse,
    status_code=status.HTTP_201_CREATED
)
def register_doctor(
    payload: DoctorRegister,
    db: Session = Depends(get_db)
):
    if email_exists(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered"
        )

    doctor = Doctor(
        full_name=payload.full_name.strip(),
        email=payload.email.lower(),
        specialty=payload.specialty.strip(),
        password_hash=hash_password(payload.password)
    )

    db.add(doctor)
    db.commit()
    db.refresh(doctor)

    return doctor


@router.post(
    "/patients/login",
    response_model=TokenResponse
)
def login_patient(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    patient = (
        db.query(Patient)
        .filter(Patient.email == payload.email.lower())
        .first()
    )

    if not patient or not verify_password(
        payload.password,
        patient.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(
        patient.id,
        "patient"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "patient"
    }


@router.post(
    "/doctors/login",
    response_model=TokenResponse
)
def login_doctor(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    doctor = (
        db.query(Doctor)
        .filter(Doctor.email == payload.email.lower())
        .first()
    )

    if not doctor or not verify_password(
        payload.password,
        doctor.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    token = create_access_token(
        doctor.id,
        "doctor"
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "doctor"
    }