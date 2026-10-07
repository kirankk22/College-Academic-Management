-- ============================================================
-- Phase 2C.3A: Academic Structure Foundation
--
-- Supports:
--   1. Semester-based programs
--   2. Annual programs
--
-- Existing semesters remain curriculum definitions.
-- academic_periods represent the program's offering
-- within a specific academic year.
--
-- Examples:
--
--   MCA / 2026-27
--       Semester 1 -> ODD
--       Semester 2 -> EVEN
--       Semester 3 -> ODD
--       Semester 4 -> EVEN
--
--   Annual Program / 2026-27
--       Year 1
--       Year 2
--       Year 3
--
-- This migration is backward-compatible with the existing
-- Phase 2 student/history implementation.
-- ============================================================


begin;


-- ============================================================
-- 1. Program academic structure
-- ============================================================

alter table public.programs
    add column if not exists academic_structure_type text;

update public.programs
set academic_structure_type = 'SEMESTER'
where academic_structure_type is null;

alter table public.programs
    alter column academic_structure_type set default 'SEMESTER';

alter table public.programs
    alter column academic_structure_type set not null;

alter table public.programs
    drop constraint if exists programs_academic_structure_type_check;

alter table public.programs
    add constraint programs_academic_structure_type_check
    check (
        academic_structure_type in (
            'SEMESTER',
            'ANNUAL'
        )
    );


-- Generic duration count.
--
-- Existing duration_semesters remains temporarily for
-- backward compatibility with Phase 2 code.
--
-- For SEMESTER programs:
--     duration_units = number of semesters
--
-- For ANNUAL programs:
--     duration_units = number of academic years

alter table public.programs
    add column if not exists duration_units integer;

update public.programs
set duration_units = duration_semesters
where duration_units is null;

alter table public.programs
    alter column duration_units set default 4;

alter table public.programs
    alter column duration_units set not null;

alter table public.programs
    drop constraint if exists programs_duration_units_check;

alter table public.programs
    add constraint programs_duration_units_check
    check (duration_units > 0);


comment on column public.programs.academic_structure_type is
    'Program academic structure: SEMESTER or ANNUAL.';

comment on column public.programs.duration_units is
    'Number of academic periods for the program. For SEMESTER this means semesters; for ANNUAL this means academic years.';

comment on column public.programs.duration_semesters is
    'Legacy field retained temporarily for backward compatibility. New code should use duration_units.';


-- ============================================================
-- 2. Academic periods
-- ============================================================

create table if not exists public.academic_periods (
    id uuid primary key default gen_random_uuid(),

    academic_year_id uuid not null
        references public.academic_years(id)
        on delete cascade,

    program_id uuid not null
        references public.programs(id)
        on delete cascade,

    period_type text not null,

    period_number integer not null,

    semester_id uuid,

    period_name text not null,

    semester_cycle text,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    constraint academic_periods_period_type_check
        check (
            period_type in (
                'SEMESTER',
                'ANNUAL_YEAR'
            )
        ),

    constraint academic_periods_period_number_check
        check (
            period_number > 0
        ),

    constraint academic_periods_semester_cycle_check
        check (
            semester_cycle is null
            or semester_cycle in (
                'ODD',
                'EVEN'
            )
        ),

    constraint academic_periods_semester_definition_check
        check (
            (
                period_type = 'SEMESTER'
                and semester_id is not null
                and semester_cycle is not null
            )
            or
            (
                period_type = 'ANNUAL_YEAR'
                and semester_id is null
                and semester_cycle is null
            )
        ),

    unique (
        academic_year_id,
        program_id,
        period_number
    )
);


-- ============================================================
-- 3. Composite uniqueness for semester/program relationship
--
-- This allows academic_periods to guarantee that the
-- referenced semester belongs to the same program.
-- ============================================================

create unique index if not exists
    semesters_id_program_id_unique
on public.semesters (
    id,
    program_id
);


alter table public.academic_periods
    drop constraint if exists academic_periods_semester_program_fkey;

alter table public.academic_periods
    add constraint academic_periods_semester_program_fkey
    foreign key (
        semester_id,
        program_id
    )
    references public.semesters (
        id,
        program_id
    )
    on delete restrict;


-- ============================================================
-- 4. Academic period indexes
-- ============================================================

create index if not exists
    idx_academic_periods_academic_year
on public.academic_periods (
    academic_year_id
);

create index if not exists
    idx_academic_periods_program
on public.academic_periods (
    program_id
);

create index if not exists
    idx_academic_periods_period_type
on public.academic_periods (
    period_type
);

create index if not exists
    idx_academic_periods_program_year
on public.academic_periods (
    program_id,
    academic_year_id
);


-- ============================================================
-- 5. Link sections to academic-year-specific periods
-- ============================================================

alter table public.sections
    add column if not exists academic_period_id uuid;


alter table public.sections
    drop constraint if exists sections_academic_period_id_fkey;

alter table public.sections
    add constraint sections_academic_period_id_fkey
    foreign key (
        academic_period_id
    )
    references public.academic_periods(id)
    on delete restrict;


create index if not exists
    idx_sections_academic_period
on public.sections (
    academic_period_id
);


-- ============================================================
-- 6. Create academic periods for existing current academic
--    year semester structures.
--
-- Existing demo programs are semester-based.
-- We only backfill periods where the current academic year
-- and curriculum semester belong to the same institution.
-- ============================================================

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
select
    ay.id,
    p.id,
    'SEMESTER',
    s.semester_number,
    s.id,
    s.name,
    case
        when mod(s.semester_number, 2) = 1 then 'ODD'
        else 'EVEN'
    end,
    true
from public.academic_years ay
join public.departments d
    on d.institution_id = ay.institution_id
join public.programs p
    on p.department_id = d.id
join public.semesters s
    on s.program_id = p.id
where ay.is_current = true
  and p.academic_structure_type = 'SEMESTER'
on conflict (
    academic_year_id,
    program_id,
    period_number
)
do update
set
    semester_id = excluded.semester_id,
    period_name = excluded.period_name,
    semester_cycle = excluded.semester_cycle,
    is_active = true,
    updated_at = now();


-- ============================================================
-- 7. Backfill existing sections
--
-- Existing sections are linked through:
--
--     section -> semester -> program -> institution
--
-- and now receive the corresponding current academic period.
-- ============================================================

update public.sections sec
set academic_period_id = ap.id,
    updated_at = now()
from public.semesters s
join public.programs p
    on p.id = s.program_id
join public.departments d
    on d.id = p.department_id
join public.academic_years ay
    on ay.institution_id = d.institution_id
   and ay.is_current = true
join public.academic_periods ap
    on ap.academic_year_id = ay.id
   and ap.program_id = p.id
   and ap.semester_id = s.id
where sec.semester_id = s.id
  and sec.academic_period_id is null;


-- ============================================================
-- 8. Academic-period consistency index
-- ============================================================

create index if not exists
    idx_sections_period_name
on public.sections (
    academic_period_id,
    name
);


-- ============================================================
-- 9. RLS
-- ============================================================

alter table public.academic_periods enable row level security;


drop policy if exists
    academic_periods_select_policy
on public.academic_periods;


create policy
    academic_periods_select_policy
on public.academic_periods
for select
using (
    exists (
        select 1
        from public.academic_years ay
        join public.institutions i
            on i.id = ay.institution_id
        where ay.id = academic_periods.academic_year_id
          and i.id = public.current_user_institution_id()
    )
);


-- ============================================================
-- 10. Documentation
-- ============================================================

comment on table public.academic_periods is
    'Academic-year-specific program periods supporting semester-based and annual programs.';

comment on column public.academic_periods.period_type is
    'SEMESTER for semester-based programs or ANNUAL_YEAR for annual programs.';

comment on column public.academic_periods.period_number is
    'Sequential period number within the program academic year.';

comment on column public.academic_periods.semester_id is
    'Curriculum semester definition. NULL for annual program periods.';

comment on column public.academic_periods.semester_cycle is
    'ODD or EVEN for semester periods. NULL for annual periods.';


commit;