from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


class AttendanceStudentContextError(Exception):
    """Raised when attendance student context validation fails."""


def _validate_academic_context(
    db: Session,
    institution_id: UUID,
    academic_year_id: UUID,
    program_id: UUID,
    academic_period_id: UUID,
    section_id: UUID,
):
    result = db.execute(
        text(
            """
            select
                ap.id as academic_period_id,
                ap.academic_year_id,
                ap.program_id,
                ap.period_type,
                ap.period_number,
                ap.semester_id,
                sec.id as section_id,
                sec.name as section_name
            from public.academic_periods ap
            join public.programs p
                on p.id = ap.program_id
            join public.departments d
                on d.id = p.department_id
            join public.academic_years ay
                on ay.id = ap.academic_year_id
            join public.sections sec
                on sec.id = :section_id
               and sec.academic_period_id = ap.id
            where ap.id = :academic_period_id
              and ap.academic_year_id = :academic_year_id
              and ap.program_id = :program_id
              and ay.institution_id = :institution_id
              and d.institution_id = :institution_id
              and ap.is_active = true
              and sec.is_active = true
            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "academic_year_id": academic_year_id,
            "program_id": program_id,
            "academic_period_id": academic_period_id,
            "section_id": section_id,
        },
    )

    return result.mappings().first()


def list_attendance_students(
    db: Session,
    institution_id: UUID,
    academic_year_id: UUID,
    program_id: UUID,
    academic_period_id: UUID,
    section_id: UUID,
):
    context = _validate_academic_context(
        db=db,
        institution_id=institution_id,
        academic_year_id=academic_year_id,
        program_id=program_id,
        academic_period_id=academic_period_id,
        section_id=section_id,
    )

    if context is None:
        raise AttendanceStudentContextError(
            "Academic year, program, academic period and section "
            "do not belong to the same institution context"
        )

    result = db.execute(
        text(
            """
            select
                s.id as student_id,
                s.permanent_student_id,
                concat_ws(
                    ' ',
                    s.first_name,
                    s.middle_name,
                    s.last_name
                ) as student_name,
                sah.roll_number,
                s.status as student_status,
                sah.id as academic_history_id
            from public.student_academic_history sah
            join public.students s
                on s.id = sah.student_id
               and s.institution_id = :institution_id
            where sah.academic_year_id = :academic_year_id
              and sah.program_id = :program_id
              and sah.section_id = :section_id
              and sah.status = 'active'
            order by
                sah.roll_number nulls last,
                s.first_name,
                s.last_name,
                s.permanent_student_id
            """
        ),
        {
            "institution_id": institution_id,
            "academic_year_id": academic_year_id,
            "program_id": program_id,
            "section_id": section_id,
        },
    )

    return result.mappings().all()