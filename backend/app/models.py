from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.orm import relationship

from .database import Base


# =========================================================
# Patient
# =========================================================
class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(
        String(120),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    # One patient can have many appointments
    appointments = relationship(
        "Appointment",
        back_populates="patient",
        cascade="all, delete-orphan",
    )


# =========================================================
# Doctor
# =========================================================
class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)

    full_name = Column(
        String(120),
        nullable=False,
    )

    email = Column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash = Column(
        String(255),
        nullable=False,
    )

    specialty = Column(
        String(120),
        nullable=False,
        index=True,
    )

    # Doctor availability slots
    availability_slots = relationship(
        "DoctorAvailability",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    # Doctor appointments
    appointments = relationship(
        "Appointment",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )


# =========================================================
# Doctor Availability
# =========================================================
class DoctorAvailability(Base):
    __tablename__ = "doctor_availability"

    id = Column(Integer, primary_key=True, index=True)

    doctor_id = Column(
        Integer,
        ForeignKey(
            "doctors.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    start_time = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    end_time = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    doctor = relationship(
        "Doctor",
        back_populates="availability_slots",
    )

    __table_args__ = (
        # A doctor cannot have two availability slots
        # starting at exactly the same time
        UniqueConstraint(
            "doctor_id",
            "start_time",
            name="uq_doctor_availability_start",
        ),

        # end_time must always be after start_time
        CheckConstraint(
            "end_time > start_time",
            name="ck_availability_end_after_start",
        ),
    )


# =========================================================
# Appointment
# =========================================================
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(
        Integer,
        ForeignKey(
            "patients.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    doctor_id = Column(
        Integer,
        ForeignKey(
            "doctors.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    slot_id = Column(
        Integer,
        ForeignKey(
            "doctor_availability.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    scheduled_at = Column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    status = Column(
        String(20),
        nullable=False,
        default="booked",
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    # Relationships
    patient = relationship(
        "Patient",
        back_populates="appointments",
    )

    doctor = relationship(
        "Doctor",
        back_populates="appointments",
    )

    slot = relationship(
        "DoctorAvailability",
    )

    __table_args__ = (

        # Only allow valid appointment statuses
        CheckConstraint(
            "status IN ('booked', 'cancelled', 'completed')",
            name="ck_appointment_status",
        ),

        # -------------------------------------------------
        # Prevent double booking
        # -------------------------------------------------
        # A doctor can only have ONE active appointment
        # at a particular date/time.
        #
        # Cancelled appointments do not block the slot.
        Index(
            "uq_active_doctor_slot",
            "doctor_id",
            "scheduled_at",
            unique=True,
            postgresql_where=text(
                "status = 'booked'"
            ),
        ),

        # A particular availability slot can only have
        # ONE active appointment.
        Index(
            "uq_active_availability_slot",
            "slot_id",
            unique=True,
            postgresql_where=text(
                "status = 'booked'"
            ),
        ),
    )