from uuid import UUID


from sqlalchemy import text


from sqlalchemy.orm import Session


from app.models.academic_period import (


    AcademicPeriodCreate,


    AcademicPeriodUpdate,


)


ACADEMIC_PERIOD_COLUMNS = """


    ap.id,


    ap.academic_year_id,


    ap.program_id,


    ap.period_type,


    ap.period_number,


    ap.semester_id,


    ap.period_name,


    ap.semester_cycle,


    ap.is_active,


    ap.created_at,


    ap.updated_at


"""


class AcademicPeriodError(Exception):


    """Raised when academic-period validation fails."""


def _normalize_required(value: str, field_name: str) -> str:


    value = value.strip()


    if not value:


        raise AcademicPeriodError(


            f"{field_name} cannot be empty"


        )


    return value


def _validate_period_type(period_type: str) -> None:


    if period_type not in {


        "SEMESTER",


        "ANNUAL_YEAR",


    }:


        raise AcademicPeriodError(


            "Invalid academic period type"


        )


def _validate_semester_cycle(


    period_type: str,


    semester_id: UUID | None,


    semester_cycle: str | None,


) -> None:


    if period_type == "SEMESTER":


        if semester_id is None:


            raise AcademicPeriodError(


                "semester_id is required for a semester period"


            )


        if semester_cycle not in {"ODD", "EVEN"}:


            raise AcademicPeriodError(


                "semester_cycle must be ODD or EVEN for a semester period"


            )


        return


    if semester_id is not None:


        raise AcademicPeriodError(


            "semester_id must be null for an annual period"


        )


    if semester_cycle is not None:


        raise AcademicPeriodError(


            "semester_cycle must be null for an annual period"


        )


def _validate_institution_context(


    db: Session,


    institution_id: UUID,


    academic_year_id: UUID,


    program_id: UUID,


) -> str:


    result = db.execute(


        text(


            """


            select


                ay.id as academic_year_id,


                ay.institution_id as academic_year_institution_id,


                p.id as program_id,


                d.institution_id as program_institution_id,


                p.academic_structure_type as academic_structure_type


            from public.academic_years ay


            join public.programs p


              on p.id = :program_id


            join public.departments d


              on d.id = p.department_id


            where ay.id = :academic_year_id


              and ay.institution_id = :institution_id


              and d.institution_id = :institution_id


            limit 1


            """


        ),


        {


            "institution_id": institution_id,


            "academic_year_id": academic_year_id,


            "program_id": program_id,


        },


    ).mappings().first()


    if result is None:


        raise AcademicPeriodError(


            "Academic year and program do not belong to the authorized institution"


        )


    return result["academic_structure_type"]


def _validate_semester_context(


    db: Session,


    program_id: UUID,


    semester_id: UUID,


    period_number: int,


) -> None:


    result = db.execute(


        text(


            """


            select


                id,


                program_id,


                semester_number


            from public.semesters


            where id = :semester_id


              and program_id = :program_id


            limit 1


            """


        ),


        {


            "semester_id": semester_id,


            "program_id": program_id,


        },


    ).mappings().first()


    if result is None:


        raise AcademicPeriodError(


            "Semester does not belong to the selected program"


        )


    if result["semester_number"] != period_number:


        raise AcademicPeriodError(


            "Period number must match the semester number"


        )


def _get_existing_period(


    db: Session,


    academic_year_id: UUID,


    program_id: UUID,


    period_number: int,


):


    result = db.execute(


        text(


            """


            select id


            from public.academic_periods


            where academic_year_id = :academic_year_id


              and program_id = :program_id


              and period_number = :period_number


            limit 1


            """


        ),


        {


            "academic_year_id": academic_year_id,


            "program_id": program_id,


            "period_number": period_number,


        },


    )


    return result.first()


def _get_period(


    db: Session,


    institution_id: UUID,


    academic_period_id: UUID,


):


    result = db.execute(


        text(


            f"""


            select {ACADEMIC_PERIOD_COLUMNS}


            from public.academic_periods ap


            join public.academic_years ay


              on ay.id = ap.academic_year_id


            join public.programs p


              on p.id = ap.program_id


            join public.departments d


              on d.id = p.department_id


            where ap.id = :academic_period_id


              and ay.institution_id = :institution_id


              and d.institution_id = :institution_id


            limit 1


            """


        ),


        {


            "academic_period_id": academic_period_id,


            "institution_id": institution_id,


        },


    )


    return result.mappings().first()


def list_academic_periods(


    db: Session,


    institution_id: UUID,


    academic_year_id: UUID | None = None,


    program_id: UUID | None = None,


):


    query = f"""


        select {ACADEMIC_PERIOD_COLUMNS}


        from public.academic_periods ap


        join public.academic_years ay


          on ay.id = ap.academic_year_id


        join public.programs p


          on p.id = ap.program_id


        join public.departments d


          on d.id = p.department_id


        where ay.institution_id = :institution_id


          and d.institution_id = :institution_id


    """


    params = {


        "institution_id": institution_id,


    }


    if academic_year_id is not None:


        query += """


            and ap.academic_year_id = :academic_year_id


        """


        params["academic_year_id"] = academic_year_id


    if program_id is not None:


        query += """


            and ap.program_id = :program_id


        """


        params["program_id"] = program_id


    query += """


        order by


            ap.program_id,


            ap.period_number


    """


    result = db.execute(


        text(query),


        params,


    )


    return result.mappings().all()


def get_academic_period(


    db: Session,


    institution_id: UUID,


    academic_period_id: UUID,


):


    return _get_period(


        db=db,


        institution_id=institution_id,


        academic_period_id=academic_period_id,


    )


def create_academic_period(


    db: Session,


    institution_id: UUID,


    payload: AcademicPeriodCreate,


):


    period_type = payload.period_type.strip().upper()


    period_name = _normalize_required(


        payload.period_name,


        "period_name",


    )


    _validate_period_type(period_type)


    _validate_semester_cycle(


        period_type=period_type,


        semester_id=payload.semester_id,


        semester_cycle=payload.semester_cycle,


    )


    academic_structure_type = _validate_institution_context(


        db=db,


        institution_id=institution_id,


        academic_year_id=payload.academic_year_id,


        program_id=payload.program_id,


    )


    if (


        academic_structure_type == "SEMESTER"


        and period_type != "SEMESTER"


    ):


        raise AcademicPeriodError(


            "SEMESTER programs require SEMESTER academic periods"


        )


    if (


        academic_structure_type == "ANNUAL"


        and period_type != "ANNUAL_YEAR"


    ):


        raise AcademicPeriodError(


            "ANNUAL programs require ANNUAL_YEAR academic periods"


        )


    if period_type == "SEMESTER":


        _validate_semester_context(


            db=db,


            program_id=payload.program_id,


            semester_id=payload.semester_id,


            period_number=payload.period_number,


        )


    existing = _get_existing_period(


        db=db,


        academic_year_id=payload.academic_year_id,


        program_id=payload.program_id,


        period_number=payload.period_number,


    )


    if existing is not None:


        raise AcademicPeriodError(


            "An academic period with this program, academic year and period number already exists"


        )


    result = db.execute(


        text(


            f"""


            insert into public.academic_periods (


                academic_year_id,


                program_id,


                period_type,


                period_number,


                semester_id,


                period_name,


                semester_cycle,


                is_active


            )


            values (


                :academic_year_id,


                :program_id,


                :period_type,


                :period_number,


                :semester_id,


                :period_name,


                :semester_cycle,


                :is_active


            )


            returning {ACADEMIC_PERIOD_COLUMNS}


            """


        ),


        {


            "academic_year_id": payload.academic_year_id,


            "program_id": payload.program_id,


            "period_type": period_type,


            "period_number": payload.period_number,


            "semester_id": payload.semester_id,


            "period_name": period_name,


            "semester_cycle": payload.semester_cycle,


            "is_active": payload.is_active,


        },


    )


    period = result.mappings().first()


    db.commit()


    return period


def update_academic_period(


    db: Session,


    institution_id: UUID,


    academic_period_id: UUID,


    payload: AcademicPeriodUpdate,


):


    existing = _get_period(


        db=db,


        institution_id=institution_id,


        academic_period_id=academic_period_id,


    )


    if existing is None:


        return None


    updates = payload.model_dump(exclude_unset=True)


    if not updates:


        return existing


    normalized = {}


    if "period_name" in updates:


        normalized["period_name"] = _normalize_required(


            updates["period_name"],


            "period_name",


        )


    if "is_active" in updates:


        normalized["is_active"] = updates["is_active"]


    assignments = [


        f"{column} = :{column}"


        for column in normalized


    ]


    params = {


        "academic_period_id": academic_period_id,


        **normalized,


    }


    result = db.execute(


        text(


            f"""


            update public.academic_periods ap


            set {", ".join(assignments)},


                updated_at = now()


            where ap.id = :academic_period_id


              and exists (


                  select 1


                  from public.academic_years ay


                  join public.programs p


                    on p.id = ap.program_id


                  join public.departments d


                    on d.id = p.department_id


                  where ay.id = ap.academic_year_id


                    and ay.institution_id = :institution_id


                    and d.institution_id = :institution_id


              )


            returning {ACADEMIC_PERIOD_COLUMNS}


            """


        ),


        {


            **params,


            "institution_id": institution_id,


        },


    )


    period = result.mappings().first()


    if period is None:


        db.rollback()


        return None


    db.commit()


    return period


def deactivate_academic_period(


    db: Session,


    institution_id: UUID,


    academic_period_id: UUID,


):


    existing = _get_period(


        db=db,


        institution_id=institution_id,


        academic_period_id=academic_period_id,


    )


    if existing is None:


        return None


    result = db.execute(


        text(


            """


            update public.academic_periods


            set is_active = false,


                updated_at = now()


            where id = :academic_period_id


            returning

                id,

                academic_year_id,

                program_id,

                period_type,

                period_number,

                semester_id,

                period_name,

                semester_cycle,

                is_active,

                created_at,

                updated_at


            """


        ),


        {


            "academic_period_id": academic_period_id,


        },


    )


    period = result.mappings().first()


    db.commit()


    return period