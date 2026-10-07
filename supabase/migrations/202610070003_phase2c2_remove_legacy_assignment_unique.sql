-- Phase 2C.2 corrective migration
-- Remove the legacy faculty assignment uniqueness constraint.
--
-- The role-aware uniqueness constraint introduced in
-- 202610070002_phase2c2_faculty_lab_assignments.sql
-- supersedes the old constraint.

begin;

alter table public.faculty_assignments
    drop constraint if exists
        faculty_assignments_faculty_id_subject_id_academ_key;

commit;