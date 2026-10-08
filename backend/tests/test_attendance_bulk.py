from datetime import date
from uuid import UUID, uuid4

import pytest

from app.models.attendance import AttendanceBulkCreate, AttendanceBulkItem
from app.services.attendance_service import (
    AttendanceConflictError,
    AttendanceError,
    create_bulk_attendance,
)


INSTITUTION_ID = UUID("11111111-1111-1111-1111-111111111111")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")

ACADEMIC_YEAR_ID = UUID("33333333-3333-3333-3333-333333333333")
PROGRAM_ID = UUID("44444444-4444-4444-4444-444444444444")
ACADEMIC_PERIOD_ID = UUID("55555555-5555-5555-5555-555555555555")
SECTION_ID = UUID("66666666-6666-6666-6666-666666666666")
SUBJECT_ID = UUID("77777777-7777-7777-7777-777777777777")

STUDENT_1 = UUID("88888888-8888-8888-8888-888888888881")
STUDENT_2 = UUID("88888888-8888-8888-8888-888888888882")
STUDENT_3 = UUID("88888888-8888-8888-8888-888888888883")


class FakeResult:
    def __init__(self, mapping=None, mappings=None):
        self._mapping = mapping
        self._mappings = mappings or []

    def mappings(self):
        return self

    def first(self):
        return self._mapping

    def all(self):
        return self._mappings

    def fetchone(self):
        return self._mapping


class FakeBulkDatabase:
    def __init__(self):
        self.saved_records = []
        self.existing_students = set()
        self.commit_count = 0
        self.rollback_count = 0

    def execute(self, statement, params=None):
        sql = str(statement)

        if "from public.students s" in sql:
            student_id = params["student_id"]

            if student_id not in {
                STUDENT_1,
                STUDENT_2,
                STUDENT_3,
            }:
                return FakeResult()

            return FakeResult(
                mapping={
                    "student_id": student_id,
                    "student_institution_id": INSTITUTION_ID,
                    "subject_id": SUBJECT_ID,
                    "subject_semester_id": UUID(
                        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                    ),
                    "section_id": SECTION_ID,
                    "section_semester_id": UUID(
                        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                    ),
                    "section_academic_period_id": ACADEMIC_PERIOD_ID,
                    "academic_period_id": ACADEMIC_PERIOD_ID,
                    "academic_year_id": ACADEMIC_YEAR_ID,
                    "program_id": PROGRAM_ID,
                    "period_type": "SEMESTER",
                    "period_number": 1,
                    "period_semester_id": UUID(
                        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                    ),
                    "academic_year_institution_id": INSTITUTION_ID,
                    "department_institution_id": INSTITUTION_ID,
                    "student_history_section_id": SECTION_ID,
                    "student_history_academic_year_id": ACADEMIC_YEAR_ID,
                    "student_history_program_id": PROGRAM_ID,
                    "student_history_semester_id": UUID(
                        "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
                    ),
                }
            )

        if (
            "select id, status" in sql
            and "from public.attendance" in sql
        ):
            student_id = params["student_id"]

            if student_id in self.existing_students:
                return FakeResult(
                    mapping={
                        "id": uuid4(),
                        "status": "PRESENT",
                    }
                )

            return FakeResult()

        if "insert into public.attendance" in sql:
            student_id = params["student_id"]

            record = {
                "id": uuid4(),
                "institution_id": params["institution_id"],
                "student_id": student_id,
                "subject_id": params["subject_id"],
                "section_id": params["section_id"],
                "academic_period_id": params["academic_period_id"],
                "attendance_date": params["attendance_date"],
                "status": params["status"],
                "source": params["source"],
                "source_import_id": None,
                "marked_by_user_id": params["marked_by_user_id"],
                "marked_by_faculty_id": params[
                    "marked_by_faculty_id"
                ],
                "correction_reason": None,
                "created_at": None,
                "updated_at": None,
            }

            self.saved_records.append(record)

            return FakeResult(mapping=record)

        raise AssertionError(f"Unexpected SQL: {sql}")

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1
        self.saved_records.clear()


def make_payload(
    records: list[AttendanceBulkItem],
) -> AttendanceBulkCreate:
    return AttendanceBulkCreate(
        subject_id=SUBJECT_ID,
        section_id=SECTION_ID,
        academic_period_id=ACADEMIC_PERIOD_ID,
        attendance_date=date(2026, 10, 8),
        source="DIRECT",
        records=records,
    )


def test_bulk_attendance_saves_all_students_atomically(monkeypatch):
    db = FakeBulkDatabase()

    result = create_bulk_attendance(
        db=db,
        institution_id=INSTITUTION_ID,
        user_id=USER_ID,
        user_role="principal",
        payload=make_payload(
            [
                AttendanceBulkItem(
                    student_id=STUDENT_1,
                    status="PRESENT",
                ),
                AttendanceBulkItem(
                    student_id=STUDENT_2,
                    status="ABSENT",
                ),
                AttendanceBulkItem(
                    student_id=STUDENT_3,
                    status="LATE",
                ),
            ]
        ),
    )

    assert len(result) == 3
    assert len(db.saved_records) == 3
    assert db.commit_count == 1
    assert db.rollback_count == 0

    assert [record["student_id"] for record in result] == [
        STUDENT_1,
        STUDENT_2,
        STUDENT_3,
    ]


def test_bulk_attendance_rejects_duplicate_student():
    db = FakeBulkDatabase()

    with pytest.raises(
        AttendanceConflictError,
        match="same student cannot appear more than once",
    ):
        create_bulk_attendance(
            db=db,
            institution_id=INSTITUTION_ID,
            user_id=USER_ID,
            user_role="principal",
            payload=make_payload(
                [
                    AttendanceBulkItem(
                        student_id=STUDENT_1,
                        status="PRESENT",
                    ),
                    AttendanceBulkItem(
                        student_id=STUDENT_1,
                        status="ABSENT",
                    ),
                ]
            ),
        )

    assert db.saved_records == []
    assert db.commit_count == 0


def test_bulk_attendance_rejects_invalid_status():
    db = FakeBulkDatabase()

    with pytest.raises(
        AttendanceError,
        match="Invalid attendance status",
    ):
        create_bulk_attendance(
            db=db,
            institution_id=INSTITUTION_ID,
            user_id=USER_ID,
            user_role="principal",
            payload=make_payload(
                [
                    AttendanceBulkItem(
                        student_id=STUDENT_1,
                        status="PRESENT",
                    ),
                    AttendanceBulkItem(
                        student_id=STUDENT_2,
                        status="INVALID",
                    ),
                ]
            ),
        )

    assert db.saved_records == []
    assert db.commit_count == 0


def test_bulk_attendance_rejects_existing_attendance():
    db = FakeBulkDatabase()
    db.existing_students.add(STUDENT_2)

    with pytest.raises(
        AttendanceConflictError,
        match="Attendance already exists",
    ):
        create_bulk_attendance(
            db=db,
            institution_id=INSTITUTION_ID,
            user_id=USER_ID,
            user_role="principal",
            payload=make_payload(
                [
                    AttendanceBulkItem(
                        student_id=STUDENT_1,
                        status="PRESENT",
                    ),
                    AttendanceBulkItem(
                        student_id=STUDENT_2,
                        status="ABSENT",
                    ),
                ]
            ),
        )

    assert db.saved_records == []
    assert db.commit_count == 0


def test_bulk_attendance_rejects_non_direct_source():
    db = FakeBulkDatabase()

    payload = AttendanceBulkCreate(
        subject_id=SUBJECT_ID,
        section_id=SECTION_ID,
        academic_period_id=ACADEMIC_PERIOD_ID,
        attendance_date=date(2026, 10, 8),
        source="GOOGLE_SHEETS",
        records=[
            AttendanceBulkItem(
                student_id=STUDENT_1,
                status="PRESENT",
            )
        ],
    )

    with pytest.raises(
        AttendanceError,
        match="only DIRECT source",
    ):
        create_bulk_attendance(
            db=db,
            institution_id=INSTITUTION_ID,
            user_id=USER_ID,
            user_role="principal",
            payload=payload,
        )

    assert db.saved_records == []
    assert db.commit_count == 0


def test_bulk_attendance_rejects_student_outside_institution_context():
    db = FakeBulkDatabase()

    invalid_student = UUID(
        "99999999-9999-9999-9999-999999999999"
    )

    with pytest.raises(
        AttendanceError,
        match="Attendance context is not valid",
    ):
        create_bulk_attendance(
            db=db,
            institution_id=INSTITUTION_ID,
            user_id=USER_ID,
            user_role="principal",
            payload=make_payload(
                [
                    AttendanceBulkItem(
                        student_id=STUDENT_1,
                        status="PRESENT",
                    ),
                    AttendanceBulkItem(
                        student_id=invalid_student,
                        status="ABSENT",
                    ),
                ]
            ),
        )

    assert db.saved_records == []
    assert db.commit_count == 0