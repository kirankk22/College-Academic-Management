import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getAcademicPeriods,
  getAcademicYears,
  getAttendanceStudents,
  getHealth,
  getPrograms,
  getSections,
  getSubjects,
} from "./api";

const ACCESS_TOKEN = "test-access-token";

afterEach(() => {
  vi.restoreAllMocks();
});

describe("API service", () => {
  it("gets backend health without authentication", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify({
            status: "ok",
            service: "college-academic-management-api",
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
            },
          },
        ),
      );

    const result = await getHealth();

    expect(result.status).toBe("ok");
    expect(result.service).toBe(
      "college-academic-management-api",
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, options] =
      fetchMock.mock.calls[0];

    expect(String(url)).toContain("/health");

    expect(
      new Headers(
        (options as RequestInit).headers,
      ).get("Authorization"),
    ).toBeNull();
  });

  it("gets academic years with bearer authentication", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify([
          {
            id: "year-1",
            institution_id: "institution-1",
            name: "2026-27",
            start_date: "2026-06-01",
            end_date: "2027-05-31",
            is_current: true,
          },
        ]),
        { status: 200 },
      ),
    );

    const result =
      await getAcademicYears(ACCESS_TOKEN);

    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("2026-27");
  });

  it("builds the program request with academic year", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response("[]", { status: 200 }),
      );

    await getPrograms(
      ACCESS_TOKEN,
      "academic-year-1",
    );

    const [url, options] =
      fetchMock.mock.calls[0];

    expect(String(url)).toContain(
      "/api/v1/programs?",
    );

    expect(String(url)).toContain(
      "academic_year_id=academic-year-1",
    );

    const headers = new Headers(
      (options as RequestInit).headers,
    );

    expect(
      headers.get("Authorization"),
    ).toBe(`Bearer ${ACCESS_TOKEN}`);
  });

  it("builds the academic period request", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response("[]", { status: 200 }),
      );

    await getAcademicPeriods(
      ACCESS_TOKEN,
      "year-1",
      "program-1",
    );

    const [url] =
      fetchMock.mock.calls[0];

    expect(String(url)).toContain(
      "academic_year_id=year-1",
    );

    expect(String(url)).toContain(
      "program_id=program-1",
    );
  });

  it("builds the section request", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response("[]", { status: 200 }),
      );

    await getSections(
      ACCESS_TOKEN,
      "period-1",
    );

    const [url] =
      fetchMock.mock.calls[0];

    expect(String(url)).toContain(
      "/api/v1/sections?",
    );

    expect(String(url)).toContain(
      "academic_period_id=period-1",
    );
  });

  it("builds the subject request", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response("[]", { status: 200 }),
      );

    await getSubjects(
      ACCESS_TOKEN,
      "period-1",
    );

    const [url] =
      fetchMock.mock.calls[0];

    expect(String(url)).toContain(
      "/api/v1/subjects?",
    );

    expect(String(url)).toContain(
      "academic_period_id=period-1",
    );
  });

  it("gets attendance-context students", async () => {
    const student = {
      student_id: "student-1",
      permanent_student_id: "MCA26-001",
      student_name: "Arjun Sharma",
      roll_number: "MCA-S1-001",
      student_status: "active",
      academic_history_id: "history-1",
    };

    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(
          JSON.stringify([student]),
          { status: 200 },
        ),
      );

    const result =
      await getAttendanceStudents(
        ACCESS_TOKEN,
        "year-1",
        "program-1",
        "period-1",
        "section-1",
      );

    expect(result).toEqual([student]);

    const [url, options] =
      fetchMock.mock.calls[0];

    expect(String(url)).toContain(
      "/api/v1/attendance/students?",
    );

    expect(String(url)).toContain(
      "academic_year_id=year-1",
    );

    expect(String(url)).toContain(
      "program_id=program-1",
    );

    expect(String(url)).toContain(
      "academic_period_id=period-1",
    );

    expect(String(url)).toContain(
      "section_id=section-1",
    );

    const headers = new Headers(
      (options as RequestInit).headers,
    );

    expect(
      headers.get("Authorization"),
    ).toBe(`Bearer ${ACCESS_TOKEN}`);
  });

  it("throws the backend detail for failed requests", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          detail: "Invalid academic context",
        }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        },
      ),
    );

    await expect(
      getAttendanceStudents(
        ACCESS_TOKEN,
        "year-1",
        "program-1",
        "period-1",
        "section-1",
      ),
    ).rejects.toThrow(
      "Invalid academic context",
    );
  });

  it("requires authentication for protected APIs", () => {
    expect(() =>
      getAcademicYears(""),
    ).toThrow(
      "Authentication is required for this operation",
    );
  });
});