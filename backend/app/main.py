from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, doctors, appointments


# Create database tables automatically.
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="Patient Management System API",
    description="Clinic appointment booking backend using FastAPI and PostgreSQL",
    version="1.0.0",
)


# Allow React frontend running with Vite
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register routers
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(appointments.router)


@app.get("/")
def root():
    return {
        "message": "Patient Management System API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy"
    }