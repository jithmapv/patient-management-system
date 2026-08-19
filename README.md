# Patient Management System

A full-stack clinic appointment management system built using FastAPI, React, PostgreSQL, and Docker.

The application allows patients to find doctors, view available time slots, book appointments, view upcoming appointments, and cancel their own bookings.

Doctors have a separate login and can manage availability and view their daily or weekly appointment schedule.

## Technology Stack

### Backend Technologies

* Python
* FastAPI
* SQLAlchemy
* PostgreSQL
* Alembic
* JWT Authentication
* Pydantic
* Pytest

### Frontend Technologies

* React
* React Hooks
* Vite
* React Router
* Fetch API

### Deployment Technologies

* Docker
* Docker Compose
* Nginx
* PostgreSQL

## Features

### Patient Features

* Register
* Login
* Search doctors by specialty
* View doctor availability
* Book appointments
* View upcoming appointments
* Cancel own appointments

### Doctor Features

* Separate doctor login
* Add availability
* Prevent overlapping availability
* View daily schedule
* View weekly schedule

### Validation and Business Rules

The application prevents:

* Double booking
* Booking past appointments
* Booking a slot belonging to another doctor
* Cancelling another patient's appointment
* Cancelling inactive appointments
* Overlapping doctor availability

## Authentication and Authorization

JWT authentication is used.

Patients and doctors have separate login endpoints:

```text
POST /auth/patients/login
POST /auth/doctors/login
```

The JWT contains the role of the authenticated user.

Backend dependencies enforce authorization so that patients and doctors can only access functionality allowed for their role.

Patients can only cancel their own appointments.

Doctors can only view their own schedules.

Frontend protected routes improve the user experience, but backend authorization remains the source of truth.

## Double Booking Protection

Double booking is prevented at two levels.

### Application Layer Protection

The backend checks whether a selected slot already has an active booking before creating an appointment.

### Database Layer Protection

PostgreSQL constraints prevent concurrent requests from creating two active bookings for the same slot.

The database constraint acts as the final protection against race conditions.

Cancelled appointments remain stored for history while making their availability slot bookable again.

## Database Migrations

Database schema changes are managed using Alembic.

The migration files are stored under:

```text
backend/alembic/versions/
```

Alembic uses the SQLAlchemy model metadata to generate versioned database schema changes.

### Generate a Migration

From the backend directory:

```powershell
cd backend
```

Activate the virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Set the local database connection:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/patient_management"
```

Generate a migration after changing SQLAlchemy models:

```powershell
python -m alembic revision --autogenerate -m "describe schema change"
```

### Apply Migrations

Run:

```powershell
python -m alembic upgrade head
```

### Check Current Migration

```powershell
python -m alembic current
```

### View Migration History

```powershell
python -m alembic history
```

Alembic migrations are used as the primary schema-management mechanism instead of relying only on SQLAlchemy `Base.metadata.create_all()`.

## Project Structure

```text
patient-management-system/
├── backend/
│   ├── alembic/
│   │   ├── versions/
│   │   │   └── *_initial_schema.py
│   │   ├── env.py
│   │   ├── README
│   │   └── script.py.mako
│   ├── alembic.ini
│   ├── app/
│   │   ├── routers/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── dependencies.py
│   │   └── test.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── nginx.conf
│   └── package.json
│
├── scripts/
│   └── deploy.ps1
│
├── docker-compose.yml
├── .env
├── .gitignore
└── README.md
```

## Run With Docker

### Docker Prerequisite

Install and start Docker Desktop.

From the project root:

```powershell
.\scripts\deploy.ps1
```

Alternatively:

```powershell
docker compose up --build -d
```

The backend container applies the latest Alembic migrations before starting the FastAPI server.

Open:

```text
Frontend: http://localhost:5173
Backend:  http://localhost:8000
Swagger:  http://localhost:8000/docs
Health:   http://localhost:8000/health
```

### View Docker Containers

```powershell
docker compose ps
```

### View Docker Logs

```powershell
docker compose logs -f
```

### Stop Docker Application

```powershell
docker compose down
```

### Remove Containers and Database Data

```powershell
docker compose down -v
```

## Local Development

### Local Backend Setup

Navigate to the backend:

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure environment variables:

```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/patient_management
SECRET_KEY=YOUR_SECRET_KEY
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Apply database migrations:

```powershell
python -m alembic upgrade head
```

Run the backend:

```powershell
python -m uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Local Frontend Setup

Open another terminal:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Run the frontend:

```powershell
npm run dev
```

Frontend:

```text
http://localhost:5173
```

Frontend environment:

```env
VITE_API_URL=http://127.0.0.1:8000
```

## Running Tests

A separate PostgreSQL test database should be used so tests do not affect development data.

Create the test database:

```sql
CREATE DATABASE patient_management_test;
```

Set the environment variable in PowerShell:

```powershell
$env:TEST_DATABASE_URL="postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/patient_management_test"
```

Run the tests:

```powershell
cd backend
python -m pytest -v
```

The test suite covers:

* Patient registration
* Doctor registration
* Login
* JWT authentication
* Authorization
* Doctor search
* Availability creation
* Availability overlap prevention
* Available slot listing
* Appointment booking
* Past appointment validation
* Double-booking prevention
* Database constraints
* Appointment ownership
* Appointment cancellation
* Rebooking cancelled slots
* Doctor daily schedule
* Doctor weekly schedule
* Error handling

## API Overview

### Authentication Endpoints

```text
POST /auth/patients/register
POST /auth/patients/login
POST /auth/doctors/register
POST /auth/doctors/login
```

### Doctor Endpoints

```text
GET  /doctors
GET  /doctors/{doctor_id}/slots
POST /doctors/me/availability
GET  /doctors/me/schedule
```

### Appointment Endpoints

```text
POST  /appointments
GET   /appointments/me
PATCH /appointments/{appointment_id}/cancel
```

## Architecture Decisions

### FastAPI Decision

FastAPI provides concise REST API development, request validation, dependency-based authorization, and automatic Swagger/OpenAPI documentation.

### PostgreSQL Decision

PostgreSQL was selected because appointment booking requires reliable database constraints and concurrency protection.

### SQLAlchemy Decision

SQLAlchemy provides the persistence layer and keeps database operations separated from application schemas.

### Alembic Decision

Alembic is used for version-controlled database migrations.

Schema changes can be generated from SQLAlchemy models and applied consistently across local development and Docker environments.

This provides a reproducible database schema and avoids depending only on automatic table creation at application startup.

### JWT Authentication Decision

JWT provides a simple stateless authentication mechanism suitable for this time-boxed application.

### React Decision

React with hooks was used to keep the frontend simple while supporting authentication state, doctor searches, booking, cancellation, and doctor schedule views.

### Availability Model Decision

Doctor availability is stored separately from appointments.

Patients select an existing availability slot instead of submitting an arbitrary appointment time.

This ensures patients can only book times that doctors have made available.

## Assumptions and Trade-offs

This project was completed as a time-boxed technical exercise.

Doctor registration is available through the backend API for demonstration convenience.

In a production system, doctor creation would normally be managed through an administrator or controlled onboarding process.

The frontend stores the JWT in `localStorage` for simplicity.

A production system should evaluate HTTP-only secure cookies, refresh token rotation, expiration handling, and token revocation.

Database schema changes are managed through Alembic migrations.

For this technical exercise, migrations are intentionally kept simple and focused on the current application schema.

## What I Would Do With More Time

With more time I would add:

* Administrator functionality
* Secure HTTP-only cookie authentication
* Refresh tokens
* Password reset
* Appointment rescheduling
* Recurring doctor availability
* Email and SMS reminders
* Patient profiles
* Doctor profiles
* Appointment completion workflow
* Improved frontend validation
* Frontend automated tests
* CI/CD pipeline
* Rate limiting
* Structured application logging
* Monitoring
* Production secret management
* Cloud deployment
* More advanced migration rollback and deployment validation

## Security

Passwords are hashed and never stored as plain text.

Protected APIs require valid JWT authentication.

Role authorization is enforced on the backend.

Patients cannot cancel another patient's appointment.

Doctors cannot view another doctor's schedule.

Database constraints provide final protection against concurrent double-booking.

Environment files containing credentials and secrets are excluded from Git.
