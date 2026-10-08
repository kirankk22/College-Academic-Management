from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session


def list_academic_years(
    db: Session,
    institution_id: UUID,
) -> list[dict]:
    query = text(
        """
        select
            ay.id,
            ay.institution_id,
            ay.name,
            ay.start_date,
            ay.end_date,
            ay.is_current
        from public.academic_years ay
        where ay.institution_id = :institution_id
          and ay.is_current = true
        order by ay.start_date desc, ay.name desc
        """
    )

    rows = db.execute(
        query,
        {"institution_id": institution_id},
    ).mappings().all()

    return [dict(row) for row in rows]


def list_programs(
    db: Session,
    institution_id: UUID,
    academic_year_id: UUID | None = None,
) -> list[dict]:
    query = text(
        """
        select distinct
            p.id,
            p.department_id,
            p.name,
            p.code,
            p.academic_structure_type,
            p.duration_units,
            p.is_active
        from public.programs p
        join public.departments d
            on d.id = p.department_id
        where d.institution_id = :institution_id
          and p.is_active = true
        """
    )

    params: dict[str, UUID] = {
        "institution_id": institution_id,
    }

    if academic_year_id is not None:
        query = text(
            """
            select distinct
                p.id,
                p.department_id,
                p.name,
                p.code,
                p.academic_structure_type,
                p.duration_units,
                p.is_active
            from public.programs p
            join public.departments d
                on d.id = p.department_id
            join public.academic_periods ap
                on ap.program_id = p.id
            where d.institution_id = :institution_id
              and ap.academic_year_id = :academic_year_id
              and p.is_active = true
              and ap.is_active = true
            order by p.name, p.code
            """
        )

        params["academic_year_id"] = academic_year_id

    else:
        query = text(
            """
            select
                p.id,
                p.department_id,
                p.name,
                p.code,
                p.academic_structure_type,
                p.duration_units,
                p.is_active
            from public.programs p
            join public.departments d
                on d.id = p.department_id
            where d.institution_id = :institution_id
              and p.is_active = true
            order by p.name, p.code
            """
        )

    rows = db.execute(
        query,
        params,
    ).mappings().all()

    return [dict(row) for row in rows]


def list_sections(
    db: Session,
    institution_id: UUID,
    academic_period_id: UUID,
) -> list[dict]:
    query = text(
        """
        select
            sec.id,
            sec.academic_period_id,
            sec.semester_id,
            sec.name,
            sec.is_active
        from public.sections sec
        join public.academic_periods ap
            on ap.id = sec.academic_period_id
        join public.programs p
            on p.id = ap.program_id
        join public.departments d
            on d.id = p.department_id
        where sec.academic_period_id = :academic_period_id
          and d.institution_id = :institution_id
          and sec.is_active = true
          and ap.is_active = true
        order by sec.name
        """
    )

    rows = db.execute(
        query,
        {
            "institution_id": institution_id,
            "academic_period_id": academic_period_id,
        },
    ).mappings().all()

    return [dict(row) for row in rows]


def list_subjects(
    db: Session,
    institution_id: UUID,
    academic_period_id: UUID,
) -> list[dict]:
    query = text(
        """
        select
            sub.id,
            sub.semester_id,
            sub.code,
            sub.name,
            sub.credits,
            sub.is_active,
            sub.has_lab
        from public.subjects sub
        join public.semesters sem
            on sem.id = sub.semester_id
        join public.academic_periods ap
            on ap.semester_id = sem.id
           and ap.program_id = sem.program_id
        join public.programs p
            on p.id = ap.program_id
        join public.departments d
            on d.id = p.department_id
        where ap.id = :academic_period_id
          and d.institution_id = :institution_id
          and ap.is_active = true
          and sub.is_active = true
        order by sub.code, sub.name
        """
    )

    rows = db.execute(
        query,
        {
            "institution_id": institution_id,
            "academic_period_id": academic_period_id,
        },
    ).mappings().all()

    return [dict(row) for row in rows]