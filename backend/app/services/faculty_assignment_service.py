from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class FacultyAssignmentConflictError(Exception):
    """Raised when a faculty assignment conflicts with an existing assignment."""


class FacultyAssignmentNotFoundError(Exception):
    """Raised when a faculty assignment does not exist."""


ASSIGNMENT_COLUMNS = """
    fa.id,
    fa.faculty_id,
    fa.subject_id,
    fa.section_id,
    fa.academic_year_id,
    fa.assignment_type,
    fa.is_primary,
    fa.is_active
"""


def _get_assignment(
    db: Session,
    institution_id: UUID,
    assignment_id: UUID,
):
    row = db.execute(
        text(
            f"""
            select
                {ASSIGNMENT_COLUMNS}
            from public.faculty_assignments fa
            join public.faculty f
              on f.id = fa.faculty_id
            where fa.id = :assignment_id
              and f.institution_id = :institution_id
            limit 1
            """
        ),
        {
            "assignment_id": assignment_id,
            "institution_id": institution_id,
        },
    ).mappings().first()

    if row is None:
        raise FacultyAssignmentNotFoundError(
            "Faculty assignment not found"
        )

    return row


def _get_assignment_context(
    db: Session,
    institution_id: UUID,
    faculty_id: UUID,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
):
    row = db.execute(
        text(
            """
            select
                f.id as faculty_id,
                f.institution_id as faculty_institution_id,
                f.is_active as faculty_is_active,

                s.id as subject_id,
                s.semester_id as subject_semester_id,
                s.has_lab as subject_has_lab,
                s.is_active as subject_is_active,

                sec.id as section_id,
                sec.semester_id as section_semester_id,
                sec.is_active as section_is_active,

                ay.id as academic_year_id,
                ay.institution_id as academic_year_institution_id,

                d.institution_id as subject_institution_id,
                d.institution_id as section_institution_id

            from public.faculty f

            join public.subjects s
              on s.id = :subject_id

            join public.semesters subject_sem
              on subject_sem.id = s.semester_id

            join public.programs subject_program
              on subject_program.id = subject_sem.program_id

            join public.departments d
              on d.id = subject_program.department_id

            join public.sections sec
              on sec.id = :section_id

            join public.academic_years ay
              on ay.id = :academic_year_id

            where f.id = :faculty_id
              and f.institution_id = :institution_id

            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "faculty_id": faculty_id,
            "subject_id": subject_id,
            "section_id": section_id,
            "academic_year_id": academic_year_id,
        },
    ).mappings().first()

    return row


def _validate_academic_context(
    db: Session,
    institution_id: UUID,
    faculty_id: UUID,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
    assignment_type: str,
):
    context = _get_assignment_context(
        db=db,
        institution_id=institution_id,
        faculty_id=faculty_id,
        subject_id=subject_id,
        section_id=section_id,
        academic_year_id=academic_year_id,
    )

    if context is None:
        raise ValueError(
            "Faculty, subject, section, or academic year is not "
            "valid for the authenticated institution"
        )

    if context["faculty_institution_id"] != institution_id:
        raise ValueError(
            "Faculty does not belong to the authenticated institution"
        )

    if context["subject_institution_id"] != institution_id:
        raise ValueError(
            "Subject does not belong to the authenticated institution"
        )

    if context["section_institution_id"] != institution_id:
        raise ValueError(
            "Section does not belong to the authenticated institution"
        )

    if context["academic_year_institution_id"] != institution_id:
        raise ValueError(
            "Academic year does not belong to the authenticated institution"
        )

    if not context["faculty_is_active"]:
        raise ValueError(
            "Inactive faculty cannot be newly assigned"
        )

    if not context["subject_is_active"]:
        raise ValueError(
            "Inactive subject cannot receive a new faculty assignment"
        )

    if not context["section_is_active"]:
        raise ValueError(
            "Inactive section cannot receive a new faculty assignment"
        )

    if context["subject_semester_id"] != context["section_semester_id"]:
        raise ValueError(
            "Subject and section must belong to the same semester"
        )

    if assignment_type in {"LAB_PRIMARY", "LAB_SECONDARY"}:
        if not context["subject_has_lab"]:
            raise ValueError(
                "Lab faculty can only be assigned to a lab-enabled subject"
            )

    return context


def _check_duplicate_faculty_role(
    db: Session,
    faculty_id: UUID,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
    assignment_type: str,
    exclude_assignment_id: UUID | None = None,
):
    query = """
        select fa.id
        from public.faculty_assignments fa
        where fa.faculty_id = :faculty_id
          and fa.subject_id = :subject_id
          and fa.section_id = :section_id
          and fa.academic_year_id = :academic_year_id
          and fa.assignment_type = :assignment_type
          and fa.is_active = true
    """

    params = {
        "faculty_id": faculty_id,
        "subject_id": subject_id,
        "section_id": section_id,
        "academic_year_id": academic_year_id,
        "assignment_type": assignment_type,
    }

    if exclude_assignment_id is not None:
        query += """
          and fa.id <> :exclude_assignment_id
        """
        params["exclude_assignment_id"] = exclude_assignment_id

    query += " limit 1"

    row = db.execute(
        text(query),
        params,
    ).first()

    return row is not None


def _check_secondary_not_primary(
    db: Session,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
    faculty_id: UUID,
    exclude_assignment_id: UUID | None = None,
):
    query = """
        select fa.id
        from public.faculty_assignments fa
        where fa.subject_id = :subject_id
          and fa.section_id = :section_id
          and fa.academic_year_id = :academic_year_id
          and fa.faculty_id = :faculty_id
          and fa.assignment_type = 'LAB_PRIMARY'
          and fa.is_active = true
    """

    params = {
        "subject_id": subject_id,
        "section_id": section_id,
        "academic_year_id": academic_year_id,
        "faculty_id": faculty_id,
    }

    if exclude_assignment_id is not None:
        query += """
          and fa.id <> :exclude_assignment_id
        """
        params["exclude_assignment_id"] = exclude_assignment_id

    query += " limit 1"

    return db.execute(
        text(query),
        params,
    ).first() is not None


def _check_one_active_role(
    db: Session,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
    assignment_type: str,
    exclude_assignment_id: UUID | None = None,
):
    query = """
        select fa.id
        from public.faculty_assignments fa
        where fa.subject_id = :subject_id
          and fa.section_id = :section_id
          and fa.academic_year_id = :academic_year_id
          and fa.assignment_type = :assignment_type
          and fa.is_active = true
    """

    params = {
        "subject_id": subject_id,
        "section_id": section_id,
        "academic_year_id": academic_year_id,
        "assignment_type": assignment_type,
    }

    if exclude_assignment_id is not None:
        query += """
          and fa.id <> :exclude_assignment_id
        """
        params["exclude_assignment_id"] = exclude_assignment_id

    query += " limit 1"

    return db.execute(
        text(query),
        params,
    ).first() is not None


def list_assignments(
    db: Session,
    institution_id: UUID,
):
    rows = db.execute(
        text(
            f"""
            select
                {ASSIGNMENT_COLUMNS}
            from public.faculty_assignments fa
            join public.faculty f
              on f.id = fa.faculty_id
            join public.subjects s
              on s.id = fa.subject_id
            join public.sections sec
              on sec.id = fa.section_id
            join public.academic_years ay
              on ay.id = fa.academic_year_id
            where f.institution_id = :institution_id
            order by fa.created_at desc
            """
        ),
        {"institution_id": institution_id},
    ).mappings().all()

    return rows


def get_assignment(
    db: Session,
    institution_id: UUID,
    assignment_id: UUID,
):
    return _get_assignment(
        db=db,
        institution_id=institution_id,
        assignment_id=assignment_id,
    )


def create_assignment(
    db: Session,
    institution_id: UUID,
    faculty_id: UUID,
    subject_id: UUID,
    section_id: UUID,
    academic_year_id: UUID,
    assignment_type: str,
):
    if assignment_type not in {
        "SUBJECT",
        "LAB_PRIMARY",
        "LAB_SECONDARY",
    }:
        raise ValueError("Invalid assignment type")

    _validate_academic_context(
        db=db,
        institution_id=institution_id,
        faculty_id=faculty_id,
        subject_id=subject_id,
        section_id=section_id,
        academic_year_id=academic_year_id,
        assignment_type=assignment_type,
    )

    if _check_duplicate_faculty_role(
        db,
        faculty_id,
        subject_id,
        section_id,
        academic_year_id,
        assignment_type,
    ):
        raise FacultyAssignmentConflictError(
            "Faculty is already assigned with this role"
        )

    if assignment_type in {"SUBJECT", "LAB_PRIMARY"}:
        if _check_one_active_role(
            db,
            subject_id,
            section_id,
            academic_year_id,
            assignment_type,
        ):
            raise FacultyAssignmentConflictError(
                f"An active {assignment_type} assignment already exists"
            )

    if assignment_type == "LAB_SECONDARY":
        if _check_secondary_not_primary(
            db,
            subject_id,
            section_id,
            academic_year_id,
            faculty_id,
        ):
            raise FacultyAssignmentConflictError(
                "A Primary Lab Faculty cannot also be Secondary Faculty"
            )

    is_primary = assignment_type in {
        "SUBJECT",
        "LAB_PRIMARY",
    }

    try:
        row = db.execute(
            text(
                f"""
                insert into public.faculty_assignments (
                    faculty_id,
                    subject_id,
                    section_id,
                    academic_year_id,
                    assignment_type,
                    is_primary,
                    is_active
                )
                values (
                    :faculty_id,
                    :subject_id,
                    :section_id,
                    :academic_year_id,
                    :assignment_type,
                    :is_primary,
                    true
                )
                returning {ASSIGNMENT_COLUMNS}
                """
            ),
            {
                "faculty_id": faculty_id,
                "subject_id": subject_id,
                "section_id": section_id,
                "academic_year_id": academic_year_id,
                "assignment_type": assignment_type,
                "is_primary": is_primary,
            },
        ).mappings().one()

        db.commit()
        return row

    except IntegrityError as exc:
        db.rollback()
        raise FacultyAssignmentConflictError(
            "Faculty assignment conflicts with an existing assignment"
        ) from exc


def update_assignment(
    db: Session,
    institution_id: UUID,
    assignment_id: UUID,
    faculty_id: UUID | None = None,
    assignment_type: str | None = None,
    is_active: bool | None = None,
):
    existing = _get_assignment(
        db=db,
        institution_id=institution_id,
        assignment_id=assignment_id,
    )

    target_faculty_id = (
        faculty_id
        if faculty_id is not None
        else existing["faculty_id"]
    )

    target_assignment_type = (
        assignment_type
        if assignment_type is not None
        else existing["assignment_type"]
    )

    target_is_active = (
        is_active
        if is_active is not None
        else existing["is_active"]
    )

    if target_assignment_type not in {
        "SUBJECT",
        "LAB_PRIMARY",
        "LAB_SECONDARY",
    }:
        raise ValueError("Invalid assignment type")

    if target_is_active:
        _validate_academic_context(
            db=db,
            institution_id=institution_id,
            faculty_id=target_faculty_id,
            subject_id=existing["subject_id"],
            section_id=existing["section_id"],
            academic_year_id=existing["academic_year_id"],
            assignment_type=target_assignment_type,
        )

        if _check_duplicate_faculty_role(
            db,
            target_faculty_id,
            existing["subject_id"],
            existing["section_id"],
            existing["academic_year_id"],
            target_assignment_type,
            exclude_assignment_id=assignment_id,
        ):
            raise FacultyAssignmentConflictError(
                "Faculty is already assigned with this role"
            )

        if target_assignment_type in {"SUBJECT", "LAB_PRIMARY"}:
            if _check_one_active_role(
                db,
                existing["subject_id"],
                existing["section_id"],
                existing["academic_year_id"],
                target_assignment_type,
                exclude_assignment_id=assignment_id,
            ):
                raise FacultyAssignmentConflictError(
                    f"An active {target_assignment_type} assignment already exists"
                )

        if target_assignment_type == "LAB_SECONDARY":
            if _check_secondary_not_primary(
                db,
                existing["subject_id"],
                existing["section_id"],
                existing["academic_year_id"],
                target_faculty_id,
                exclude_assignment_id=assignment_id,
            ):
                raise FacultyAssignmentConflictError(
                    "A Primary Lab Faculty cannot also be Secondary Faculty"
                )

    is_primary = target_assignment_type in {
        "SUBJECT",
        "LAB_PRIMARY",
    }

    try:
        row = db.execute(
            text(
                f"""
                update public.faculty_assignments
                set
                    faculty_id = :faculty_id,
                    assignment_type = :assignment_type,
                    is_primary = :is_primary,
                    is_active = :is_active,
                    updated_at = now()
                where id = :assignment_id
                returning {ASSIGNMENT_COLUMNS}
                """
            ),
            {
                "faculty_id": target_faculty_id,
                "assignment_type": target_assignment_type,
                "is_primary": is_primary,
                "is_active": target_is_active,
                "assignment_id": assignment_id,
            },
        ).mappings().one()

        db.commit()
        return row

    except IntegrityError as exc:
        db.rollback()
        raise FacultyAssignmentConflictError(
            "Faculty assignment conflicts with an existing assignment"
        ) from exc


def deactivate_assignment(
    db: Session,
    institution_id: UUID,
    assignment_id: UUID,
):
    return update_assignment(
        db=db,
        institution_id=institution_id,
        assignment_id=assignment_id,
        is_active=False,
    )