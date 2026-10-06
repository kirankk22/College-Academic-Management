# College Academic Management Platform

Phase 1 foundation for a multi-tenant, multi-campus College Academic Management Platform.

## Locked architecture

- Frontend: React + TypeScript + Vite
- Frontend hosting: Render Static Site
- Backend: Python + FastAPI
- Backend hosting: Render Web Service
- Database/Auth: Supabase PostgreSQL + Supabase Auth
- Source control: GitHub
- CI: GitHub Actions
- CD: Render automatic deployment after successful CI
- Demo domain: `college-demo.caretransparent.com` (configure later)

## Phase 1 scope

1. Repository and project foundation
2. Frontend/backend local development
3. Supabase database migration foundation
4. Multi-tenant hierarchy:
   Organization -> Institution -> Department -> Program -> Academic Year -> Semester -> Section
5. User profile and role model
6. Supabase Auth JWT verification boundary
7. Basic protected API
8. Health/readiness endpoints
9. Seed/demo data
10. GitHub CI
11. Render deployment configuration
12. Basic application logging/observability

Attendance, Google Sheets sync, eligibility, fine, Accounts, notifications and reports are intentionally deferred to later phases.

## Repository structure

```text
college-academic-management/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .python-version
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── config/
│   │   ├── features/
│   │   ├── layouts/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
├── supabase/
│   └── migrations/
├── .github/workflows/ci.yml
├── render.yaml
└── .env.example
```

## Local setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API:
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/ready
- http://127.0.0.1:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite normally starts at http://localhost:5173.

## Environment variables

Do not commit real secrets.

Backend:
- SUPABASE_URL
- SUPABASE_JWT_SECRET
- ENVIRONMENT
- LOG_LEVEL
- CORS_ORIGINS

Frontend:
- VITE_API_BASE_URL
- VITE_SUPABASE_URL
- VITE_SUPABASE_ANON_KEY

## Git workflow

Use:

```text
main
  └── feature/*
```

Pull requests must pass GitHub Actions before merging.

Render should deploy the main branch only after CI succeeds.

## Phase 1 acceptance criteria

- Backend starts locally.
- `/health` returns 200.
- `/ready` verifies required configuration.
- Swagger loads.
- Frontend starts locally.
- Frontend can call backend health endpoint.
- Supabase migration creates the Phase 1 schema.
- Multi-tenant tables have organization/institution scope.
- RLS is enabled for application tables.
- Protected API rejects requests without a valid bearer token.
- GitHub CI runs backend tests and frontend build.
- Render configuration exists for frontend and backend.
