from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .auth import decode_access_token
from .database import get_db
from .models import Doctor, Patient


# Reads:
# Authorization: Bearer <token>
bearer_scheme = HTTPBearer()


def get_current_identity(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
):
    """
    Decode JWT token and return:
    {
        "id": user_id,
        "role": "patient" or "doctor"
    }
    """

    try:
        payload = decode_access_token(credentials.credentials)

        user_id = int(payload["sub"])
        role = payload["role"]

    except (ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
        )

    if role not in {"patient", "doctor"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication role",
        )

    return {
        "id": user_id,
        "role": role,
    }


def get_current_patient(
    identity=Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """
    Allow only logged-in patients.
    """

    if identity["role"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient access required",
        )

    patient = db.get(
        Patient,
        identity["id"],
    )

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Patient account not found",
        )

    return patient


def get_current_doctor(
    identity=Depends(get_current_identity),
    db: Session = Depends(get_db),
):
    """
    Allow only logged-in doctors.
    """

    if identity["role"] != "doctor":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor access required",
        )

    doctor = db.get(
        Doctor,
        identity["id"],
    )

    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Doctor account not found",
        )

    return doctor