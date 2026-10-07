-- ============================================================
-- Phase 3A.1: Attendance Foundation
-- Project: College Academic Management
--
-- Scope:
--   Student
--     -> Subject
--     -> Section
--     -> Academic Period
--     -> Attendance Date
--
-- Attendance can enter the system through:
--   1. Direct UI
--   2. Google Sheets import
--
-- Both sources ultimately use the normalized attendance table.
--
-- This migration intentionally does NOT implement:
--   - attendance percentage calculation
--   - eligibility thresholds
--   - fines / condonation
--   - payments / receipts
--   - notifications
--   - timetable/session-level attendance
-- ============================================================


-- ============================================================
-- 1. Attendance
-- ============================================================

create table if not exists public.attendance (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    student_id uuid not null
        references public.students(id)
        on delete restrict,

    subject_id uuid not null
        references public.subjects(id)
        on delete restrict,

    section_id uuid not null
        references public.sections(id)
        on delete restrict,

    academic_period_id uuid not null
        references public.academic_periods(id)
        on delete restrict,

    attendance_date date not null,

    status text not null,

    source text not null default 'DIRECT',

    source_import_id uuid,

    marked_by_user_id uuid
        references public.user_profiles(id)
        on delete set null,

    marked_by_faculty_id uuid
        references public.faculty(id)
        on delete set null,

    correction_reason text,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    constraint attendance_status_check
        check (
            status = any (
                array[
                    'PRESENT'::text,
                    'ABSENT'::text,
                    'LEAVE'::text,
                    'OD'::text,
                    'LATE'::text,
                    'CANCELLED'::text,
                    'SPECIAL'::text
                ]
            )
        ),

    constraint attendance_source_check
        check (
            source = any (
                array[
                    'DIRECT'::text,
                    'GOOGLE_SHEETS'::text
                ]
            )
        ),

    constraint attendance_correction_reason_check
        check (
            correction_reason is null
            or length(trim(correction_reason)) > 0
        ),

    constraint attendance_unique_student_subject_section_period_date
        unique (
            student_id,
            subject_id,
            section_id,
            academic_period_id,
            attendance_date
        )
);


-- ============================================================
-- 2. Attendance indexes
-- ============================================================

create index if not exists idx_attendance_institution_date
    on public.attendance (
        institution_id,
        attendance_date
    );

create index if not exists idx_attendance_student_period
    on public.attendance (
        student_id,
        academic_period_id,
        attendance_date
    );

create index if not exists idx_attendance_subject_section_period_date
    on public.attendance (
        subject_id,
        section_id,
        academic_period_id,
        attendance_date
    );

create index if not exists idx_attendance_marked_by_user
    on public.attendance (
        marked_by_user_id
    );

create index if not exists idx_attendance_source_import
    on public.attendance (
        source_import_id
    );


-- ============================================================
-- 3. Attendance import batches
-- ============================================================

create table if not exists public.attendance_imports (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    source_type text not null,

    source_name text,

    academic_year_id uuid
        references public.academic_years(id)
        on delete restrict,

    academic_period_id uuid
        references public.academic_periods(id)
        on delete restrict,

    section_id uuid
        references public.sections(id)
        on delete restrict,

    subject_id uuid
        references public.subjects(id)
        on delete restrict,

    attendance_date date,

    status text not null default 'PENDING',

    total_rows integer not null default 0,

    successful_rows integer not null default 0,

    failed_rows integer not null default 0,

    duplicate_rows integer not null default 0,

    error_message text,

    started_at timestamptz,

    completed_at timestamptz,

    initiated_by_user_id uuid
        references public.user_profiles(id)
        on delete set null,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    constraint attendance_imports_source_type_check
        check (
            source_type = any (
                array[
                    'GOOGLE_SHEETS'::text,
                    'DIRECT'::text
                ]
            )
        ),

    constraint attendance_imports_status_check
        check (
            status = any (
                array[
                    'PENDING'::text,
                    'RUNNING'::text,
                    'COMPLETED'::text,
                    'PARTIAL'::text,
                    'FAILED'::text
                ]
            )
        ),

    constraint attendance_imports_total_rows_check
        check (total_rows >= 0),

    constraint attendance_imports_successful_rows_check
        check (successful_rows >= 0),

    constraint attendance_imports_failed_rows_check
        check (failed_rows >= 0),

    constraint attendance_imports_duplicate_rows_check
        check (duplicate_rows >= 0)
);


create index if not exists idx_attendance_imports_institution_created
    on public.attendance_imports (
        institution_id,
        created_at desc
    );

create index if not exists idx_attendance_imports_period_section_subject
    on public.attendance_imports (
        academic_period_id,
        section_id,
        subject_id,
        attendance_date
    );


-- ============================================================
-- 4. Attendance import errors
-- ============================================================

create table if not exists public.attendance_import_errors (
    id uuid primary key default gen_random_uuid(),

    attendance_import_id uuid not null
        references public.attendance_imports(id)
        on delete cascade,

    row_number integer,

    permanent_student_id text,

    student_id uuid
        references public.students(id)
        on delete set null,

    subject_code text,

    attendance_date date,

    raw_status text,

    error_code text not null,

    error_message text not null,

    created_at timestamptz not null default now(),

    constraint attendance_import_errors_row_number_check
        check (
            row_number is null
            or row_number > 0
        )
);


create index if not exists idx_attendance_import_errors_import
    on public.attendance_import_errors (
        attendance_import_id,
        row_number
    );

create index if not exists idx_attendance_import_errors_student
    on public.attendance_import_errors (
        student_id
    );


-- ============================================================
-- 5. Google Sheets source configuration
-- ============================================================

create table if not exists public.google_sheet_sources (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    name text not null,

    spreadsheet_id text not null,

    sheet_name text not null,

    academic_year_id uuid
        references public.academic_years(id)
        on delete restrict,

    academic_period_id uuid
        references public.academic_periods(id)
        on delete restrict,

    section_id uuid
        references public.sections(id)
        on delete restrict,

    subject_id uuid
        references public.subjects(id)
        on delete restrict,

    is_active boolean not null default true,

    last_sync_at timestamptz,

    created_by_user_id uuid
        references public.user_profiles(id)
        on delete set null,

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    constraint google_sheet_sources_name_check
        check (length(trim(name)) > 0),

    constraint google_sheet_sources_spreadsheet_id_check
        check (length(trim(spreadsheet_id)) > 0),

    constraint google_sheet_sources_sheet_name_check
        check (length(trim(sheet_name)) > 0),

    constraint google_sheet_sources_unique_sheet
        unique (
            institution_id,
            spreadsheet_id,
            sheet_name
        )
);


create index if not exists idx_google_sheet_sources_institution
    on public.google_sheet_sources (
        institution_id,
        is_active
    );

create index if not exists idx_google_sheet_sources_period
    on public.google_sheet_sources (
        academic_period_id
    );


-- ============================================================
-- 6. Google Sheets synchronization logs
-- ============================================================

create table if not exists public.google_sheet_sync_logs (
    id uuid primary key default gen_random_uuid(),

    google_sheet_source_id uuid not null
        references public.google_sheet_sources(id)
        on delete cascade,

    attendance_import_id uuid
        references public.attendance_imports(id)
        on delete set null,

    sync_status text not null,

    rows_read integer not null default 0,

    rows_processed integer not null default 0,

    rows_failed integer not null default 0,

    rows_skipped integer not null default 0,

    error_message text,

    started_at timestamptz not null default now(),

    completed_at timestamptz,

    created_at timestamptz not null default now(),

    constraint google_sheet_sync_logs_status_check
        check (
            sync_status = any (
                array[
                    'STARTED'::text,
                    'COMPLETED'::text,
                    'PARTIAL'::text,
                    'FAILED'::text
                ]
            )
        ),

    constraint google_sheet_sync_logs_rows_read_check
        check (rows_read >= 0),

    constraint google_sheet_sync_logs_rows_processed_check
        check (rows_processed >= 0),

    constraint google_sheet_sync_logs_rows_failed_check
        check (rows_failed >= 0),

    constraint google_sheet_sync_logs_rows_skipped_check
        check (rows_skipped >= 0)
);


create index if not exists idx_google_sheet_sync_logs_source
    on public.google_sheet_sync_logs (
        google_sheet_source_id,
        started_at desc
    );

create index if not exists idx_google_sheet_sync_logs_import
    on public.google_sheet_sync_logs (
        attendance_import_id
    );


-- ============================================================
-- 7. Add source-import foreign key after both tables exist
-- ============================================================

alter table public.attendance
    add constraint attendance_source_import_id_fkey
    foreign key (source_import_id)
    references public.attendance_imports(id)
    on delete set null;


-- ============================================================
-- 8. Row Level Security
--
-- FastAPI remains the primary authorization boundary.
-- These policies provide the database-level SELECT foundation
-- consistent with the current Phase 1 architecture.
-- ============================================================

alter table public.attendance enable row level security;

alter table public.attendance_imports enable row level security;

alter table public.attendance_import_errors enable row level security;

alter table public.google_sheet_sources enable row level security;

alter table public.google_sheet_sync_logs enable row level security;


-- ============================================================
-- 9. RLS SELECT policies
-- ============================================================

create policy attendance_select_same_institution
on public.attendance
for select
using (
    institution_id = public.current_user_institution_id()
);

create policy attendance_imports_select_same_institution
on public.attendance_imports
for select
using (
    institution_id = public.current_user_institution_id()
);

create policy attendance_import_errors_select_same_institution
on public.attendance_import_errors
for select
using (
    exists (
        select 1
        from public.attendance_imports ai
        where ai.id = attendance_import_errors.attendance_import_id
          and ai.institution_id = public.current_user_institution_id()
    )
);

create policy google_sheet_sources_select_same_institution
on public.google_sheet_sources
for select
using (
    institution_id = public.current_user_institution_id()
);

create policy google_sheet_sync_logs_select_same_institution
on public.google_sheet_sync_logs
for select
using (
    exists (
        select 1
        from public.google_sheet_sources gss
        where gss.id = google_sheet_sync_logs.google_sheet_source_id
          and gss.institution_id = public.current_user_institution_id()
    )
);


-- ============================================================
-- 10. Verification
-- ============================================================

select
    table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
      'attendance',
      'attendance_imports',
      'attendance_import_errors',
      'google_sheet_sources',
      'google_sheet_sync_logs'
  )
order by table_name;