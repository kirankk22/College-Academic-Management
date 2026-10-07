from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.faculty import FacultyCreate, FacultyUpdate


class FacultyConflictError(Exception):
    """Raised when a faculty operation conflicts with an existing record."""


FACULTY_COLUMNS = """
    id,
    institution_id,
    user_profile_id,
    employee_id,
    name,
    email,
    phone,
    designation,
    department_id,
    is_active
"""


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _faculty_row(result):
    return result.mappings().first()


def _get_faculty(
    db: Session,
    institution_id: UUID,
    faculty_id: UUID,
):
    result = db.execute(
        text(
            f"""
            select {FACULTY_COLUMNS}
            from public.faculty
            where id = :faculty_id
              and institution_id = :institution_id
            limit 1
            """
        ),
        {
            "faculty_id": faculty_id,
            "institution_id": institution_id,
        },
    )

    return _faculty_row(result)


def _validate_department(
    db: Session,
    institution_id: UUID,
    department_id: UUID | None,
) -> None:
    if department_id is None:
        return

    result = db.execute(
        text(
            """
            select id
            from public.departments
            where id = :department_id
              and institution_id = :institution_id
            limit 1
            """
        ),
        {
            "department_id": department_id,
            "institution_id": institution_id,
        },
    )

    if result.first() is None:
        raise ValueError(
            "Department does not belong to the authenticated institution"
        )


def _validate_user_profile(
    db: Session,
    institution_id: UUID,
    user_profile_id: UUID | None,
) -> None:
    if user_profile_id is None:
        return

    result = db.execute(
        text(
            """
            select id
            from public.user_profiles
            where id = :user_profile_id
              and institution_id = :institution_id
            limit 1
            """
        ),
        {
            "user_profile_id": user_profile_id,
            "institution_id": institution_id,
        },
    )

    if result.first() is None:
        raise ValueError(
            "User profile does not belong to the authenticated institution"
        )


def list_faculty(
    db: Session,
    institution_id: UUID,
):
    result = db.execute(
        text(
            f"""
            select {FACULTY_COLUMNS}
            from public.faculty
            where institution_id = :institution_id
            order by name, employee_id
            """
        ),
        {
            "institution_id": institution_id,
        },
    )

    return result.mappings().all()


def get_faculty(
    db: Session,
    institution_id: UUID,
    faculty_id: UUID,
):
    return _get_faculty(
        db=db,
        institution_id=institution_id,
        faculty_id=faculty_id,
    )


def create_faculty(
    db: Session,
    institution_id: UUID,
    payload: FacultyCreate,
):
    employee_id = payload.employee_id.strip()
    name = payload.name.strip()

    if not employee_id:
        raise ValueError("Employee ID cannot be empty")

    if not name:
        raise ValueError("Faculty name cannot be empty")

    department_id = payload.department_id
    user_profile_id = payload.user_profile_id

    _validate_department(
        db=db,
        institution_id=institution_id,
        department_id=department_id,
    )

    _validate_user_profile(
        db=db,
        institution_id=institution_id,
        user_profile_id=user_profile_id,
    )

    existing = db.execute(
        text(
            """
            select id
            from public.faculty
            where institution_id = :institution_id
              and employee_id = :employee_id
            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "employee_id": employee_id,
        },
    ).first()

    if existing:
        raise FacultyConflictError(
            "A faculty member with this employee ID already exists"
        )

    result = db.execute(
        text(
            f"""
            insert into public.faculty (
                institution_id,
                user_profile_id,
                employee_id,
                name,
                email,
                phone,
                designation,
                department_id,
                is_active
            )
            values (
                :institution_id,
                :user_profile_id,
                :employee_id,
                :name,
                :email,
                :phone,
                :designation,
                :department_id,
                :is_active
            )
            returning {FACULTY_COLUMNS}
            """
        ),
        {
            "institution_id": institution_id,
            "user_profile_id": user_profile_id,
            "employee_id": employee_id,
            "name": name,
            "email": _normalize_optional(payload.email),
            "phone": _normalize_optional(payload.phone),
            "designation": _normalize_optional(payload.designation),
            "department_id": department_id,
            "is_active": payload.is_active,
        },
    )

    faculty = _faculty_row(result)

    db.commit()

    return faculty


def update_faculty(
    db: Session,
    institution_id: UUID,
    faculty_id: UUID,
    payload: FacultyUpdate,
):
    existing = _get_faculty(
        db=db,
        institution_id=institution_id,
        faculty_id=faculty_id,
    )

    if existing is None:
        return None

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        return existing

    normalized = {}

    for key, value in updates.items():
        if isinstance(value, str):
            normalized[key] = value.strip() or None
        else:
            normalized[key] = value

    if "employee_id" in normalized:
        employee_id = normalized["employee_id"]

        if employee_id is None:
            raise ValueError("Employee ID cannot be empty")

        duplicate = db.execute(
            text(
                """
                select id
                from public.faculty
                where institution_id = :institution_id
                  and employee_id = :employee_id
                  and id <> :faculty_id
                limit 1
                """
            ),
            {
                "institution_id": institution_id,
                "employee_id": employee_id,
                "faculty_id": faculty_id,
            },
        ).first()

        if duplicate:
            raise FacultyConflictError(
                "A faculty member with this employee ID already exists"
            )

    if "name" in normalized and normalized["name"] is None:
        raise ValueError("Faculty name cannot be empty")

    if "department_id" in normalized:
        _validate_department(
            db=db,
            institution_id=institution_id,
            department_id=normalized["department_id"],
        )

    if "user_profile_id" in normalized:
        _validate_user_profile(
            db=db,
            institution_id=institution_id,
            user_profile_id=normalized["user_profile_id"],
        )

    assignments = []

    for column in normalized:
        assignments.append(f"{column} = :{column}")

    params = {
        "faculty_id": faculty_id,
        "institution_id": institution_id,
        **normalized,
    }

    result = db.execute(
        text(
            f"""
            update public.faculty
            set {", ".join(assignments)},
                updated_at = now()
            where id = :faculty_id
              and institution_id = :institution_id
            returning {FACULTY_COLUMNS}
            """
        ),
        params,
    )

    faculty = _faculty_row(result)

    if faculty is None:
        db.rollback()
        return None

    db.commit()

    return faculty