import { env } from "../config/env";

export interface HealthResponse {
  status: string;
  service: string;
}

export interface AcademicYear {
  id: string;
  institution_id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

export interface Program {
  id: string;
  department_id: string;
  name: string;
  code: string;
  academic_structure_type: string;
  duration_units: number;
  is_active: boolean;
}

export interface AcademicPeriod {
  id: string;
  academic_year_id: string;
  program_id: string;
  period_type: string;
  period_number: number;
  semester_id: string | null;
  period_name: string;
  semester_cycle: string | null;
  is_active: boolean;
}

export interface Section {
  id: string;
  academic_period_id: string;
  semester_id: string;
  name: string;
  is_active: boolean;
}

export interface Subject {
  id: string;
  semester_id: string;
  code: string;
  name: string;
  credits: number | null;
  is_active: boolean;
  has_lab: boolean;
}

export interface AttendanceStudent {
  student_id: string;
  permanent_student_id: string;
  student_name: string;
  roll_number: string | null;
  student_status: string;
  academic_history_id: string;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  accessToken?: string,
): Promise<T> {
  const headers = new Headers(options.headers);

  headers.set("Content-Type", "application/json");

  if (accessToken) {
    headers.set(
      "Authorization",
      `Bearer ${accessToken}`,
    );
  }

  const response = await fetch(
    `${env.apiBaseUrl}${path}`,
    {
      ...options,
      headers,
    },
  );

  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;

    try {
      const body = await response.json();

      if (typeof body?.detail === "string") {
        detail = body.detail;
      }
    } catch {
      // Keep the HTTP status message when the response
      // body is not JSON.
    }

    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

function requireAccessToken(
  accessToken: string | null | undefined,
): string {
  if (!accessToken) {
    throw new Error(
      "Authentication is required for this operation",
    );
  }

  return accessToken;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getAcademicYears(
  accessToken: string,
): Promise<AcademicYear[]> {
  return request<AcademicYear[]>(
    "/api/v1/academic-years",
    {},
    requireAccessToken(accessToken),
  );
}

export function getPrograms(
  accessToken: string,
  academicYearId: string,
): Promise<Program[]> {
  const params = new URLSearchParams({
    academic_year_id: academicYearId,
  });

  return request<Program[]>(
    `/api/v1/programs?${params.toString()}`,
    {},
    requireAccessToken(accessToken),
  );
}

export function getAcademicPeriods(
  accessToken: string,
  academicYearId: string,
  programId: string,
): Promise<AcademicPeriod[]> {
  const params = new URLSearchParams({
    academic_year_id: academicYearId,
    program_id: programId,
  });

  return request<AcademicPeriod[]>(
    `/api/v1/academic-periods?${params.toString()}`,
    {},
    requireAccessToken(accessToken),
  );
}

export function getSections(
  accessToken: string,
  academicPeriodId: string,
): Promise<Section[]> {
  const params = new URLSearchParams({
    academic_period_id: academicPeriodId,
  });

  return request<Section[]>(
    `/api/v1/sections?${params.toString()}`,
    {},
    requireAccessToken(accessToken),
  );
}

export function getSubjects(
  accessToken: string,
  academicPeriodId: string,
): Promise<Subject[]> {
  const params = new URLSearchParams({
    academic_period_id: academicPeriodId,
  });

  return request<Subject[]>(
    `/api/v1/subjects?${params.toString()}`,
    {},
    requireAccessToken(accessToken),
  );
}

export function getAttendanceStudents(
  accessToken: string,
  academicYearId: string,
  programId: string,
  academicPeriodId: string,
  sectionId: string,
): Promise<AttendanceStudent[]> {
  const params = new URLSearchParams({
    academic_year_id: academicYearId,
    program_id: programId,
    academic_period_id: academicPeriodId,
    section_id: sectionId,
  });

  return request<AttendanceStudent[]>(
    `/api/v1/attendance/students?${params.toString()}`,
    {},
    requireAccessToken(accessToken),
  );
}