from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.attendance import (
    ATTENDANCE_SOURCES,
    ATTENDANCE_STATUSES,
    AttendanceCreate,
    AttendanceUpdate,
)


ATTENDANCE_COLUMNS = """
    a.id,
    a.institution_id,
    a.student_id,
    a.subject_id,
    a.section_id,
    a.academic_period_id,
    a.attendance_date,
    a.status,
    a.source,
    a.source_import_id,
    a.marked_by_user_id,
    a.marked_by_faculty_id,
    a.correction_reason,
    a.created_at,
    a.updated_at
"""


CORRECTION_COLUMNS = """
    ac.id,
    ac.institution_id,
    ac.attendance_id,
    ac.old_status,
    ac.new_status,
    ac.reason,
    ac.changed_by_user_id,
    ac.changed_by_faculty_id,
    ac.source,
    ac.changed_at
"""


class AttendanceError(Exception):
    """Base attendance business-rule error."""


class AttendanceNotFoundError(AttendanceError):
    """Raised when an attendance record is not found."""


class AttendanceConflictError(AttendanceError):
    """Raised when attendance conflicts with an existing record."""


def _validate_status(status_value: str) -> str:
    value = status_value.strip().upper()

    if value not in ATTENDANCE_STATUSES:
        raise AttendanceError(
            "Invalid attendance status"
        )

    return value


def _validate_source(source_value: str) -> str:
    value = source_value.strip().upper()

    if value not in ATTENDANCE_SOURCES:
        raise AttendanceError(
            "Invalid attendance source"
        )

    return value


def _validate_reason(reason: str | None) -> str | None:
    if reason is None:
        return None

    normalized = reason.strip()

    if not normalized:
        raise AttendanceError(
            "Correction reason cannot be empty"
        )

    return normalized


def _validate_institution_scope(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
    subject_id: UUID,
    section_id: UUID,
    academic_period_id: UUID,
) -> dict:
    """
    Validate that all attendance dimensions belong to one coherent
    academic context inside the authenticated institution.

    Student membership is also checked through student academic history.
    """

    result = db.execute(
        text(
            """
            select
                s.id as student_id,
                s.institution_id as student_institution_id,

                sub.id as subject_id,
                sub.semester_id as subject_semester_id,

                sec.id as section_id,
                sec.semester_id as section_semester_id,
                sec.academic_period_id as section_academic_period_id,

                ap.id as academic_period_id,
                ap.academic_year_id,
                ap.program_id,
                ap.period_type,
                ap.period_number,
                ap.semester_id as period_semester_id,

                ay.institution_id as academic_year_institution_id,

                d.institution_id as department_institution_id,

                pah.section_id as student_history_section_id,
                pah.academic_year_id as student_history_academic_year_id,
                pah.program_id as student_history_program_id,
                pah.semester_id as student_history_semester_id

            from public.students s

            join public.subjects sub
              on sub.id = :subject_id

            join public.sections sec
              on sec.id = :section_id

            join public.academic_periods ap
              on ap.id = :academic_period_id

            join public.academic_years ay
              on ay.id = ap.academic_year_id

            join public.programs p
              on p.id = ap.program_id

            join public.departments d
              on d.id = p.department_id

            left join public.student_academic_history pah
              on pah.student_id = s.id
             and pah.academic_year_id = ap.academic_year_id
             and pah.semester_id = ap.semester_id
             and pah.program_id = ap.program_id
             and pah.section_id = sec.id

            where s.id = :student_id
              and s.institution_id = :institution_id
              and sub.id = :subject_id
              and sec.id = :section_id
              and ap.id = :academic_period_id

            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "student_id": student_id,
            "subject_id": subject_id,
            "section_id": section_id,
            "academic_period_id": academic_period_id,
        },
    )

    row = result.mappings().first()

    if row is None:
        raise AttendanceError(
            "Attendance context is not valid for the authenticated institution"
        )

    if row["student_institution_id"] != institution_id:
        raise AttendanceError(
            "Student is not valid for the authenticated institution"
        )

    if row["academic_year_institution_id"] != institution_id:
        raise AttendanceError(
            "Academic year is not valid for the authenticated institution"
        )

    if row["department_institution_id"] != institution_id:
        raise AttendanceError(
            "Academic program is not valid for the authenticated institution"
        )

    if row["subject_semester_id"] != row["section_semester_id"]:
        raise AttendanceError(
            "Subject and section do not belong to the same semester"
        )

    if row["period_type"] == "SEMESTER":
        if row["period_semester_id"] != row["section_semester_id"]:
            raise AttendanceError(
                "Academic period and section do not belong to the same semester"
            )

    if (
        row["section_academic_period_id"] is not None
        and row["section_academic_period_id"] != academic_period_id
    ):
        raise AttendanceError(
            "Section is not assigned to the selected academic period"
        )

    if row["student_history_section_id"] is None:
        raise AttendanceError(
            "Student does not have academic history for the selected section"
        )

    return dict(row)


def _get_faculty_for_user(
    db: Session,
    institution_id: UUID,
    user_id: UUID,
):
    result = db.execute(
        text(
            """
            select
                id,
                institution_id,
                user_profile_id,
                is_active
            from public.faculty
            where user_profile_id = :user_id
              and institution_id = :institution_id
            limit 1
            """
        ),
        {
            "user_id": user_id,
            "institution_id": institution_id,
        },
    )

    return result.mappings().first()


def _validate_faculty_assignment(
    db: Session,
    institution_id: UUID,
    user_id: UUID,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
):
    faculty = _get_faculty_for_user(
        db=db,
        institution_id=institution_id,
        user_id=user_id,
    )

    if faculty is None:
        raise AttendanceError(
            "Authenticated faculty profile was not found"
        )

    if not faculty["is_active"]:
        raise AttendanceError(
            "Inactive faculty cannot modify attendance"
        )

    result = db.execute(
        text(
            """
            select fa.id
            from public.faculty_assignments fa
            join public.faculty f
              on f.id = fa.faculty_id
            where fa.faculty_id = :faculty_id
              and fa.subject_id = :subject_id
              and fa.section_id = :section_id
              and fa.academic_year_id = :academic_year_id
              and fa.is_active = true
              and f.institution_id = :institution_id
              and fa.assignment_type in (
                  'SUBJECT',
                  'LAB_PRIMARY',
                  'LAB_SECONDARY'
              )
            limit 1
            """
        ),
        {
            "faculty_id": faculty["id"],
            "subject_id": subject_id,
            "section_id": section_id,
            "academic_year_id": academic_year_id,
            "institution_id": institution_id,
        },
    )

    assignment = result.first()

    if assignment is None:
        raise AttendanceError(
            "Faculty is not assigned to this subject and section"
        )

    return faculty["id"]


def _get_attendance(
    db: Session,
    institution_id: UUID,
    attendance_id: UUID,
):
    result = db.execute(
        text(
            f"""
            select {ATTENDANCE_COLUMNS}
            from public.attendance a
            where a.id = :attendance_id
              and a.institution_id = :institution_id
            limit 1
            """
        ),
        {
            "attendance_id": attendance_id,
            "institution_id": institution_id,
        },
    )

    return result.mappings().first()


def list_attendance(
    db: Session,
    institution_id: UUID,
    student_id: UUID | None = None,
    subject_id: UUID | None = None,
    section_id: UUID | None = None,
    academic_period_id: UUID | None = None,
    attendance_date: date | None = None,
):
    query = f"""
        select {ATTENDANCE_COLUMNS}
        from public.attendance a
        where a.institution_id = :institution_id
    """

    params: dict = {
        "institution_id": institution_id,
    }

    if student_id is not None:
        query += """
            and a.student_id = :student_id
        """
        params["student_id"] = student_id

    if subject_id is not None:
        query += """
            and a.subject_id = :subject_id
        """
        params["subject_id"] = subject_id

    if section_id is not None:
        query += """
            and a.section_id = :section_id
        """
        params["section_id"] = section_id

    if academic_period_id is not None:
        query += """
            and a.academic_period_id = :academic_period_id
        """
        params["academic_period_id"] = academic_period_id

    if attendance_date is not None:
        query += """
            and a.attendance_date = :attendance_date
        """
        params["attendance_date"] = attendance_date

    query += """
        order by
            a.attendance_date desc,
            a.student_id,
            a.subject_id
    """

    result = db.execute(
        text(query),
        params,
    )

    return result.mappings().all()


def get_attendance(
    db: Session,
    institution_id: UUID,
    attendance_id: UUID,
):
    return _get_attendance(
        db=db,
        institution_id=institution_id,
        attendance_id=attendance_id,
    )


def create_attendance(
    db: Session,
    institution_id: UUID,
    user_id: UUID,
    user_role: str,
    payload: AttendanceCreate,
):
    status_value = _validate_status(payload.status)
    source = _validate_source(payload.source)
    reason = _validate_reason(payload.correction_reason)

    if source != "DIRECT":
        raise AttendanceError(
            "Direct attendance API accepts only DIRECT source"
        )

    context = _validate_institution_scope(
        db=db,
        institution_id=institution_id,
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        section_id=payload.section_id,
        academic_period_id=payload.academic_period_id,
    )

    faculty_id = None

    if user_role == "faculty":
        faculty_id = _validate_faculty_assignment(
            db=db,
            institution_id=institution_id,
            user_id=user_id,
            subject_id=payload.subject_id,
            section_id=payload.section_id,
            academic_year_id=context["academic_year_id"],
        )

    existing = db.execute(
        text(
            """
            select id, status
            from public.attendance
            where institution_id = :institution_id
              and student_id = :student_id
              and subject_id = :subject_id
              and section_id = :section_id
              and academic_period_id = :academic_period_id
              and attendance_date = :attendance_date
            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "student_id": payload.student_id,
            "subject_id": payload.subject_id,
            "section_id": payload.section_id,
            "academic_period_id": payload.academic_period_id,
            "attendance_date": payload.attendance_date,
        },
    ).mappings().first()

    if existing is not None:
        if existing["status"] == status_value:
            raise AttendanceConflictError(
                "Attendance already exists with the requested status"
            )

        raise AttendanceConflictError(
            "Attendance already exists for this student, subject, "
            "section, academic period and date; use PATCH to correct it"
        )

    try:
        result = db.execute(
            text(
                f"""
                insert into public.attendance as a (
                    institution_id,
                    student_id,
                    subject_id,
                    section_id,
                    academic_period_id,
                    attendance_date,
                    status,
                    source,
                    marked_by_user_id,
                    marked_by_faculty_id,
                    correction_reason
                )
                values (
                    :institution_id,
                    :student_id,
                    :subject_id,
                    :section_id,
                    :academic_period_id,
                    :attendance_date,
                    :status,
                    :source,
                    :marked_by_user_id,
                    :marked_by_faculty_id,
                    :correction_reason
                )
                returning {ATTENDANCE_COLUMNS}
                """
            ),
            {
                "institution_id": institution_id,
                "student_id": payload.student_id,
                "subject_id": payload.subject_id,
                "section_id": payload.section_id,
                "academic_period_id": payload.academic_period_id,
                "attendance_date": payload.attendance_date,
                "status": status_value,
                "source": source,
                "marked_by_user_id": user_id,
                "marked_by_faculty_id": faculty_id,
                "correction_reason": reason,
            },
        )

        attendance = result.mappings().first()

        db.commit()

        return attendance

    except IntegrityError as exc:
        db.rollback()

        raise AttendanceConflictError(
            "Attendance already exists for this student, subject, "
            "section, academic period and date"
        ) from exc


def update_attendance(
    db: Session,
    institution_id: UUID,
    user_id: UUID,
    user_role: str,
    attendance_id: UUID,
    payload: AttendanceUpdate,
):
    new_status = _validate_status(payload.status)
    reason = _validate_reason(payload.correction_reason)

    if reason is None:
        raise AttendanceError(
            "Correction reason is required"
        )

    existing = _get_attendance(
        db=db,
        institution_id=institution_id,
        attendance_id=attendance_id,
    )

    if existing is None:
        raise AttendanceNotFoundError(
            "Attendance not found"
        )

    old_status = existing["status"]

    if old_status == new_status:
        raise AttendanceError(
            "New attendance status must differ from the existing status"
        )

    faculty_id = None

    if user_role == "faculty":
        faculty_id = _validate_faculty_assignment(
            db=db,
            institution_id=institution_id,
            user_id=user_id,
            subject_id=existing["subject_id"],
            section_id=existing["section_id"],
            academic_year_id=_get_academic_year_id(
                db=db,
                academic_period_id=existing["academic_period_id"],
            ),
        )

    try:
        result = db.execute(
            text(
                f"""
                update public.attendance as a
                set
                    status = :new_status,
                    correction_reason = :correction_reason,
                    marked_by_user_id = :marked_by_user_id,
                    marked_by_faculty_id = :marked_by_faculty_id,
                    updated_at = now()
                where id = :attendance_id
                  and institution_id = :institution_id
                returning {ATTENDANCE_COLUMNS}
                """
            ),
            {
                "new_status": new_status,
                "correction_reason": reason,
                "marked_by_user_id": user_id,
                "marked_by_faculty_id": faculty_id,
                "attendance_id": attendance_id,
                "institution_id": institution_id,
            },
        )

        attendance = result.mappings().first()

        if attendance is None:
            db.rollback()

            raise AttendanceNotFoundError(
                "Attendance not found"
            )

        db.execute(
            text(
                """
                insert into public.attendance_corrections (
                    institution_id,
                    attendance_id,
                    old_status,
                    new_status,
                    reason,
                    changed_by_user_id,
                    changed_by_faculty_id,
                    source
                )
                values (
                    :institution_id,
                    :attendance_id,
                    :old_status,
                    :new_status,
                    :reason,
                    :changed_by_user_id,
                    :changed_by_faculty_id,
                    'DIRECT'
                )
                """
            ),
            {
                "institution_id": institution_id,
                "attendance_id": attendance_id,
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
                "changed_by_user_id": user_id,
                "changed_by_faculty_id": faculty_id,
            },
        )

        db.commit()

        return attendance

    except IntegrityError as exc:
        db.rollback()

        raise AttendanceError(
            "Attendance correction could not be saved"
        ) from exc


def _get_academic_year_id(
    db: Session,
    academic_period_id: UUID,
) -> UUID:
    result = db.execute(
        text(
            """
            select academic_year_id
            from public.academic_periods
            where id = :academic_period_id
            limit 1
            """
        ),
        {
            "academic_period_id": academic_period_id,
        },
    )

    row = result.first()

    if row is None:
        raise AttendanceError(
            "Academic period not found"
        )

    return row[0]


def list_corrections(
    db: Session,
    institution_id: UUID,
    attendance_id: UUID,
):
    attendance = _get_attendance(
        db=db,
        institution_id=institution_id,
        attendance_id=attendance_id,
    )

    if attendance is None:
        raise AttendanceNotFoundError(
            "Attendance not found"
        )

    result = db.execute(
        text(
            f"""
            select {CORRECTION_COLUMNS}
            from public.attendance_corrections ac
            where ac.institution_id = :institution_id
              and ac.attendance_id = :attendance_id
            order by ac.changed_at desc, ac.id desc
            """
        ),
        {
            "institution_id": institution_id,
            "attendance_id": attendance_id,
        },
    )

    return result.mappings().all()

def create_bulk_attendance(
    db: Session,
    institution_id: UUID,
    user_id: UUID,
    user_role: str,
    payload,
):
    """
    Create attendance for multiple students as one atomic transaction.

    Business rules:
    - DIRECT source only.
    - Every student must belong to the selected academic context.
    - Faculty must be actively assigned to the subject/section.
    - Existing attendance records are rejected.
    - Duplicate students inside the request are rejected.
    - No rows are committed unless every validation succeeds.
    """

    source = _validate_source(payload.source)

    if source != "DIRECT":
        raise AttendanceError(
            "Bulk direct attendance API accepts only DIRECT source"
        )

    if not payload.records:
        raise AttendanceError(
            "At least one student attendance record is required"
        )

    student_ids = [record.student_id for record in payload.records]

    if len(student_ids) != len(set(student_ids)):
        raise AttendanceConflictError(
            "The same student cannot appear more than once in one "
            "bulk attendance submission"
        )

    normalized_records = []

    for record in payload.records:
        status_value = _validate_status(record.status)

        normalized_records.append(
            {
                "student_id": record.student_id,
                "status": status_value,
            }
        )

    first_context = _validate_institution_scope(
        db=db,
        institution_id=institution_id,
        student_id=student_ids[0],
        subject_id=payload.subject_id,
        section_id=payload.section_id,
        academic_period_id=payload.academic_period_id,
    )

    faculty_id = None

    if user_role == "faculty":
        faculty_id = _validate_faculty_assignment(
            db=db,
            institution_id=institution_id,
            user_id=user_id,
            subject_id=payload.subject_id,
            section_id=payload.section_id,
            academic_year_id=first_context["academic_year_id"],
        )

    validated_contexts = []

    for record in normalized_records:
        context = _validate_institution_scope(
            db=db,
            institution_id=institution_id,
            student_id=record["student_id"],
            subject_id=payload.subject_id,
            section_id=payload.section_id,
            academic_period_id=payload.academic_period_id,
        )

        validated_contexts.append(context)

    for record in normalized_records:
        existing = db.execute(
            text(
                """
                select id, status
                from public.attendance
                where institution_id = :institution_id
                  and student_id = :student_id
                  and subject_id = :subject_id
                  and section_id = :section_id
                  and academic_period_id = :academic_period_id
                  and attendance_date = :attendance_date
                limit 1
                """
            ),
            {
                "institution_id": institution_id,
                "student_id": record["student_id"],
                "subject_id": payload.subject_id,
                "section_id": payload.section_id,
                "academic_period_id": payload.academic_period_id,
                "attendance_date": payload.attendance_date,
            },
        ).mappings().first()

        if existing is not None:
            raise AttendanceConflictError(
                "Attendance already exists for one or more students "
                "for this subject, section, academic period and date; "
                "use PATCH to correct existing attendance"
            )

    saved_records = []

    try:
        for record in normalized_records:
            result = db.execute(
                text(
                    f"""
                    insert into public.attendance as a (
                        institution_id,
                        student_id,
                        subject_id,
                        section_id,
                        academic_period_id,
                        attendance_date,
                        status,
                        source,
                        marked_by_user_id,
                        marked_by_faculty_id
                    )
                    values (
                        :institution_id,
                        :student_id,
                        :subject_id,
                        :section_id,
                        :academic_period_id,
                        :attendance_date,
                        :status,
                        :source,
                        :marked_by_user_id,
                        :marked_by_faculty_id
                    )
                    returning {ATTENDANCE_COLUMNS}
                    """
                ),
                {
                    "institution_id": institution_id,
                    "student_id": record["student_id"],
                    "subject_id": payload.subject_id,
                    "section_id": payload.section_id,
                    "academic_period_id": payload.academic_period_id,
                    "attendance_date": payload.attendance_date,
                    "status": record["status"],
                    "source": source,
                    "marked_by_user_id": user_id,
                    "marked_by_faculty_id": faculty_id,
                },
            )

            attendance = result.mappings().first()

            if attendance is None:
                raise AttendanceError(
                    "Bulk attendance record could not be created"
                )

            saved_records.append(attendance)

        db.commit()

        return saved_records

    except IntegrityError as exc:
        db.rollback()

        raise AttendanceConflictError(
            "Bulk attendance could not be saved because one or more "
            "attendance records already exist"
        ) from exc

    except Exception:
        db.rollback()
        raise
