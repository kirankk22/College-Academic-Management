-- ============================================================
-- Phase 2 Demo Academic Data
-- ============================================================
--
-- Purpose:
--   Seed a small, reusable demo dataset for development/testing.
--
-- Scope:
--   BLR-DEMO
--     -> MCA
--       -> Academic Year 2026-27
--         -> Semester 1
--           -> Section A
--             -> 6 subjects
--             -> 5 students
--             -> student academic history
--
-- Important:
--   - No attendance data is created here.
--   - No semester results are created here.
--   - No real student data is used.
--   - Existing academic master records are discovered dynamically.
--   - The migration is safe to rerun.
--
-- ============================================================

begin;

-- ============================================================
-- 1. Demo Subjects
-- ============================================================

insert into public.subjects (
    semester_id,
    code,
    name,
    credits,
    is_active,
    has_lab
)
select
    s.id,
    demo.code,
    demo.name,
    demo.credits,
    true,
    demo.has_lab
from public.semesters s
join public.programs p
    on p.id = s.program_id
join public.departments d
    on d.id = p.department_id
join public.institutions i
    on i.id = d.institution_id
cross join (
    values
        (
            'MCA101',
            'Data Structures',
            4::numeric,
            false
        ),
        (
            'MCA102',
            'Database Management Systems',
            4::numeric,
            false
        ),
        (
            'MCA103',
            'Computer Networks',
            4::numeric,
            false
        ),
        (
            'MCA104',
            'Python Programming',
            4::numeric,
            false
        ),
        (
            'MCA105',
            'Software Engineering',
            3::numeric,
            false
        ),
        (
            'MCA106',
            'Python Programming Lab',
            2::numeric,
            true
        )
) as demo(code, name, credits, has_lab)
where i.code = 'BLR-DEMO'
  and p.code = 'MCA'
  and s.semester_number = 1
on conflict (
    semester_id,
    code
)
do update
set
    name = excluded.name,
    credits = excluded.credits,
    is_active = excluded.is_active,
    has_lab = excluded.has_lab,
    updated_at = now();


-- ============================================================
-- 2. Demo Students
-- ============================================================

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
select
    i.id,
    demo.permanent_student_id,
    demo.admission_number,
    demo.first_name,
    null,
    demo.last_name,
    demo.date_of_birth,
    demo.gender,
    demo.email,
    null,
    ay.start_date,
    'active'
from public.institutions i
join public.academic_years ay
    on ay.institution_id = i.id
cross join (
    values
        (
            'MCA26-001',
            'MCA26-001',
            'Arjun',
            'Sharma',
            date '2004-06-15',
            'Male',
            'arjun.sharma@college-demo.local'
        ),
        (
            'MCA26-002',
            'MCA26-002',
            'Bhavana',
            'Rao',
            date '2004-09-22',
            'Female',
            'bhavana.rao@college-demo.local'
        ),
        (
            'MCA26-003',
            'MCA26-003',
            'Charan',
            'Kumar',
            date '2004-03-11',
            'Male',
            'charan.kumar@college-demo.local'
        ),
        (
            'MCA26-004',
            'MCA26-004',
            'Divya',
            'Nair',
            date '2004-12-04',
            'Female',
            'divya.nair@college-demo.local'
        ),
        (
            'MCA26-005',
            'MCA26-005',
            'Eshan',
            'Patil',
            date '2004-08-19',
            'Male',
            'eshan.patil@college-demo.local'
        )
) as demo(
    permanent_student_id,
    admission_number,
    first_name,
    last_name,
    date_of_birth,
    gender,
    email
)
where i.code = 'BLR-DEMO'
  and ay.name = '2026-27'
on conflict (
    institution_id,
    permanent_student_id
)
do update
set
    admission_number = excluded.admission_number,
    first_name = excluded.first_name,
    last_name = excluded.last_name,
    date_of_birth = excluded.date_of_birth,
    gender = excluded.gender,
    email = excluded.email,
    status = 'active',
    updated_at = now();


-- ============================================================
-- 3. Demo Student Academic History
-- ============================================================

insert into public.student_academic_history (
    student_id,
    academic_year_id,
    program_id,
    semester_id,
    section_id,
    roll_number,
    status,
    start_date,
    end_date
)
select
    st.id,
    ay.id,
    p.id,
    s.id,
    sec.id,
    case st.permanent_student_id
        when 'MCA26-001' then 'MCA-S1-001'
        when 'MCA26-002' then 'MCA-S1-002'
        when 'MCA26-003' then 'MCA-S1-003'
        when 'MCA26-004' then 'MCA-S1-004'
        when 'MCA26-005' then 'MCA-S1-005'
    end,
    'active',
    ay.start_date,
    null
from public.students st
join public.institutions i
    on i.id = st.institution_id
join public.academic_years ay
    on ay.institution_id = i.id
join public.programs p
    on p.department_id in (
        select d.id
        from public.departments d
        where d.institution_id = i.id
    )
join public.semesters s
    on s.program_id = p.id
join public.academic_periods ap
    on ap.academic_year_id = ay.id
   and ap.program_id = p.id
   and ap.semester_id = s.id
join public.sections sec
    on sec.academic_period_id = ap.id
   and sec.semester_id = s.id
where i.code = 'BLR-DEMO'
  and ay.name = '2026-27'
  and p.code = 'MCA'
  and s.semester_number = 1
  and ap.period_number = 1
  and ap.period_type = 'SEMESTER'
  and sec.name = 'Section A'
  and st.status = 'active'
  and st.permanent_student_id in (
      'MCA26-001',
      'MCA26-002',
      'MCA26-003',
      'MCA26-004',
      'MCA26-005'
  )
on conflict (
    student_id,
    academic_year_id,
    semester_id
)
do update
set
    program_id = excluded.program_id,
    section_id = excluded.section_id,
    roll_number = excluded.roll_number,
    status = excluded.status,
    start_date = excluded.start_date,
    end_date = excluded.end_date,
    updated_at = now();


commit;


-- ============================================================
-- Verification
-- ============================================================

select
    i.code as institution_code,
    p.code as program_code,
    s.semester_number,
    sub.code as subject_code,
    sub.name as subject_name,
    sub.has_lab
from public.subjects sub
join public.semesters s
    on s.id = sub.semester_id
join public.programs p
    on p.id = s.program_id
join public.departments d
    on d.id = p.department_id
join public.institutions i
    on i.id = d.institution_id
where i.code = 'BLR-DEMO'
  and p.code = 'MCA'
  and s.semester_number = 1
order by sub.code;


select
    i.code as institution_code,
    st.permanent_student_id,
    st.first_name,
    st.last_name,
    st.status,
    p.code as program_code,
    s.semester_number,
    sec.name as section_name,
    sah.status as academic_status,
    sah.roll_number
from public.students st
join public.institutions i
    on i.id = st.institution_id
join public.student_academic_history sah
    on sah.student_id = st.id
join public.programs p
    on p.id = sah.program_id
join public.semesters s
    on s.id = sah.semester_id
join public.sections sec
    on sec.id = sah.section_id
where i.code = 'BLR-DEMO'
  and p.code = 'MCA'
  and s.semester_number = 1
order by st.permanent_student_id;


select
    count(*) as demo_subject_count
from public.subjects sub
join public.semesters s
    on s.id = sub.semester_id
join public.programs p
    on p.id = s.program_id
join public.departments d
    on d.id = p.department_id
join public.institutions i
    on i.id = d.institution_id
where i.code = 'BLR-DEMO'
  and p.code = 'MCA'
  and s.semester_number = 1;


select
    count(*) as demo_student_count
from public.students st
join public.institutions i
    on i.id = st.institution_id
where i.code = 'BLR-DEMO'
  and st.permanent_student_id in (
      'MCA26-001',
      'MCA26-002',
      'MCA26-003',
      'MCA26-004',
      'MCA26-005'
  );


select
    count(*) as demo_academic_history_count
from public.student_academic_history sah
join public.students st
    on st.id = sah.student_id
join public.institutions i
    on i.id = st.institution_id
where i.code = 'BLR-DEMO'
  and st.permanent_student_id in (
      'MCA26-001',
      'MCA26-002',
      'MCA26-003',
      'MCA26-004',
      'MCA26-005'
  )
  and sah.semester_id = (
      select s.id
      from public.semesters s
      join public.programs p
          on p.id = s.program_id
      join public.departments d
          on d.id = p.department_id
      join public.institutions i2
          on i2.id = d.institution_id
      where i2.code = 'BLR-DEMO'
        and p.code = 'MCA'
        and s.semester_number = 1
      limit 1
  );