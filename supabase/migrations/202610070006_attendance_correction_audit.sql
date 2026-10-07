-- ============================================================
-- Phase 3A.2A: Attendance Correction Audit
-- Project: College Academic Management
--
-- Purpose:
--   Persist every attendance correction as an immutable
--   before/after audit record.
--
-- This migration does NOT modify the attendance identity or
-- attendance status rules.
-- ============================================================


create table if not exists public.attendance_corrections (
    id uuid primary key default gen_random_uuid(),

    institution_id uuid not null
        references public.institutions(id)
        on delete restrict,

    attendance_id uuid not null
        references public.attendance(id)
        on delete restrict,

    old_status text not null,

    new_status text not null,

    reason text not null,

    changed_by_user_id uuid
        references public.user_profiles(id)
        on delete set null,

    changed_by_faculty_id uuid
        references public.faculty(id)
        on delete set null,

    source text not null default 'DIRECT',

    changed_at timestamptz not null default now(),

    constraint attendance_corrections_old_status_check
        check (
            old_status = any (
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

    constraint attendance_corrections_new_status_check
        check (
            new_status = any (
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

    constraint attendance_corrections_source_check
        check (
            source = any (
                array[
                    'DIRECT'::text,
                    'GOOGLE_SHEETS'::text
                ]
            )
        ),

    constraint attendance_corrections_reason_check
        check (length(trim(reason)) > 0)
);


create index if not exists idx_attendance_corrections_attendance
    on public.attendance_corrections (
        attendance_id,
        changed_at desc
    );


create index if not exists idx_attendance_corrections_institution
    on public.attendance_corrections (
        institution_id,
        changed_at desc
    );


create index if not exists idx_attendance_corrections_changed_by
    on public.attendance_corrections (
        changed_by_user_id,
        changed_at desc
    );


alter table public.attendance_corrections enable row level security;


create policy attendance_corrections_select_same_institution
on public.attendance_corrections
for select
using (
    institution_id = public.current_user_institution_id()
);


select
    table_name
from information_schema.tables
where table_schema = 'public'
  and table_name = 'attendance_corrections';