-- ============================================================
-- Phase 1: Multi-Tenant Academic Foundation
-- Project: College Academic Management
--
-- Scope:
--   Organization
--     -> Institution
--       -> Department
--         -> Program
--           -> Academic Year
--             -> Semester
--               -> Section
--
-- This migration establishes the reusable academic foundation
-- for the demo MVP.
--
-- It intentionally does NOT create:
--   students
--   attendance
--   Google Sheets integration
--   eligibility
--   fines
--   payments
--   receipts
--   notifications
--   reports
-- ============================================================


-- ============================================================
-- 1. Extensions
-- ============================================================

create extension if not exists pgcrypto;


-- ============================================================
-- 2. Roles
-- ============================================================

do $$
begin
    create type public.user_role as enum (
        'platform_admin',
        'organization_admin',
        'principal',
        'hod',
        'faculty',
        'accounts',
        'student',
        'parent'
    );
exception
    when duplicate_object then null;
end
$$;


-- ============================================================
-- 3. Organizations
-- ============================================================

create table if not exists public.organizations (
    id uuid primary key default gen_random_uuid(),

    name text not null,

    code text not null unique,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now()
);


-- ============================================================
-- 4. Institutions / Campuses
-- ============================================================

create table if not exists public.institutions (
    id uuid primary key default gen_random_uuid(),

    organization_id uuid not null
        references public.organizations(id)
        on delete cascade,

    name text not null,

    code text not null,

    city text,

    state text,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (organization_id, code)
);


-- ============================================================
-- 5. Departments
-- ============================================================

create table if not exists public.departments (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete cascade,

    name text not null,

    code text not null,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (institution_id, code)
);


-- ============================================================
-- 6. Programs
-- ============================================================

create table if not exists public.programs (
    id uuid primary key default gen_random_uuid(),

    department_id uuid not null
        references public.departments(id)
        on delete cascade,

    name text not null,

    code text not null,

    duration_semesters integer not null default 4,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    check (duration_semesters > 0),

    unique (department_id, code)
);


-- ============================================================
-- 7. Academic Years
-- ============================================================

create table if not exists public.academic_years (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete cascade,

    name text not null,

    start_date date not null,

    end_date date not null,

    is_current boolean not null default false,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    check (end_date > start_date),

    unique (institution_id, name)
);


-- ============================================================
-- 8. Semesters
-- ============================================================

create table if not exists public.semesters (
    id uuid primary key default gen_random_uuid(),

    program_id uuid not null
        references public.programs(id)
        on delete cascade,

    semester_number integer not null,

    name text not null,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    check (semester_number > 0),

    unique (program_id, semester_number)
);


-- ============================================================
-- 9. Sections
-- ============================================================

create table if not exists public.sections (
    id uuid primary key default gen_random_uuid(),

    semester_id uuid not null
        references public.semesters(id)
        on delete cascade,

    name text not null,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    unique (semester_id, name)
);


-- ============================================================
-- 10. User Profiles
--
-- One profile corresponds to one Supabase Auth user.
--
-- Scope columns allow us to establish organization,
-- institution and department boundaries.
-- ============================================================

create table if not exists public.user_profiles (
    id uuid primary key
        references auth.users(id)
        on delete cascade,

    display_name text,

    email text,

    role public.user_role not null,

    organization_id uuid
        references public.organizations(id)
        on delete set null,

    institution_id uuid
        references public.institutions(id)
        on delete set null,

    department_id uuid
        references public.departments(id)
        on delete set null,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now()
);


-- ============================================================
-- 11. Indexes
-- ============================================================

create index if not exists idx_institutions_organization_id
    on public.institutions(organization_id);

create index if not exists idx_departments_institution_id
    on public.departments(institution_id);

create index if not exists idx_programs_department_id
    on public.programs(department_id);

create index if not exists idx_academic_years_institution_id
    on public.academic_years(institution_id);

create index if not exists idx_semesters_program_id
    on public.semesters(program_id);

create index if not exists idx_sections_semester_id
    on public.sections(semester_id);

create index if not exists idx_user_profiles_organization_id
    on public.user_profiles(organization_id);

create index if not exists idx_user_profiles_institution_id
    on public.user_profiles(institution_id);

create index if not exists idx_user_profiles_department_id
    on public.user_profiles(department_id);

create index if not exists idx_user_profiles_role
    on public.user_profiles(role);


-- ============================================================
-- 12. Row Level Security
-- ============================================================

alter table public.organizations enable row level security;

alter table public.institutions enable row level security;

alter table public.departments enable row level security;

alter table public.programs enable row level security;

alter table public.academic_years enable row level security;

alter table public.semesters enable row level security;

alter table public.sections enable row level security;

alter table public.user_profiles enable row level security;


-- ============================================================
-- 13. Helper function:
--     Current authenticated user's organization
-- ============================================================

create or replace function public.current_user_organization_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select organization_id
    from public.user_profiles
    where id = auth.uid()
      and is_active = true
    limit 1;
$$;


-- ============================================================
-- 14. Helper function:
--     Current authenticated user's institution
-- ============================================================

create or replace function public.current_user_institution_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select institution_id
    from public.user_profiles
    where id = auth.uid()
      and is_active = true
    limit 1;
$$;


-- ============================================================
-- 15. Helper function:
--     Current authenticated user's department
-- ============================================================

create or replace function public.current_user_department_id()
returns uuid
language sql
stable
security definer
set search_path = public
as $$
    select department_id
    from public.user_profiles
    where id = auth.uid()
      and is_active = true
    limit 1;
$$;


-- ============================================================
-- 16. Organization RLS policies
-- ============================================================

drop policy if exists organizations_select_policy
    on public.organizations;

create policy organizations_select_policy
on public.organizations
for select
to authenticated
using (
    id = public.current_user_organization_id()
);


-- ============================================================
-- 17. Institution RLS policies
-- ============================================================

drop policy if exists institutions_select_policy
    on public.institutions;

create policy institutions_select_policy
on public.institutions
for select
to authenticated
using (
    organization_id = public.current_user_organization_id()
);


-- ============================================================
-- 18. Department RLS policies
-- ============================================================

drop policy if exists departments_select_policy
    on public.departments;

create policy departments_select_policy
on public.departments
for select
to authenticated
using (
    institution_id = public.current_user_institution_id()
);


-- ============================================================
-- 19. Program RLS policies
-- ============================================================

drop policy if exists programs_select_policy
    on public.programs;

create policy programs_select_policy
on public.programs
for select
to authenticated
using (
    department_id = public.current_user_department_id()
);


-- ============================================================
-- 20. Academic Year RLS policies
-- ============================================================

drop policy if exists academic_years_select_policy
    on public.academic_years;

create policy academic_years_select_policy
on public.academic_years
for select
to authenticated
using (
    institution_id = public.current_user_institution_id()
);


-- ============================================================
-- 21. Semester RLS policies
-- ============================================================

drop policy if exists semesters_select_policy
    on public.semesters;

create policy semesters_select_policy
on public.semesters
for select
to authenticated
using (
    exists (
        select 1
        from public.programs p
        join public.departments d
            on d.id = p.department_id
        where p.id = semesters.program_id
          and d.institution_id = public.current_user_institution_id()
    )
);


-- ============================================================
-- 22. Section RLS policies
-- ============================================================

drop policy if exists sections_select_policy
    on public.sections;

create policy sections_select_policy
on public.sections
for select
to authenticated
using (
    exists (
        select 1
        from public.semesters s
        join public.programs p
            on p.id = s.program_id
        join public.departments d
            on d.id = p.department_id
        where s.id = sections.semester_id
          and d.institution_id = public.current_user_institution_id()
    )
);


-- ============================================================
-- 23. User profile RLS policy
-- ============================================================

drop policy if exists user_profiles_select_policy
    on public.user_profiles;

create policy user_profiles_select_policy
on public.user_profiles
for select
to authenticated
using (
    id = auth.uid()
    or organization_id = public.current_user_organization_id()
);


-- ============================================================
-- 24. Demo Organization
-- ============================================================

insert into public.organizations (
    name,
    code
)
values (
    'Demo Education Group',
    'DEMO-GROUP'
)
on conflict (code) do update
set
    name = excluded.name,
    updated_at = now();


-- ============================================================
-- 25. Demo Institutions
-- ============================================================

insert into public.institutions (
    organization_id,
    name,
    code,
    city,
    state
)
select
    id,
    'Bangalore Demo College',
    'BLR-DEMO',
    'Bangalore',
    'Karnataka'
from public.organizations
where code = 'DEMO-GROUP'
on conflict (organization_id, code)
do update
set
    name = excluded.name,
    city = excluded.city,
    state = excluded.state,
    updated_at = now();


insert into public.institutions (
    organization_id,
    name,
    code,
    city,
    state
)
select
    id,
    'Mysore Demo College',
    'MYS-DEMO',
    'Mysore',
    'Karnataka'
from public.organizations
where code = 'DEMO-GROUP'
on conflict (organization_id, code)
do update
set
    name = excluded.name,
    city = excluded.city,
    state = excluded.state,
    updated_at = now();


-- ============================================================
-- 26. Demo Departments
-- ============================================================

insert into public.departments (
    institution_id,
    name,
    code
)
select
    id,
    'Master of Computer Applications',
    'MCA'
from public.institutions
where code = 'BLR-DEMO'
on conflict (institution_id, code)
do update
set
    name = excluded.name,
    updated_at = now();


insert into public.departments (
    institution_id,
    name,
    code
)
select
    id,
    'Master of Business Administration',
    'MBA'
from public.institutions
where code = 'BLR-DEMO'
on conflict (institution_id, code)
do update
set
    name = excluded.name,
    updated_at = now();


insert into public.departments (
    institution_id,
    name,
    code
)
select
    id,
    'Master of Computer Applications',
    'MCA'
from public.institutions
where code = 'MYS-DEMO'
on conflict (institution_id, code)
do update
set
    name = excluded.name,
    updated_at = now();


insert into public.departments (
    institution_id,
    name,
    code
)
select
    id,
    'Master of Business Administration',
    'MBA'
from public.institutions
where code = 'MYS-DEMO'
on conflict (institution_id, code)
do update
set
    name = excluded.name,
    updated_at = now();


-- ============================================================
-- 27. Demo Programs
-- ============================================================

insert into public.programs (
    department_id,
    name,
    code,
    duration_semesters
)
select
    id,
    'MCA',
    'MCA',
    4
from public.departments
where code = 'MCA'
on conflict (department_id, code)
do update
set
    name = excluded.name,
    duration_semesters = excluded.duration_semesters,
    updated_at = now();


insert into public.programs (
    department_id,
    name,
    code,
    duration_semesters
)
select
    id,
    'MBA',
    'MBA',
    4
from public.departments
where code = 'MBA'
on conflict (department_id, code)
do update
set
    name = excluded.name,
    duration_semesters = excluded.duration_semesters,
    updated_at = now();


-- ============================================================
-- 28. Demo Academic Year
-- ============================================================

insert into public.academic_years (
    institution_id,
    name,
    start_date,
    end_date,
    is_current
)
select
    id,
    '2026-27',
    date '2026-06-01',
    date '2027-05-31',
    true
from public.institutions
where code in ('BLR-DEMO', 'MYS-DEMO')
on conflict (institution_id, name)
do update
set
    start_date = excluded.start_date,
    end_date = excluded.end_date,
    is_current = excluded.is_current,
    updated_at = now();


-- ============================================================
-- 29. Demo Semesters
-- ============================================================

insert into public.semesters (
    program_id,
    semester_number,
    name
)
select
    p.id,
    semester_number,
    'Semester ' || semester_number
from public.programs p
cross join generate_series(1, 4) as semester_number
on conflict (program_id, semester_number)
do update
set
    name = excluded.name,
    updated_at = now();


-- ============================================================
-- 30. Demo Sections
-- ============================================================

insert into public.sections (
    semester_id,
    name,
    is_active
)
select
    s.id,
    'Section A',
    true
from public.semesters s
on conflict (semester_id, name)
do update
set
    is_active = true,
    updated_at = now();


-- ============================================================
-- End of Phase 1 Foundation Migration
-- ============================================================
