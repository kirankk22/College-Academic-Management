# Phase 1 — Foundation

## What we are implementing

Phase 1 establishes the foundation only.

### Included

- GitHub repository structure
- React + TypeScript frontend
- FastAPI backend
- Supabase PostgreSQL schema
- Multi-tenant organization/institution hierarchy
- Department/program/semester/section foundation
- User profile and role foundation
- JWT verification boundary
- Health/readiness endpoints
- Local test suite
- GitHub Actions CI
- Render deployment configuration
- Basic logs and health monitoring

### Not included yet

- Attendance
- Google Sheets sync
- Eligibility
- Fine/condonation
- Accounts
- Payments
- Receipts
- Notifications
- Student academic history
- Parent/student full portal
- Reports

Those belong to later phases.

## Step 1 — Create GitHub repository

Recommended repository:

`College-Academic-Management`

Create it under the GitHub account/organization that will own the product.

Initialize it empty if you are uploading this project bundle.

## Step 2 — Local environment

From the repository root:

```bash
python3 --version
node --version
git --version
```

Recommended:
- Python 3.13.x
- Node.js 22.x
- Git current stable

## Step 3 — Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
```

Edit `backend/.env` with the Supabase project URL and JWT secret.

Run:

```bash
uvicorn app.main:app --reload --port 8000
```

Verify:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ready
```

Expected:

```json
{"status":"ok","service":"college-management-api"}
```

and:

```json
{"status":"ready","environment":"local"}
```

Open:

`http://127.0.0.1:8000/docs`

## Step 4 — Backend tests

From `backend/`:

```bash
pytest -q
ruff check app tests
```

Expected: tests pass and lint returns no errors.

## Step 5 — Frontend

From repository root:

```bash
cd frontend
npm install
npm run build
npm run dev
```

Open the Vite URL shown by the terminal, normally:

`http://localhost:5173`

The page should display backend status as `college-management-api: ok`.

## Step 6 — Supabase

Create a dedicated Supabase project for the College Academic Management demo. Do not reuse CareTransparent production data.

Open Supabase SQL Editor and run:

`supabase/migrations/202610060001_phase1_foundation.sql`

Verify that these tables exist:

- organizations
- institutions
- departments
- programs
- academic_years
- semesters
- sections
- user_profiles

Verify demo rows for:
- Demo Education Group
- Bangalore Demo College
- Mysore Demo College
- MCA
- MBA

Do not put a service-role key in frontend environment variables.

## Step 7 — Git

From repository root:

```bash
git init
git add .
git commit -m "feat: initialize college management phase 1"
git branch -M main
git remote add origin <YOUR_GITHUB_REPOSITORY_URL>
git push -u origin main
```

## Step 8 — GitHub CI

GitHub Actions reads:

`.github/workflows/ci.yml`

It runs:
- backend lint
- backend tests
- frontend build

A pull request or push to `main` triggers CI.

## Step 9 — Render

Create/connect the GitHub repository in Render.

The `render.yaml` describes:
- `college-management-api`
- `college-management-frontend`

Configure secrets in Render, never in Git.

Backend:
- SUPABASE_URL
- SUPABASE_JWT_SECRET
- CORS_ORIGINS

Frontend:
- VITE_API_BASE_URL
- VITE_SUPABASE_URL
- VITE_SUPABASE_ANON_KEY

Use the Render backend URL in `VITE_API_BASE_URL`.

Set backend health check to:

`/health`

## Step 10 — CI/CD rule

Preferred flow:

```text
feature branch
      ↓
Pull Request
      ↓
GitHub Actions
  ├── backend lint
  ├── backend tests
  └── frontend build
      ↓
merge to main
      ↓
Render deploy
      ↓
health check
      ↓
live demo
```

Render supports automatic deployment from a linked Git branch and can be configured to deploy after GitHub checks pass.

## Step 11 — Monitoring

For Phase 1:
- Render service health check: `/health`
- Render deploy history/logs
- FastAPI structured basic application logs
- GitHub Actions status
- Supabase database dashboard/logs

Later phases will add:
- request IDs
- centralized structured logs
- error tracking
- metrics
- alerting
- database monitoring
- audit monitoring

## Phase 1 definition of done

Do not start Phase 2 until all of these are true:

1. GitHub repository exists.
2. `main` branch is clean.
3. CI is green.
4. Backend starts locally.
5. Frontend starts locally.
6. Frontend reaches backend.
7. Supabase migration succeeds.
8. Multi-tenant foundation tables exist.
9. Demo organization/campuses/departments exist.
10. Protected `/api/v1/auth/me` returns 401 without a token.
11. Render backend deploys successfully.
12. Render frontend deploys successfully.
13. Backend health check passes on Render.
14. No secrets are committed to GitHub.

Only then move to Phase 2.
