from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.student import StudentCreate, StudentUpdate


STUDENT_COLUMNS = """
    id,
    institution_id,
    permanent_student_id,
    admission_number,
    first_name,
    middle_name,
    last_name,
    date_of_birth,
    gender,
    email,
    phone,
    admission_date,
    status
"""


def _normalize_optional(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.strip()

    return value or None


def _student_row(result):
    return result.mappings().first()


def list_students(
    db: Session,
    institution_id: UUID,
):
    result = db.execute(
        text(
            f"""
            select {STUDENT_COLUMNS}
            from public.students
            where institution_id = :institution_id
            order by first_name, last_name, permanent_student_id
            """
        ),
        {
            "institution_id": institution_id,
        },
    )

    return result.mappings().all()


def get_student(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
):
    result = db.execute(
        text(
            f"""
            select {STUDENT_COLUMNS}
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

    return _student_row(result)


def create_student(
    db: Session,
    institution_id: UUID,
    payload: StudentCreate,
):
    permanent_student_id = payload.permanent_student_id.strip()

    if not permanent_student_id:
        raise ValueError("Permanent student ID cannot be empty")

    admission_number = _normalize_optional(payload.admission_number)

    existing = db.execute(
        text(
            """
            select id
            from public.students
            where institution_id = :institution_id
              and permanent_student_id = :permanent_student_id
            limit 1
            """
        ),
        {
            "institution_id": institution_id,
            "permanent_student_id": permanent_student_id,
        },
    ).first()

    if existing:
        raise ValueError(
            "A student with this permanent student ID already exists"
        )

    if admission_number is not None:
        existing_admission = db.execute(
            text(
                """
                select id
                from public.students
                where institution_id = :institution_id
                  and admission_number = :admission_number
                limit 1
                """
            ),
            {
                "institution_id": institution_id,
                "admission_number": admission_number,
            },
        ).first()

        if existing_admission:
            raise ValueError(
                "A student with this admission number already exists"
            )

    result = db.execute(
        text(
            f"""
            insert into public.students (
                institution_id,
                permanent_student_id,
                admission_number,
                first_name,
                middle_name,
                last_name,
                date_of_birth,
                gender,
                email,
                phone,
                admission_date,
                status
            )
            values (
                :institution_id,
                :permanent_student_id,
                :admission_number,
                :first_name,
                :middle_name,
                :last_name,
                :date_of_birth,
                :gender,
                :email,
                :phone,
                :admission_date,
                :status
            )
            returning {STUDENT_COLUMNS}
            """
        ),
        {
            "institution_id": institution_id,
            "permanent_student_id": permanent_student_id,
            "admission_number": admission_number,
            "first_name": payload.first_name.strip(),
            "middle_name": _normalize_optional(payload.middle_name),
            "last_name": _normalize_optional(payload.last_name),
            "date_of_birth": payload.date_of_birth,
            "gender": _normalize_optional(payload.gender),
            "email": _normalize_optional(payload.email),
            "phone": _normalize_optional(payload.phone),
            "admission_date": payload.admission_date,
            "status": payload.status,
        },
    )

    student = _student_row(result)

    db.commit()

    return student


def update_student(
    db: Session,
    institution_id: UUID,
    student_id: UUID,
    payload: StudentUpdate,
):
    existing = get_student(
        db=db,
        institution_id=institution_id,
        student_id=student_id,
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

    if "first_name" in normalized and normalized["first_name"] is None:
        raise ValueError("First name cannot be empty")

    if "status" in normalized:
        allowed_statuses = {
            "active",
            "inactive",
            "graduated",
            "withdrawn",
            "transferred",
        }

        if normalized["status"] not in allowed_statuses:
            raise ValueError("Invalid student status")

    if "admission_number" in normalized:
        admission_number = normalized["admission_number"]

        if admission_number is not None:
            duplicate = db.execute(
                text(
                    """
                    select id
                    from public.students
                    where institution_id = :institution_id
                      and admission_number = :admission_number
                      and id <> :student_id
                    limit 1
                    """
                ),
                {
                    "institution_id": institution_id,
                    "admission_number": admission_number,
                    "student_id": student_id,
                },
            ).first()

            if duplicate:
                raise ValueError(
                    "A student with this admission number already exists"
                )

    assignments = []

    for column in normalized:
        assignments.append(f"{column} = :{column}")

    params = {
        "student_id": student_id,
        "institution_id": institution_id,
        **normalized,
    }

    result = db.execute(
        text(
            f"""
            update public.students
            set {", ".join(assignments)}
            where id = :student_id
              and institution_id = :institution_id
            returning {STUDENT_COLUMNS}
            """
        ),
        params,
    )

    student = _student_row(result)

    if student is None:
        db.rollback()
        return None

    db.commit()

    return student