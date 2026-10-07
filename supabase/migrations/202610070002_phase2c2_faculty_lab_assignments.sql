-- Phase 2C.2
-- Faculty & Lab Assignment Foundation
--
-- Adds subject-level lab configuration and explicit faculty
-- assignment roles.
--
-- Assignment types:
--   SUBJECT
--   LAB_PRIMARY
--   LAB_SECONDARY

begin;

-- ============================================================
-- 1. Subject-level lab configuration
-- ============================================================

alter table public.subjects
    add column if not exists has_lab boolean not null default false;


-- ============================================================
-- 2. Assignment type
-- ============================================================

alter table public.faculty_assignments
    add column if not exists assignment_type text;


-- ============================================================
-- 3. Defensive backfill for any legacy rows
--
-- The current production/demo database has zero rows in
-- faculty_assignments.
--
-- If legacy rows ever exist, they are initially treated as
-- SUBJECT assignments. The application will manage lab roles
-- explicitly from this migration onward.
-- ============================================================

update public.faculty_assignments
set assignment_type = 'SUBJECT'
where assignment_type is null;


-- ============================================================
-- 4. Validate assignment type
-- ============================================================

alter table public.faculty_assignments
    add constraint faculty_assignments_assignment_type_check
    check (
        assignment_type in (
            'SUBJECT',
            'LAB_PRIMARY',
            'LAB_SECONDARY'
        )
    );


-- ============================================================
-- 5. assignment_type is mandatory
-- ============================================================

alter table public.faculty_assignments
    alter column assignment_type set not null;


-- ============================================================
-- 6. Remove the existing uniqueness rule
--
-- Actual existing PostgreSQL constraint:
-- faculty_assignments_faculty_id_subject_id_academ_key
--
-- The old rule prevented the same faculty from being assigned
-- to multiple roles for the same subject/section/year.
-- ============================================================

alter table public.faculty_assignments
    drop constraint if exists
        faculty_assignments_faculty_id_subject_id_academ_key;


-- ============================================================
-- 7. New role-aware uniqueness
--
-- A faculty member cannot have the same assignment role twice
-- for the same subject/section/academic-year.
--
-- The same faculty MAY be:
--   SUBJECT
--   LAB_PRIMARY
-- for the same subject/section/year.
-- ============================================================

alter table public.faculty_assignments
    add constraint faculty_assignments_unique_role
    unique (
        faculty_id,
        subject_id,
        section_id,
        academic_year_id,
        assignment_type
    );


-- ============================================================
-- 8. Only one active SUBJECT faculty
-- ============================================================

create unique index if not exists
    faculty_assignments_one_subject_faculty
on public.faculty_assignments (
    subject_id,
    section_id,
    academic_year_id
)
where assignment_type = 'SUBJECT'
  and is_active = true;


-- ============================================================
-- 9. Only one active PRIMARY LAB faculty
-- ============================================================

create unique index if not exists
    faculty_assignments_one_primary_lab_faculty
on public.faculty_assignments (
    subject_id,
    section_id,
    academic_year_id
)
where assignment_type = 'LAB_PRIMARY'
  and is_active = true;


-- ============================================================
-- 10. LAB_SECONDARY is intentionally not unique by
--     subject/section/year.
--
-- Multiple secondary faculty are allowed.
-- Secondary faculty remains optional.
-- ============================================================


-- ============================================================
-- 11. Keep is_primary consistent with assignment_type
--
-- SUBJECT       -> is_primary = true
-- LAB_PRIMARY   -> is_primary = true
-- LAB_SECONDARY -> is_primary = false
--
-- assignment_type is the authoritative role field.
-- is_primary is retained for compatibility with the existing
-- schema and is kept internally consistent.
-- ============================================================

alter table public.faculty_assignments
    drop constraint if exists
        faculty_assignments_is_primary_consistency_check;

alter table public.faculty_assignments
    add constraint faculty_assignments_is_primary_consistency_check
    check (
        (
            assignment_type in ('SUBJECT', 'LAB_PRIMARY')
            and is_primary = true
        )
        or
        (
            assignment_type = 'LAB_SECONDARY'
            and is_primary = false
        )
    );


-- ============================================================
-- 12. Helpful indexes
-- ============================================================

create index if not exists
    idx_faculty_assignments_subject_section_year
on public.faculty_assignments (
    subject_id,
    section_id,
    academic_year_id
);

create index if not exists
    idx_faculty_assignments_faculty
on public.faculty_assignments (
    faculty_id
);

create index if not exists
    idx_faculty_assignments_assignment_type
on public.faculty_assignments (
    assignment_type
);


-- ============================================================
-- 13. Documentation
-- ============================================================

comment on column public.subjects.has_lab is
    'Whether this subject requires lab faculty assignment. Lab capability is configured per subject, not per department.';

comment on column public.faculty_assignments.assignment_type is
    'Faculty assignment role: SUBJECT, LAB_PRIMARY, or LAB_SECONDARY.';


commit;