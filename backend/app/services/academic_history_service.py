from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.academic_history import (
    AcademicHistoryCreate,
    SemesterResultCreate,
)


ACADEMIC_HISTORY_COLUMNS = """
    id,
    student_id,
    academic_year_id,
    program_id,
    semester_id,
    section_id,
    roll_number,
    status,
    start_date,
    end_date
"""


SEMESTER_RESULT_COLUMNS = """
    id,
    student_id,
    academic_year_id,
    program_id,
    semester_id,
    result_status,
    progression_status,
    result_date,
    remarks
"""


class AcademicHistoryError(Exception):
    """Raised when academic history validation fails."""


class SemesterResultError(Exception):
    """Raised when semester-result validation fails."""


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _validate_history_status(status: str) -> None:
    allowed = {
        "active",
        "completed",
        "promoted",
        "detained",
        "withdrawn",
        "transferred",
    }

    if status not in allowed:
        raise AcademicHistoryError(
            "Invalid academic history status"
        )


def _validate_result_status(result_status: str) -> None:
    allowed = {
        "pending",
        "pass",
        "fail",
    }

    if result_status not in allowed:
        raise SemesterResultError(
            "Invalid semester result status"
        )


def _get_student(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
):
    result = db.execute(
        text(
            """
            select id
            from public.students
            where id = :student_id
              and institution_id = :institution_id
            limit 1
            """
        ),
        {
            "student_id": student_id,
            "institution_id": institution_id,
        },
    )

    return result.first()


def _get_academic_context(
    db: Session,
    institution_id: UUID,
    academic_year_id: UUID,
    program_id: UUID,
    semester_id: UUID,
    section_id: UUID,
):
    result = db.execute(
        text(
            """
            select
                ay.id as academic_year_id,
                p.id as program_id,
                s.id as semester_id,
                sec.id as section_id,
                s.semester_number,
                p.duration_semesters
            from public.academic_years ay
            join public.institutions i
              on i.id = ay.institution_id
            join public.programs p
              on p.id = :program_id
            join public.departments d
              on d.id = p.department_id
            join public.semesters s
              on s.id = :semester_id
             and s.program_id = p.id
            join public.sections sec
              on sec.id = :section_id
             and sec.semester_id = s.id
            where ay.id = :academic_year_id
              and i.id = :institution_id
              and d.institution_id = :institution_id
            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "academic_year_id": academic_year_id,
            "program_id": program_id,
            "semester_id": semester_id,
            "section_id": section_id,
        },
    )

    return result.mappings().first()


def _get_existing_history(
    db: Session,
    student_id: UUID,
    academic_year_id: UUID,
    semester_id: UUID,
):
    result = db.execute(
        text(
            """
            select id
            from public.student_academic_history
            where student_id = :student_id
              and academic_year_id = :academic_year_id
              and semester_id = :semester_id
            limit 1
            """
        ),
        {
            "student_id": student_id,
            "academic_year_id": academic_year_id,
            "semester_id": semester_id,
        },
    )

    return result.first()


def _get_previous_result(
    db: Session,
    student_id: UUID,
    program_id: UUID,
    current_semester_number: int,
):
    if current_semester_number <= 1:
        return None

    result = db.execute(
        text(
            """
            select
                ssr.result_status,
                ssr.progression_status,
                ssr.academic_year_id,
                ssr.semester_id
            from public.student_semester_results ssr
            join public.semesters s
              on s.id = ssr.semester_id
            join public.academic_years ay
              on ay.id = ssr.academic_year_id
            where ssr.student_id = :student_id
              and ssr.program_id = :program_id
              and s.semester_number = :previous_semester_number
            order by ay.end_date desc
            limit 1
            """
        ),
        {
            "student_id": student_id,
            "program_id": program_id,
            "previous_semester_number": current_semester_number - 1,
        },
    )

    return result.mappings().first()


def list_academic_history(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
):
    student = _get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )

    if student is None:
        raise AcademicHistoryError("Student not found")

    result = db.execute(
        text(
            f"""
            select {ACADEMIC_HISTORY_COLUMNS}
            from public.student_academic_history
            where student_id = :student_id
            order by start_date nulls last, id
            """
        ),
        {
            "student_id": student_id,
        },
    )

    return result.mappings().all()


def create_academic_history(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
    payload: AcademicHistoryCreate,
):
    _validate_history_status(payload.status)

    student = _get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )

    if student is None:
        raise AcademicHistoryError("Student not found")

    context = _get_academic_context(
        db=db,
        institution_id=institution_id,
        academic_year_id=payload.academic_year_id,
        program_id=payload.program_id,
        semester_id=payload.semester_id,
        section_id=payload.section_id,
    )

    if context is None:
        raise AcademicHistoryError(
            "Academic year, program, semester and section "
            "do not belong to the same institution/program context"
        )

    existing = _get_existing_history(
        db=db,
        student_id=student_id,
        academic_year_id=payload.academic_year_id,
        semester_id=payload.semester_id,
    )

    if existing is not None:
        raise AcademicHistoryError(
            "Student already has academic history for this semester"
        )

    semester_number = context["semester_number"]

    previous_result = _get_previous_result(
        db=db,
        student_id=student_id,
        program_id=payload.program_id,
        current_semester_number=semester_number,
    )

    if semester_number > 1:
        if previous_result is None:
            raise AcademicHistoryError(
                "Student cannot progress because the previous "
                "semester result is not available"
            )

        if previous_result["result_status"] != "pass":
            raise AcademicHistoryError(
                "Student cannot progress because the previous "
                "semester result is not PASS"
            )

    result = db.execute(
        text(
            f"""
            insert into public.student_academic_history (
                student_id,
                academic_year_id,
                program_id,
                semester_id,
                section_id,
                roll_number,
                status,
                start_date
            )
            values (
                :student_id,
                :academic_year_id,
                :program_id,
                :semester_id,
                :section_id,
                :roll_number,
                :status,
                current_date
            )
            returning {ACADEMIC_HISTORY_COLUMNS}
            """
        ),
        {
            "student_id": student_id,
            "academic_year_id": payload.academic_year_id,
            "program_id": payload.program_id,
            "semester_id": payload.semester_id,
            "section_id": payload.section_id,
            "roll_number": _normalize_optional(
                payload.roll_number
            ),
            "status": payload.status,
        },
    )

    history = result.mappings().first()

    db.commit()

    return history


def list_semester_results(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
):
    student = _get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )

    if student is None:
        raise SemesterResultError("Student not found")

    result = db.execute(
        text(
            f"""
            select {SEMESTER_RESULT_COLUMNS}
            from public.student_semester_results
            where student_id = :student_id
            order by result_date nulls last, id
            """
        ),
        {
            "student_id": student_id,
        },
    )

    return result.mappings().all()


def create_semester_result(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
    payload: SemesterResultCreate,
):
    _validate_result_status(payload.result_status)

    student = _get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
    )

    if student is None:
        raise SemesterResultError("Student not found")

    context = _get_academic_context(
        db=db,
        institution_id=institution_id,
        academic_year_id=payload.academic_year_id,
        program_id=payload.program_id,
        semester_id=payload.semester_id,
        section_id=(
            _get_section_for_history(
                db=db,
                student_id=student_id,
                academic_year_id=payload.academic_year_id,
                semester_id=payload.semester_id,
            )
        ),
    )

    if context is None:
        raise SemesterResultError(
            "Student does not have valid academic history "
            "for this semester"
        )

    history = db.execute(
        text(
            """
            select id
            from public.student_academic_history
            where student_id = :student_id
              and academic_year_id = :academic_year_id
              and program_id = :program_id
              and semester_id = :semester_id
            limit 1
            """
        ),
        {
            "student_id": student_id,
            "academic_year_id": payload.academic_year_id,
            "program_id": payload.program_id,
            "semester_id": payload.semester_id,
        },
    ).first()

    if history is None:
        raise SemesterResultError(
            "Student does not have academic history for this semester"
        )

    existing = db.execute(
        text(
            """
            select id
            from public.student_semester_results
            where student_id = :student_id
              and academic_year_id = :academic_year_id
              and semester_id = :semester_id
            limit 1
            """
        ),
        {
            "student_id": student_id,
            "academic_year_id": payload.academic_year_id,
            "semester_id": payload.semester_id,
        },
    ).first()

    if existing is not None:
        raise SemesterResultError(
            "Semester result already exists"
        )

    progression_status = (
        "eligible"
        if payload.result_status == "pass"
        else "blocked"
    )

    result = db.execute(
        text(
            f"""
            insert into public.student_semester_results (
                student_id,
                academic_year_id,
                program_id,
                semester_id,
                result_status,
                progression_status,
                result_date,
                remarks
            )
            values (
                :student_id,
                :academic_year_id,
                :program_id,
                :semester_id,
                :result_status,
                :progression_status,
                :result_date,
                :remarks
            )
            returning {SEMESTER_RESULT_COLUMNS}
            """
        ),
        {
            "student_id": student_id,
            "academic_year_id": payload.academic_year_id,
            "program_id": payload.program_id,
            "semester_id": payload.semester_id,
            "result_status": payload.result_status,
            "progression_status": progression_status,
            "result_date": payload.result_date,
            "remarks": _normalize_optional(payload.remarks),
        },
    )

    semester_result = result.mappings().first()

    db.execute(
        text(
            """
            update public.student_academic_history
            set status = :history_status,
                end_date = case
                    when :history_status in ('completed', 'promoted')
                    then current_date
                    else end_date
                end
            where student_id = :student_id
              and academic_year_id = :academic_year_id
              and program_id = :program_id
              and semester_id = :semester_id
            """
        ),
        {
            "history_status": (
                "promoted"
                if payload.result_status == "pass"
                else "detained"
                if payload.result_status == "fail"
                else "active"
            ),
            "student_id": student_id,
            "academic_year_id": payload.academic_year_id,
            "program_id": payload.program_id,
            "semester_id": payload.semester_id,
        },
    )

    db.commit()

    return semester_result


def _get_section_for_history(
    db: Session,
    student_id: UUID,
    academic_year_id: UUID,
    semester_id: UUID,
):
    result = db.execute(
        text(
            """
            select section_id
            from public.student_academic_history
            where student_id = :student_id
              and academic_year_id = :academic_year_id
              and semester_id = :semester_id
            limit 1
            """
        ),
        {
            "student_id": student_id,
            "academic_year_id": academic_year_id,
            "semester_id": semester_id,
        },
    )

    row = result.first()

    if row is None:
        return None

    return row[0]