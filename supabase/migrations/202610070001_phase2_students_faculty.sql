-- ============================================================
-- Phase 2: Students, Academic History & Faculty Assignments
-- Project: College Academic Management
--
-- Scope:
--   Students
--   Parents / Guardians
--   Student-parent relationships
--   Student academic history
--   Student semester results and progression
--   Subjects
--   Faculty
--   Faculty assignments
--
-- IMPORTANT BUSINESS RULE:
--
--   PASS    -> ELIGIBLE for progression
--   FAIL    -> BLOCKED from progression
--   PENDING -> BLOCKED until result is decided
--
-- The FastAPI business layer will enforce the progression
-- rule when creating the next academic placement.
--
-- This migration intentionally does NOT create:
--   attendance
--   Google Sheets integration
--   eligibility calculations
--   attendance fines
--   payments
--   receipts
--   notifications
--   reports
-- ============================================================


-- ============================================================
-- 1. Students
-- ============================================================

create table if not exists public.students (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    -- Permanent identity of the student.
    -- This value must remain unchanged throughout the
    -- student's academic journey.
    permanent_student_id text not null,

    -- Institution-specific admission number.
    admission_number text,

    first_name text not null,

    middle_name text,

    last_name text,

    date_of_birth date,

    gender text,

    email text,

    phone text,

    admission_date date,

    status text not null default 'active',

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (
        institution_id,
        permanent_student_id
    ),

    unique (
        institution_id,
        admission_number
    ),

    check (
        status in (
            'active',
            'inactive',
            'graduated',
            'withdrawn',
            'transferred'
        )
    )
);


-- ============================================================
-- 2. Parents / Guardians
-- ============================================================

create table if not exists public.parents (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    name text not null,

    email text,

    phone text,

    relationship text not null,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now()
);


-- ============================================================
-- 3. Student <-> Parent relationships
-- ============================================================

create table if not exists public.student_parent_links (
    id uuid primary key default gen_random_uuid(),

    student_id uuid not null
        references public.students(id)
        on delete cascade,

    parent_id uuid not null
        references public.parents(id)
        on delete cascade,

    is_primary boolean not null default false,

    created_at timestamptz not null default now(),

    unique (
        student_id,
        parent_id
    )
);


-- ============================================================
-- 4. Student Academic History
--
-- A student has ONE permanent identity.
--
-- This table records the student's academic placement
-- during each semester.
--
-- Example:
--
--   Student CAM-2026-00001
--       -> 2026-27
--       -> MCA
--       -> Semester 1
--       -> Section A
--
-- Later:
--
--       -> 2026-27
--       -> MCA
--       -> Semester 2
--       -> Section A
--
-- The permanent_student_id does NOT change.
-- ============================================================

create table if not exists public.student_academic_history (
    id uuid primary key default gen_random_uuid(),

    student_id uuid not null
        references public.students(id)
        on delete cascade,

    academic_year_id uuid not null
        references public.academic_years(id)
        on delete restrict,

    program_id uuid not null
        references public.programs(id)
        on delete restrict,

    semester_id uuid not null
        references public.semesters(id)
        on delete restrict,

    section_id uuid not null
        references public.sections(id)
        on delete restrict,

    roll_number text,

    status text not null default 'active',

    start_date date,

    end_date date,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    check (
        status in (
            'active',
            'completed',
            'promoted',
            'detained',
            'withdrawn',
            'transferred'
        )
    ),

    check (
        end_date is null
        or start_date is null
        or end_date >= start_date
    ),

    unique (
        student_id,
        academic_year_id,
        semester_id
    )
);


-- ============================================================
-- 5. Student Semester Results & Progression
--
-- This table records the result of a student for a semester.
--
-- Current MVP progression rule:
--
--   PASS
--       -> ELIGIBLE
--
--   FAIL
--       -> BLOCKED
--
--   PENDING
--       -> BLOCKED
--
-- IMPORTANT:
--
-- The FastAPI business layer will prevent creation of the
-- next semester academic-history record when the previous
-- semester is not eligible for progression.
--
-- This table is intentionally separate from academic history.
-- Academic history tells us WHERE the student was enrolled.
-- This table tells us the RESULT and PROGRESSION decision.
-- ============================================================

create table if not exists public.student_semester_results (
    id uuid primary key default gen_random_uuid(),

    student_id uuid not null
        references public.students(id)
        on delete cascade,

    academic_year_id uuid not null
        references public.academic_years(id)
        on delete restrict,

    program_id uuid not null
        references public.programs(id)
        on delete restrict,

    semester_id uuid not null
        references public.semesters(id)
        on delete restrict,

    result_status text not null default 'pending',

    progression_status text not null default 'blocked',

    result_date date,

    remarks text,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    check (
        result_status in (
            'pending',
            'pass',
            'fail'
        )
    ),

    check (
        progression_status in (
            'eligible',
            'blocked',
            'conditional'
        )
    ),

    unique (
        student_id,
        academic_year_id,
        semester_id
    )
);


-- ============================================================
-- 6. Subjects
--
-- Subjects belong to a semester.
--
-- Semester already belongs to a Program.
-- ============================================================

create table if not exists public.subjects (
    id uuid primary key default gen_random_uuid(),

    semester_id uuid not null
        references public.semesters(id)
        on delete restrict,

    code text not null,

    name text not null,

    credits numeric(4,1),

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (
        semester_id,
        code
    )
);


-- ============================================================
-- 7. Faculty
--
-- A faculty member belongs to an institution.
--
-- user_profile_id is optional because a faculty record may
-- exist before the person receives a login account.
-- ============================================================

create table if not exists public.faculty (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    user_profile_id uuid
        references public.user_profiles(id)
        on delete set null,

    employee_id text not null,

    name text not null,

    email text,

    phone text,

    designation text,

    department_id uuid
        references public.departments(id)
        on delete set null,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (
        institution_id,
        employee_id
    )
);


-- ============================================================
-- 8. Faculty Assignments
--
-- Example:
--
--   Faculty:
--       Professor A
--
--   Academic Year:
--       2026-27
--
--   Subject:
--       Advanced Java
--
--   Semester:
--       Semester 2
--
--   Section:
--       Section A
--
-- This table records the teaching assignment.
-- ============================================================

create table if not exists public.faculty_assignments (
    id uuid primary key default gen_random_uuid(),

    faculty_id uuid not null
        references public.faculty(id)
        on delete cascade,

    subject_id uuid not null
        references public.subjects(id)
        on delete restrict,

    section_id uuid not null
        references public.sections(id)
        on delete restrict,

    academic_year_id uuid not null
        references public.academic_years(id)
        on delete restrict,

    is_primary boolean not null default false,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (
        faculty_id,
        subject_id,
        section_id,
        academic_year_id
    )
);


-- ============================================================
-- 9. Indexes
-- ============================================================

create index if not exists idx_students_institution_id
    on public.students(institution_id);

create index if not exists idx_students_permanent_student_id
    on public.students(permanent_student_id);

create index if not exists idx_students_admission_number
    on public.students(admission_number);

create index if not exists idx_students_status
    on public.students(status);


create index if not exists idx_parents_institution_id
    on public.parents(institution_id);


create index if not exists idx_student_parent_links_student_id
    on public.student_parent_links(student_id);

create index if not exists idx_student_parent_links_parent_id
    on public.student_parent_links(parent_id);


create index if not exists idx_student_academic_history_student_id
    on public.student_academic_history(student_id);

create index if not exists idx_student_academic_history_academic_year_id
    on public.student_academic_history(academic_year_id);

create index if not exists idx_student_academic_history_program_id
    on public.student_academic_history(program_id);

create index if not exists idx_student_academic_history_semester_id
    on public.student_academic_history(semester_id);

create index if not exists idx_student_academic_history_section_id
    on public.student_academic_history(section_id);


create index if not exists idx_student_semester_results_student_id
    on public.student_semester_results(student_id);

create index if not exists idx_student_semester_results_academic_year_id
    on public.student_semester_results(academic_year_id);

create index if not exists idx_student_semester_results_program_id
    on public.student_semester_results(program_id);

create index if not exists idx_student_semester_results_semester_id
    on public.student_semester_results(semester_id);

create index if not exists idx_student_semester_results_result_status
    on public.student_semester_results(result_status);

create index if not exists idx_student_semester_results_progression_status
    on public.student_semester_results(progression_status);


create index if not exists idx_subjects_semester_id
    on public.subjects(semester_id);


create index if not exists idx_faculty_institution_id
    on public.faculty(institution_id);

create index if not exists idx_faculty_user_profile_id
    on public.faculty(user_profile_id);

create index if not exists idx_faculty_department_id
    on public.faculty(department_id);


create index if not exists idx_faculty_assignments_faculty_id
    on public.faculty_assignments(faculty_id);

create index if not exists idx_faculty_assignments_subject_id
    on public.faculty_assignments(subject_id);

create index if not exists idx_faculty_assignments_section_id
    on public.faculty_assignments(section_id);

create index if not exists idx_faculty_assignments_academic_year_id
    on public.faculty_assignments(academic_year_id);


-- ============================================================
-- 10. Row Level Security
-- ============================================================

alter table public.students
    enable row level security;

alter table public.parents
    enable row level security;

alter table public.student_parent_links
    enable row level security;

alter table public.student_academic_history
    enable row level security;

alter table public.student_semester_results
    enable row level security;

alter table public.subjects
    enable row level security;

alter table public.faculty
    enable row level security;

alter table public.faculty_assignments
    enable row level security;


-- ============================================================
-- 11. Students RLS
-- ============================================================

drop policy if exists students_select_policy
    on public.students;

create policy students_select_policy
on public.students
for select
to authenticated
using (
    institution_id = public.current_user_institution_id()
);


-- ============================================================
-- 12. Parents RLS
-- ============================================================

drop policy if exists parents_select_policy
    on public.parents;

create policy parents_select_policy
on public.parents
for select
to authenticated
using (
    institution_id = public.current_user_institution_id()
);


-- ============================================================
-- 13. Student-parent links RLS
-- ============================================================

drop policy if exists student_parent_links_select_policy
    on public.student_parent_links;

create policy student_parent_links_select_policy
on public.student_parent_links
for select
to authenticated
using (
    exists (
        select 1
        from public.students s
        where s.id = student_parent_links.student_id
          and s.institution_id =
              public.current_user_institution_id()
    )
);


-- ============================================================
-- 14. Student academic history RLS
-- ============================================================

drop policy if exists student_academic_history_select_policy
    on public.student_academic_history;

create policy student_academic_history_select_policy
on public.student_academic_history
for select
to authenticated
using (
    exists (
        select 1
        from public.students s
        where s.id = student_academic_history.student_id
          and s.institution_id =
              public.current_user_institution_id()
    )
);


-- ============================================================
-- 15. Student semester results RLS
-- ============================================================

drop policy if exists student_semester_results_select_policy
    on public.student_semester_results;

create policy student_semester_results_select_policy
on public.student_semester_results
for select
to authenticated
using (
    exists (
        select 1
        from public.students s
        where s.id = student_semester_results.student_id
          and s.institution_id =
              public.current_user_institution_id()
    )
);


-- ============================================================
-- 16. Subjects RLS
-- ============================================================

drop policy if exists subjects_select_policy
    on public.subjects;

create policy subjects_select_policy
on public.subjects
for select
to authenticated
using (
    exists (
        select 1
        from public.semesters sem
        join public.programs p
            on p.id = sem.program_id
        join public.departments d
            on d.id = p.department_id
        where sem.id = subjects.semester_id
          and d.institution_id =
              public.current_user_institution_id()
    )
);


-- ============================================================
-- 17. Faculty RLS
-- ============================================================

drop policy if exists faculty_select_policy
    on public.faculty;

create policy faculty_select_policy
on public.faculty
for select
to authenticated
using (
    institution_id = public.current_user_institution_id()
);


-- ============================================================
-- 18. Faculty assignments RLS
-- ============================================================

drop policy if exists faculty_assignments_select_policy
    on public.faculty_assignments;

create policy faculty_assignments_select_policy
on public.faculty_assignments
for select
to authenticated
using (
    exists (
        select 1
        from public.faculty f
        where f.id = faculty_assignments.faculty_id
          and f.institution_id =
              public.current_user_institution_id()
    )
);


-- ============================================================
-- 19. End of Phase 2 migration
-- ============================================================
