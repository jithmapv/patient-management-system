import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import JWTError, jwt
from passlib.context import CryptContext


load_dotenv()


SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-this-secret-key"
)

ALGORITHM = os.getenv(
    "ALGORITHM",
    "HS256"
)

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "60"
    )
)


# Password hashing configuration
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


# =========================================================
# Password Functions
# =========================================================

def hash_password(password: str) -> str:
    """
    Convert plain password into a secure bcrypt hash.
    """

    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """
    Compare plain password with stored password hash.
    """

    return pwd_context.verify(
        plain_password,
        hashed_password
    )


# =========================================================
# JWT Token Functions
# =========================================================

def create_access_token(
    user_id: int,
    role: str
) -> str:
    """
    Create JWT access token.

    role:
        patient
        doctor
    """

    expire = (
        datetime.now(timezone.utc)
        + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )

    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }

    token = jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return token


def decode_access_token(
    token: str
) -> dict:
    """
    Decode and validate JWT token.
    """

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        return payload

    except JWTError as exc:
        raise ValueError(
            "Invalid or expired token"
        ) from exc