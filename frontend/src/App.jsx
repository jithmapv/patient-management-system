import { useEffect, useState } from "react";

import {
  Link,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router-dom";


const API_URL =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";


/* =========================================================
   API HELPER
========================================================= */

async function apiRequest(
  endpoint,
  method = "GET",
  body = null,
  token = null
) {
  const headers = {
    Accept: "application/json",
  };

  if (body !== null) {
    headers["Content-Type"] =
      "application/json";
  }

  if (token) {
    headers.Authorization =
      `Bearer ${token}`;
  }

  const response = await fetch(
    `${API_URL}${endpoint}`,
    {
      method,
      headers,
      body:
        body !== null
          ? JSON.stringify(body)
          : undefined,
    }
  );

  let data;

  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    let message = "Something went wrong";

    if (typeof data?.detail === "string") {
      message = data.detail;
    }

    if (Array.isArray(data?.detail)) {
      message = data.detail
        .map(
          (item) =>
            item.msg ||
            "Validation error"
        )
        .join(", ");
    }

    if (data?.error?.message) {
      message = data.error.message;
    }

    throw new Error(message);
  }

  return data;
}


/* =========================================================
   NAVBAR
========================================================= */

function Navbar({
  token,
  role,
  logout,
}) {
  return (
    <nav className="navbar">

      <Link
        to="/"
        className="brand"
      >
        ClinicCare
      </Link>

      <div className="nav-links">

        {role === "patient" && (
          <>
            <Link to="/doctors">
              Doctors
            </Link>

            <Link to="/appointments">
              My Appointments
            </Link>
          </>
        )}

        {role === "doctor" && (
          <>
            <Link to="/availability">
              Availability
            </Link>

            <Link to="/schedule">
              Schedule
            </Link>
          </>
        )}

        {!token && (
          <>
            <Link to="/register">
              Patient Register
            </Link>

            <Link to="/patient-login">
              Patient Login
            </Link>

            <Link to="/doctor-login">
              Doctor Login
            </Link>
          </>
        )}

        {token && (
          <button
            className="logout-button"
            onClick={logout}
          >
            Logout
          </button>
        )}

      </div>

    </nav>
  );
}


/* =========================================================
   HOME
========================================================= */

function Home({ role }) {
  return (
    <div className="container">

      <div className="hero">

        <h1>
          Patient Management System
        </h1>

        <p>
          Book and manage clinic
          appointments with doctors.
        </p>

        {!role && (
          <div className="button-group">

            <Link
              className="button"
              to="/register"
            >
              Patient Register
            </Link>

            <Link
              className="button secondary"
              to="/patient-login"
            >
              Patient Login
            </Link>

            <Link
              className="button secondary"
              to="/doctor-login"
            >
              Doctor Login
            </Link>

          </div>
        )}

        {role === "patient" && (
          <div className="button-group">

            <Link
              className="button"
              to="/doctors"
            >
              Find Doctors
            </Link>

            <Link
              className="button secondary"
              to="/appointments"
            >
              My Appointments
            </Link>

          </div>
        )}

        {role === "doctor" && (
          <div className="button-group">

            <Link
              className="button"
              to="/availability"
            >
              Add Availability
            </Link>

            <Link
              className="button secondary"
              to="/schedule"
            >
              View Schedule
            </Link>

          </div>
        )}

      </div>

    </div>
  );
}


/* =========================================================
   PATIENT REGISTER
========================================================= */

function PatientRegister() {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
  });

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  function changeField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]:
        event.target.value,
    }));
  }


  async function submit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await apiRequest(
        "/auth/patients/register",
        "POST",
        form
      );

      window.alert(
        "Registration successful. Please login."
      );

      navigate("/patient-login");

    } catch (err) {
      setError(err.message);

    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="container small">

      <h2>
        Patient Registration
      </h2>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <form onSubmit={submit}>

        <label>
          Full Name
        </label>

        <input
          name="full_name"
          value={form.full_name}
          onChange={changeField}
          minLength="2"
          maxLength="120"
          required
        />

        <label>
          Email
        </label>

        <input
          type="email"
          name="email"
          value={form.email}
          onChange={changeField}
          required
        />

        <label>
          Password
        </label>

        <input
          type="password"
          name="password"
          value={form.password}
          onChange={changeField}
          minLength="8"
          maxLength="128"
          required
        />

        <button
          disabled={loading}
        >
          {loading
            ? "Registering..."
            : "Register"}
        </button>

      </form>

    </div>
  );
}


/* =========================================================
   PATIENT LOGIN
========================================================= */

function PatientLogin({ login }) {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  function changeField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]:
        event.target.value,
    }));
  }


  async function submit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const data = await apiRequest(
        "/auth/patients/login",
        "POST",
        form
      );

      login(
        data.access_token,
        data.role
      );

      navigate("/doctors");

    } catch (err) {
      setError(err.message);

    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="container small">

      <h2>
        Patient Login
      </h2>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <form onSubmit={submit}>

        <label>
          Email
        </label>

        <input
          type="email"
          name="email"
          value={form.email}
          onChange={changeField}
          required
        />

        <label>
          Password
        </label>

        <input
          type="password"
          name="password"
          value={form.password}
          onChange={changeField}
          required
        />

        <button
          disabled={loading}
        >
          {loading
            ? "Logging in..."
            : "Login"}
        </button>

      </form>

    </div>
  );
}


/* =========================================================
   DOCTOR LOGIN
========================================================= */

function DoctorLogin({ login }) {
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  function changeField(event) {
    setForm((current) => ({
      ...current,
      [event.target.name]:
        event.target.value,
    }));
  }


  async function submit(event) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      const data = await apiRequest(
        "/auth/doctors/login",
        "POST",
        form
      );

      login(
        data.access_token,
        data.role
      );

      navigate("/schedule");

    } catch (err) {
      setError(err.message);

    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="container small">

      <h2>
        Doctor Login
      </h2>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <form onSubmit={submit}>

        <label>
          Email
        </label>

        <input
          type="email"
          name="email"
          value={form.email}
          onChange={changeField}
          required
        />

        <label>
          Password
        </label>

        <input
          type="password"
          name="password"
          value={form.password}
          onChange={changeField}
          required
        />

        <button
          disabled={loading}
        >
          {loading
            ? "Logging in..."
            : "Login"}
        </button>

      </form>

      <p className="note">
        Doctor accounts can be created
        through FastAPI Swagger for this demo.
      </p>

    </div>
  );
}


/* =========================================================
   DOCTOR SEARCH
========================================================= */

function Doctors() {
  const [doctors, setDoctors] =
    useState([]);

  const [specialty, setSpecialty] =
    useState("");

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(true);


  async function searchDoctors(
    specialtyValue
  ) {
    setLoading(true);
    setError("");

    try {
      let endpoint = "/doctors";

      if (specialtyValue.trim()) {
        endpoint +=
          `?specialty=${encodeURIComponent(
            specialtyValue.trim()
          )}`;
      }

      const data =
        await apiRequest(endpoint);

      setDoctors(data);

    } catch (err) {
      setError(err.message);

    } finally {
      setLoading(false);
    }
  }


  useEffect(() => {
    let cancelled = false;

    async function fetchInitialDoctors() {
      try {
        const data =
          await apiRequest(
            "/doctors"
          );

        if (!cancelled) {
          setDoctors(data);
        }

      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchInitialDoctors();

    return () => {
      cancelled = true;
    };

  }, []);


  function submitSearch(event) {
    event.preventDefault();

    searchDoctors(specialty);
  }


  function clearSearch() {
    setSpecialty("");

    searchDoctors("");
  }


  return (
    <div className="container">

      <h2>
        Find Doctors
      </h2>

      <p>
        Search doctors by specialty.
      </p>

      <form
        className="search-form"
        onSubmit={submitSearch}
      >

        <input
          placeholder="Specialty e.g. Cardiology"
          value={specialty}
          onChange={(event) =>
            setSpecialty(
              event.target.value
            )
          }
        />

        <button>
          Search
        </button>

        <button
          type="button"
          className="secondary-button"
          onClick={clearSearch}
        >
          Clear
        </button>

      </form>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {loading && (
        <p>
          Loading doctors...
        </p>
      )}

      {!loading &&
        doctors.map((doctor) => (

          <div
            className="card"
            key={doctor.id}
          >

            <h3>
              {doctor.full_name}
            </h3>

            <p>
              <strong>
                Specialty:
              </strong>{" "}
              {doctor.specialty}
            </p>

            <Link
              className="button"
              to={
                `/doctors/${doctor.id}/slots`
              }
            >
              View Available Slots
            </Link>

          </div>

        ))}

      {!loading &&
        doctors.length === 0 && (
          <p>
            No doctors found.
          </p>
        )}

    </div>
  );
}


/* =========================================================
   DOCTOR AVAILABLE SLOTS
========================================================= */

function DoctorSlots({ token }) {
  const { doctorId } =
    useParams();

  const [slots, setSlots] =
    useState([]);

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [bookingId, setBookingId] =
    useState(null);


  async function reloadSlots() {
    try {
      const data =
        await apiRequest(
          `/doctors/${doctorId}/slots`
        );

      setSlots(data);

    } catch (err) {
      setError(err.message);
    }
  }


  useEffect(() => {
    let cancelled = false;

    async function fetchInitialSlots() {
      try {
        const data =
          await apiRequest(
            `/doctors/${doctorId}/slots`
          );

        if (!cancelled) {
          setSlots(data);
        }

      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchInitialSlots();

    return () => {
      cancelled = true;
    };

  }, [doctorId]);


  async function book(slotId) {
    setError("");
    setSuccess("");
    setBookingId(slotId);

    try {
      await apiRequest(
        "/appointments",
        "POST",
        {
          doctor_id:
            Number(doctorId),

          slot_id:
            slotId,
        },
        token
      );

      setSuccess(
        "Appointment booked successfully."
      );

      await reloadSlots();

    } catch (err) {
      setError(err.message);

      /*
       * If another patient booked the
       * slot first, refresh available slots.
       */
      await reloadSlots();

    } finally {
      setBookingId(null);
    }
  }


  return (
    <div className="container">

      <h2>
        Available Slots
      </h2>

      <Link
        to="/doctors"
        className="back-link"
      >
        ← Back to Doctors
      </Link>

      {success && (
        <div className="success">
          {success}
        </div>
      )}

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {loading && (
        <p>
          Loading slots...
        </p>
      )}

      {!loading &&
        slots.map((slot) => (

          <div
            className="card"
            key={slot.id}
          >

            <p>
              <strong>
                Start:
              </strong>{" "}
              {new Date(
                slot.start_time
              ).toLocaleString()}
            </p>

            <p>
              <strong>
                End:
              </strong>{" "}
              {new Date(
                slot.end_time
              ).toLocaleString()}
            </p>

            <button
              disabled={
                bookingId === slot.id
              }
              onClick={() =>
                book(slot.id)
              }
            >
              {bookingId === slot.id
                ? "Booking..."
                : "Book Appointment"}
            </button>

          </div>

        ))}

      {!loading &&
        slots.length === 0 && (
          <p>
            No available slots.
          </p>
        )}

    </div>
  );
}


/* =========================================================
   PATIENT UPCOMING APPOINTMENTS
========================================================= */

function MyAppointments({ token }) {
  const [
    appointments,
    setAppointments,
  ] = useState([]);

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(true);

  const [
    cancellingId,
    setCancellingId,
  ] = useState(null);


  async function reloadAppointments() {
    try {
      const data =
        await apiRequest(
          "/appointments/me",
          "GET",
          null,
          token
        );

      setAppointments(data);

    } catch (err) {
      setError(err.message);
    }
  }


  useEffect(() => {
    let cancelled = false;

    async function fetchInitialAppointments() {
      try {
        const data =
          await apiRequest(
            "/appointments/me",
            "GET",
            null,
            token
          );

        if (!cancelled) {
          setAppointments(data);
        }

      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchInitialAppointments();

    return () => {
      cancelled = true;
    };

  }, [token]);


  async function cancelAppointment(id) {
    const confirmed =
      window.confirm(
        "Are you sure you want to cancel this appointment?"
      );

    if (!confirmed) {
      return;
    }

    setError("");
    setCancellingId(id);

    try {
      await apiRequest(
        `/appointments/${id}/cancel`,
        "PATCH",
        null,
        token
      );

      await reloadAppointments();

    } catch (err) {
      setError(err.message);

    } finally {
      setCancellingId(null);
    }
  }


  return (
    <div className="container">

      <h2>
        My Upcoming Appointments
      </h2>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {loading && (
        <p>
          Loading appointments...
        </p>
      )}

      {!loading &&
        appointments.map(
          (appointment) => (

            <div
              className="card"
              key={appointment.id}
            >

              <p>
                <strong>
                  Appointment ID:
                </strong>{" "}
                {appointment.id}
              </p>

              <p>
                <strong>
                  Doctor ID:
                </strong>{" "}
                {appointment.doctor_id}
              </p>

              <p>
                <strong>
                  Date:
                </strong>{" "}
                {new Date(
                  appointment.scheduled_at
                ).toLocaleString()}
              </p>

              <p>
                <strong>
                  Status:
                </strong>{" "}
                {appointment.status}
              </p>

              <button
                className="danger"
                disabled={
                  cancellingId ===
                  appointment.id
                }
                onClick={() =>
                  cancelAppointment(
                    appointment.id
                  )
                }
              >
                {cancellingId ===
                appointment.id
                  ? "Cancelling..."
                  : "Cancel Appointment"}
              </button>

            </div>

          )
        )}

      {!loading &&
        appointments.length === 0 && (
          <p>
            No upcoming appointments.
          </p>
        )}

    </div>
  );
}


/* =========================================================
   DOCTOR AVAILABILITY
========================================================= */

function DoctorAvailability({
  token,
}) {
  const [startTime, setStartTime] =
    useState("");

  const [endTime, setEndTime] =
    useState("");

  const [error, setError] =
    useState("");

  const [success, setSuccess] =
    useState("");

  const [loading, setLoading] =
    useState(false);


  async function submit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (
      new Date(endTime) <=
      new Date(startTime)
    ) {
      setError(
        "End time must be after start time."
      );

      return;
    }

    setLoading(true);

    try {
      await apiRequest(
        "/doctors/me/availability",
        "POST",
        {
          start_time:
            new Date(
              startTime
            ).toISOString(),

          end_time:
            new Date(
              endTime
            ).toISOString(),
        },
        token
      );

      setSuccess(
        "Availability created successfully."
      );

      setStartTime("");
      setEndTime("");

    } catch (err) {
      setError(err.message);

    } finally {
      setLoading(false);
    }
  }


  return (
    <div className="container small">

      <h2>
        Add Availability
      </h2>

      <p>
        Add a future time slot for
        patients to book.
      </p>

      {success && (
        <div className="success">
          {success}
        </div>
      )}

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      <form onSubmit={submit}>

        <label>
          Start Time
        </label>

        <input
          type="datetime-local"
          value={startTime}
          onChange={(event) =>
            setStartTime(
              event.target.value
            )
          }
          required
        />

        <label>
          End Time
        </label>

        <input
          type="datetime-local"
          value={endTime}
          onChange={(event) =>
            setEndTime(
              event.target.value
            )
          }
          required
        />

        <button
          disabled={loading}
        >
          {loading
            ? "Saving..."
            : "Add Availability"}
        </button>

      </form>

    </div>
  );
}


/* =========================================================
   DOCTOR SCHEDULE
========================================================= */

function DoctorSchedule({ token }) {
  const [view, setView] =
    useState("day");

  const [date, setDate] =
    useState(
      new Date()
        .toISOString()
        .split("T")[0]
    );

  const [
    appointments,
    setAppointments,
  ] = useState([]);

  const [error, setError] =
    useState("");

  const [loading, setLoading] =
    useState(true);


  useEffect(() => {
    let cancelled = false;

    async function fetchSchedule() {
      try {
        const data =
          await apiRequest(
            `/doctors/me/schedule?view=${view}&date=${date}`,
            "GET",
            null,
            token
          );

        if (!cancelled) {
          setAppointments(data);
        }

      } catch (err) {
        if (!cancelled) {
          setError(err.message);
        }

      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    fetchSchedule();

    return () => {
      cancelled = true;
    };

  }, [
    view,
    date,
    token,
  ]);


  function changeView(event) {
    setLoading(true);
    setError("");

    setView(
      event.target.value
    );
  }


  function changeDate(event) {
    setLoading(true);
    setError("");

    setDate(
      event.target.value
    );
  }


  return (
    <div className="container">

      <h2>
        Doctor Schedule
      </h2>

      <div className="filters">

        <div>

          <label>
            View
          </label>

          <select
            value={view}
            onChange={changeView}
          >

            <option value="day">
              Day
            </option>

            <option value="week">
              Week
            </option>

          </select>

        </div>

        <div>

          <label>
            Date
          </label>

          <input
            type="date"
            value={date}
            onChange={changeDate}
          />

        </div>

      </div>

      {error && (
        <div className="error">
          {error}
        </div>
      )}

      {loading && (
        <p>
          Loading schedule...
        </p>
      )}

      {!loading &&
        appointments.map(
          (appointment) => (

            <div
              className="card"
              key={appointment.id}
            >

              <p>
                <strong>
                  Appointment ID:
                </strong>{" "}
                {appointment.id}
              </p>

              <p>
                <strong>
                  Patient ID:
                </strong>{" "}
                {appointment.patient_id}
              </p>

              <p>
                <strong>
                  Date:
                </strong>{" "}
                {new Date(
                  appointment.scheduled_at
                ).toLocaleString()}
              </p>

              <p>
                <strong>
                  Status:
                </strong>{" "}
                {appointment.status}
              </p>

            </div>

          )
        )}

      {!loading &&
        appointments.length === 0 && (
          <p>
            No appointments found.
          </p>
        )}

    </div>
  );
}


/* =========================================================
   PROTECTED ROUTE
========================================================= */

function ProtectedRoute({
  token,
  role,
  requiredRole,
  children,
}) {
  if (!token) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  if (
    requiredRole &&
    role !== requiredRole
  ) {
    return (
      <Navigate
        to="/"
        replace
      />
    );
  }

  return children;
}


/* =========================================================
   APP
========================================================= */

export default function App() {
  const [token, setToken] =
    useState(
      localStorage.getItem(
        "token"
      )
    );

  const [role, setRole] =
    useState(
      localStorage.getItem(
        "role"
      )
    );


  function login(
    newToken,
    newRole
  ) {
    localStorage.setItem(
      "token",
      newToken
    );

    localStorage.setItem(
      "role",
      newRole
    );

    setToken(newToken);
    setRole(newRole);
  }


  function logout() {
    localStorage.removeItem(
      "token"
    );

    localStorage.removeItem(
      "role"
    );

    setToken(null);
    setRole(null);
  }


  return (
    <>

      <Navbar
        token={token}
        role={role}
        logout={logout}
      />

      <Routes>

        <Route
          path="/"
          element={
            <Home
              role={role}
            />
          }
        />

        <Route
          path="/register"
          element={
            <PatientRegister />
          }
        />

        <Route
          path="/patient-login"
          element={
            <PatientLogin
              login={login}
            />
          }
        />

        <Route
          path="/doctor-login"
          element={
            <DoctorLogin
              login={login}
            />
          }
        />

        <Route
          path="/doctors"
          element={
            <ProtectedRoute
              token={token}
              role={role}
              requiredRole="patient"
            >
              <Doctors />
            </ProtectedRoute>
          }
        />

        <Route
          path="/doctors/:doctorId/slots"
          element={
            <ProtectedRoute
              token={token}
              role={role}
              requiredRole="patient"
            >
              <DoctorSlots
                token={token}
              />
            </ProtectedRoute>
          }
        />

        <Route
          path="/appointments"
          element={
            <ProtectedRoute
              token={token}
              role={role}
              requiredRole="patient"
            >
              <MyAppointments
                token={token}
              />
            </ProtectedRoute>
          }
        />

        <Route
          path="/availability"
          element={
            <ProtectedRoute
              token={token}
              role={role}
              requiredRole="doctor"
            >
              <DoctorAvailability
                token={token}
              />
            </ProtectedRoute>
          }
        />

        <Route
          path="/schedule"
          element={
            <ProtectedRoute
              token={token}
              role={role}
              requiredRole="doctor"
            >
              <DoctorSchedule
                token={token}
              />
            </ProtectedRoute>
          }
        />

        <Route
          path="*"
          element={
            <Navigate
              to="/"
              replace
            />
          }
        />

      </Routes>

    </>
  );
}