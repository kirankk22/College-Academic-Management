-- Phase 1: multi-tenant academic foundation.
-- Run this migration in the Supabase SQL Editor for the project database.

create extension if not exists pgcrypto;

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

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  code text not null unique,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.institutions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  code text not null,
  city text,
  state text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, code)
);

create table if not exists public.departments (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  name text not null,
  code text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (institution_id, code)
);

create table if not exists public.programs (
  id uuid primary key default gen_random_uuid(),
  department_id uuid not null references public.departments(id) on delete cascade,
  name text not null,
  code text not null,
  duration_semesters integer not null default 4 check (duration_semesters > 0),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (department_id, code)
);

create table if not exists public.academic_years (
  id uuid primary key default gen_random_uuid(),
  institution_id uuid not null references public.institutions(id) on delete cascade,
  name text not null,
  start_date date not null,
  end_date date not null,
  is_current boolean not null default false,
  created_at timestamptz not null default now(),
  check (end_date > start_date),
  unique (institution_id, name)
);

create table if not exists public.semesters (
  id uuid primary key default gen_random_uuid(),
  program_id uuid not null references public.programs(id) on delete cascade,
  semester_number integer not null check (semester_number > 0),
  name text not null,
  unique (program_id, semester_number)
);

create table if not exists public.sections (
  id uuid primary key default gen_random_uuid(),
  semester_id uuid not null references public.semesters(id) on delete cascade,
  name text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  unique (semester_id, name)
);

create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  email text,
  role public.user_role not null,
  organization_id uuid references public.organizations(id) on delete set null,
  institution_id uuid references public.institutions(id) on delete set null,
  department_id uuid references public.departments(id) on delete set null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_institutions_org on public.institutions(organization_id);
create index if not exists idx_departments_institution on public.departments(institution_id);
create index if not exists idx_programs_department on public.programs(department_id);
create index if not exists idx_academic_years_institution on public.academic_years(institution_id);
create index if not exists idx_semesters_program on public.semesters(program_id);
create index if not exists idx_sections_semester on public.sections(semester_id);
create index if not exists idx_user_profiles_org on public.user_profiles(organization_id);
create index if not exists idx_user_profiles_institution on public.user_profiles(institution_id);

alter table public.organizations enable row level security;
alter table public.institutions enable row level security;
alter table public.departments enable row level security;
alter table public.programs enable row level security;
alter table public.academic_years enable row level security;
alter table public.semesters enable row level security;
alter table public.sections enable row level security;
alter table public.user_profiles enable row level security;

-- The application backend will initially use a controlled service-role
-- connection for server-side operations. Client-facing policies will be
-- added as the authenticated user/role model is completed in Phase 1B.
-- Do not expose the service-role key to the browser.

insert into public.organizations (name, code)
values ('Demo Education Group', 'DEMO-GROUP')
on conflict (code) do nothing;

insert into public.institutions (organization_id, name, code, city, state)
select id, 'Bangalore Demo College', 'BLR-DEMO', 'Bangalore', 'Karnataka'
from public.organizations
where code = 'DEMO-GROUP'
on conflict (organization_id, code) do nothing;

insert into public.institutions (organization_id, name, code, city, state)
select id, 'Mysore Demo College', 'MYS-DEMO', 'Mysore', 'Karnataka'
from public.organizations
where code = 'DEMO-GROUP'
on conflict (organization_id, code) do nothing;

insert into public.departments (institution_id, name, code)
select id, 'Master of Computer Applications', 'MCA'
from public.institutions
where code = 'BLR-DEMO'
on conflict (institution_id, code) do nothing;

insert into public.departments (institution_id, name, code)
select id, 'Master of Business Administration', 'MBA'
from public.institutions
where code = 'BLR-DEMO'
on conflict (institution_id, code) do nothing;

insert into public.departments (institution_id, name, code)
select id, 'Master of Computer Applications', 'MCA'
from public.institutions
where code = 'MYS-DEMO'
on conflict (institution_id, code) do nothing;

insert into public.departments (institution_id, name, code)
select id, 'Master of Business Administration', 'MBA'
from public.institutions
where code = 'MYS-DEMO'
on conflict (institution_id, code) do nothing;

insert into public.programs (department_id, name, code, duration_semesters)
select id, 'MCA', 'MCA', 4
from public.departments
where code = 'MCA'
on conflict (department_id, code) do nothing;

insert into public.programs (department_id, name, code, duration_semesters)
select id, 'MBA', 'MBA', 4
from public.departments
where code = 'MBA'
on conflict (department_id, code) do nothing;
