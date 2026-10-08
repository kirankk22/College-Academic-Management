import {
  useEffect,
  useState,
} from "react";
import type { Session } from "@supabase/supabase-js";

import {
  getAcademicPeriods,
  getAcademicYears,
  getAttendanceStudents,
  getPrograms,
  getSections,
  getSubjects,
  type AcademicPeriod,
  type AcademicYear,
  type AttendanceStudent,
  type Program,
  type Section,
  type Subject,
} from "./services/api";
import {
  getSession,
  signIn,
  signOut,
  subscribeToAuthChanges,
} from "./services/auth";

interface AcademicContext {
  academicYear: AcademicYear | null;
  program: Program | null;
  academicPeriod: AcademicPeriod | null;
  section: Section | null;
  subjects: Subject[];
  students: AttendanceStudent[];
}

const EMPTY_CONTEXT: AcademicContext = {
  academicYear: null,
  program: null,
  academicPeriod: null,
  section: null,
  subjects: [],
  students: [],
};

export default function App() {
  const [session, setSession] =
    useState<Session | null>(null);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(true);
  const [loginLoading, setLoginLoading] =
    useState(false);

  const [error, setError] = useState("");

  const [academicYears, setAcademicYears] =
    useState<AcademicYear[]>([]);
  const [programs, setPrograms] =
    useState<Program[]>([]);
  const [academicPeriods, setAcademicPeriods] =
    useState<AcademicPeriod[]>([]);
  const [sections, setSections] =
    useState<Section[]>([]);

  const [selectedYearId, setSelectedYearId] =
    useState("");
  const [selectedProgramId, setSelectedProgramId] =
    useState("");
  const [selectedPeriodId, setSelectedPeriodId] =
    useState("");
  const [selectedSectionId, setSelectedSectionId] =
    useState("");

  const [context, setContext] =
    useState<AcademicContext>(EMPTY_CONTEXT);

  useEffect(() => {
    let mounted = true;

    getSession()
      .then((currentSession) => {
        if (mounted) {
          setSession(currentSession);
        }
      })
      .catch((err: unknown) => {
        if (mounted) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load session",
          );
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    const unsubscribe =
      subscribeToAuthChanges((currentSession) => {
        if (mounted) {
          setSession(currentSession);
        }
      });

    return () => {
      mounted = false;
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!session?.access_token) {
      return;
    }

    setError("");

    getAcademicYears(session.access_token)
      .then((years) => {
        setAcademicYears(years);

        const currentYear =
          years.find((year) => year.is_current) ??
          years[0];

        if (currentYear) {
          setSelectedYearId(currentYear.id);
        }
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load academic years",
        );
      });
  }, [session]);

  useEffect(() => {
    if (
      !session?.access_token ||
      !selectedYearId
    ) {
      setPrograms([]);
      setSelectedProgramId("");
      return;
    }

    setError("");

    getPrograms(
      session.access_token,
      selectedYearId,
    )
      .then((items) => {
        setPrograms(items);

        const activeProgram =
          items.find((item) => item.is_active) ??
          items[0];

        setSelectedProgramId(
          activeProgram?.id ?? "",
        );
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load programs",
        );
      });
  }, [session, selectedYearId]);

  useEffect(() => {
    if (
      !session?.access_token ||
      !selectedYearId ||
      !selectedProgramId
    ) {
      setAcademicPeriods([]);
      setSelectedPeriodId("");
      return;
    }

    setError("");

    getAcademicPeriods(
      session.access_token,
      selectedYearId,
      selectedProgramId,
    )
      .then((items) => {
        const activePeriods = items.filter(
          (item) => item.is_active,
        );

        setAcademicPeriods(activePeriods);

        const firstSemester =
          activePeriods.find(
            (item) =>
              item.period_type === "SEMESTER",
          ) ?? activePeriods[0];

        setSelectedPeriodId(
          firstSemester?.id ?? "",
        );
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load academic periods",
        );
      });
  }, [
    session,
    selectedYearId,
    selectedProgramId,
  ]);

  useEffect(() => {
    if (
      !session?.access_token ||
      !selectedPeriodId
    ) {
      setSections([]);
      setSelectedSectionId("");
      return;
    }

    setError("");

    getSections(
      session.access_token,
      selectedPeriodId,
    )
      .then((items) => {
        const activeSections = items.filter(
          (item) => item.is_active,
        );

        setSections(activeSections);
        setSelectedSectionId(
          activeSections[0]?.id ?? "",
        );
      })
      .catch((err: unknown) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load sections",
        );
      });
  }, [session, selectedPeriodId]);

  async function loadAttendanceContext() {
    if (!session?.access_token) {
      setError("Authentication is required");
      return;
    }

    if (
      !selectedYearId ||
      !selectedProgramId ||
      !selectedPeriodId ||
      !selectedSectionId
    ) {
      setError(
        "Select academic year, program, academic period and section",
      );
      return;
    }

    setError("");

    try {
      const [
        selectedSubjects,
        selectedStudents,
      ] = await Promise.all([
        getSubjects(
          session.access_token,
          selectedPeriodId,
        ),
        getAttendanceStudents(
          session.access_token,
          selectedYearId,
          selectedProgramId,
          selectedPeriodId,
          selectedSectionId,
        ),
      ]);

      setContext({
        academicYear:
          academicYears.find(
            (item) =>
              item.id === selectedYearId,
          ) ?? null,

        program:
          programs.find(
            (item) =>
              item.id === selectedProgramId,
          ) ?? null,

        academicPeriod:
          academicPeriods.find(
            (item) =>
              item.id === selectedPeriodId,
          ) ?? null,

        section:
          sections.find(
            (item) =>
              item.id === selectedSectionId,
          ) ?? null,

        subjects: selectedSubjects.filter(
          (item) => item.is_active,
        ),

        students: selectedStudents,
      });
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load attendance context",
      );
    }
  }

  async function handleLogin(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    setError("");
    setLoginLoading(true);

    try {
      const newSession = await signIn(
        email.trim(),
        password,
      );

      setSession(newSession);
      setPassword("");
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Login failed",
      );
    } finally {
      setLoginLoading(false);
    }
  }

  async function handleLogout() {
    setError("");

    try {
      await signOut();
      setSession(null);
      setContext(EMPTY_CONTEXT);
      setAcademicYears([]);
      setPrograms([]);
      setAcademicPeriods([]);
      setSections([]);
      setSelectedYearId("");
      setSelectedProgramId("");
      setSelectedPeriodId("");
      setSelectedSectionId("");
    } catch (err: unknown) {
      setError(
        err instanceof Error
          ? err.message
          : "Logout failed",
      );
    }
  }

  if (loading) {
    return (
      <main style={styles.page}>
        <h1>College Academic Management</h1>
        <p>Loading authentication...</p>
      </main>
    );
  }

  if (!session) {
    return (
      <main style={styles.page}>
        <section style={styles.card}>
          <h1>College Academic Management</h1>
          <p style={styles.muted}>
            Direct Attendance Foundation
          </p>

          <h2>Sign in</h2>

          <form
            onSubmit={handleLogin}
            style={styles.form}
          >
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                required
              />
            </label>

            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) =>
                  setPassword(event.target.value)
                }
                required
              />
            </label>

            <button
              type="submit"
              disabled={loginLoading}
            >
              {loginLoading
                ? "Signing in..."
                : "Sign in"}
            </button>
          </form>

          {error && (
            <p style={styles.error}>{error}</p>
          )}
        </section>
      </main>
    );
  }

  return (
    <main style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1>College Academic Management</h1>
          <p style={styles.muted}>
            Direct Attendance Foundation
          </p>
        </div>

        <button
          type="button"
          onClick={handleLogout}
        >
          Sign out
        </button>
      </header>

      {error && (
        <div style={styles.errorBox}>
          {error}
        </div>
      )}

      <section style={styles.card}>
        <h2>Academic Context</h2>

        <div style={styles.grid}>
          <label>
            Academic Year
            <select
              value={selectedYearId}
              onChange={(event) => {
                setSelectedYearId(
                  event.target.value,
                );
                setContext(EMPTY_CONTEXT);
              }}
            >
              <option value="">
                Select academic year
              </option>

              {academicYears.map((year) => (
                <option
                  key={year.id}
                  value={year.id}
                >
                  {year.name}
                  {year.is_current
                    ? " (Current)"
                    : ""}
                </option>
              ))}
            </select>
          </label>

          <label>
            Program
            <select
              value={selectedProgramId}
              onChange={(event) => {
                setSelectedProgramId(
                  event.target.value,
                );
                setContext(EMPTY_CONTEXT);
              }}
            >
              <option value="">
                Select program
              </option>

              {programs.map((program) => (
                <option
                  key={program.id}
                  value={program.id}
                >
                  {program.name} (
                  {program.code})
                </option>
              ))}
            </select>
          </label>

          <label>
            Academic Period
            <select
              value={selectedPeriodId}
              onChange={(event) => {
                setSelectedPeriodId(
                  event.target.value,
                );
                setContext(EMPTY_CONTEXT);
              }}
            >
              <option value="">
                Select academic period
              </option>

              {academicPeriods.map(
                (period) => (
                  <option
                    key={period.id}
                    value={period.id}
                  >
                    {period.period_name}
                  </option>
                ),
              )}
            </select>
          </label>

          <label>
            Section
            <select
              value={selectedSectionId}
              onChange={(event) => {
                setSelectedSectionId(
                  event.target.value,
                );
                setContext(EMPTY_CONTEXT);
              }}
            >
              <option value="">
                Select section
              </option>

              {sections.map((section) => (
                <option
                  key={section.id}
                  value={section.id}
                >
                  {section.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <button
          type="button"
          onClick={loadAttendanceContext}
          style={styles.primaryButton}
        >
          Load Attendance Context
        </button>
      </section>

      {context.academicPeriod && (
        <section style={styles.card}>
          <h2>Attendance Context</h2>

          <p>
            <strong>
              {context.academicYear?.name}
            </strong>
            {" → "}
            <strong>
              {context.program?.name}
            </strong>
            {" → "}
            <strong>
              {context.academicPeriod.period_name}
            </strong>
            {" → "}
            <strong>
              {context.section?.name}
            </strong>
          </p>

          <h3>Subjects</h3>

          {context.subjects.length === 0 ? (
            <p style={styles.muted}>
              No active subjects found.
            </p>
          ) : (
            <ul>
              {context.subjects.map(
                (subject) => (
                  <li key={subject.id}>
                    {subject.code} —{" "}
                    {subject.name}
                    {subject.has_lab
                      ? " — Lab"
                      : ""}
                  </li>
                ),
              )}
            </ul>
          )}

          <h3>
            Students ({context.students.length})
          </h3>

          {context.students.length === 0 ? (
            <p style={styles.muted}>
              No active students found for
              this academic context.
            </p>
          ) : (
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.cell}>
                    Permanent Student ID
                  </th>
                  <th style={styles.cell}>
                    Roll Number
                  </th>
                  <th style={styles.cell}>
                    Student Name
                  </th>
                  <th style={styles.cell}>
                    Status
                  </th>
                </tr>
              </thead>

              <tbody>
                {context.students.map(
                  (student) => (
                    <tr
                      key={
                        student.student_id
                      }
                    >
                      <td style={styles.cell}>
                        {
                          student.permanent_student_id
                        }
                      </td>
                      <td style={styles.cell}>
                        {student.roll_number ??
                          "—"}
                      </td>
                      <td style={styles.cell}>
                        {student.student_name}
                      </td>
                      <td style={styles.cell}>
                        {student.student_status}
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          )}
        </section>
      )}
    </main>
  );
}

const styles: Record<
  string,
  React.CSSProperties
> = {
  page: {
    fontFamily:
      "Arial, sans-serif",
    padding: 32,
    maxWidth: 1200,
    margin: "0 auto",
    backgroundColor: "#f7f7f7",
    minHeight: "100vh",
  },

  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 20,
    marginBottom: 24,
  },

  card: {
    backgroundColor: "#ffffff",
    border: "1px solid #dddddd",
    borderRadius: 10,
    padding: 24,
    marginBottom: 20,
  },

  form: {
    display: "grid",
    gap: 16,
    maxWidth: 420,
  },

  grid: {
    display: "grid",
    gridTemplateColumns:
      "repeat(auto-fit, minmax(220px, 1fr))",
    gap: 16,
    marginBottom: 20,
  },

  muted: {
    color: "#666666",
  },

  error: {
    color: "#b00020",
    marginTop: 16,
  },

  errorBox: {
    backgroundColor: "#fff0f0",
    border: "1px solid #e0aaaa",
    borderRadius: 8,
    padding: 12,
    marginBottom: 20,
    color: "#8b0000",
  },

  primaryButton: {
    padding: "10px 16px",
    cursor: "pointer",
  },

  table: {
    width: "100%",
    borderCollapse: "collapse",
  },

  cell: {
    border: "1px solid #dddddd",
    padding: 10,
    textAlign: "left",
  },
};
