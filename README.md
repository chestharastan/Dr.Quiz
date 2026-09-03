# Quiz Dr

A QCM (multiple-choice) test system built from the Khmer-language midwifery
exam bank scanned in `source/`. Admins curate the question bank; students
take scored quizzes. Stack: FastAPI + Postgres (Supabase later) + Next.js
(Vercel later). Runs fully locally today.

## Layout

```
source/                      raw scanned PDFs (input, untouched)
data/extracted/*.json        one question-bank JSON per source PDF (source of truth for DB seed)
backend/                     FastAPI app, SQLAlchemy models, Alembic migrations, OCR pipeline
frontend/                    Next.js app (student quiz + admin panel)
docker-compose.yml           local Postgres for dev
```

## Data provenance and accuracy note

`data/extracted/Untitled 6.json` (101 questions, #421–521) was transcribed
by reading each PDF page directly (not OCR — Tesseract was tested and
rejected for full-page use because it misreads Latin option letters, Khmer
numerals, and the answer-key column). Answer-key letters were read with high
confidence; a subset of longer/technical questions (roughly #471–490 and
#501–520, covering dystocia/partograph and postpartum clinical detail) may
have minor phrasing imperfections. It's marked `needs_review: false` in the
data since it's fully hand-verified.

Any other file under `data/extracted/` produced by the OCR pipeline
(`backend/app/ocr/`, see below) is marked `needs_review: true` with an
`ocr_confidence` score and should be treated as unverified until checked in
the admin panel — filter by "Needs review only" and cross-check against
`source_file` + `source_page` + `question_number` shown per row.

## Local setup

### 1. Start Postgres

```bash
docker compose up -d
```

This runs Postgres on `localhost:5433` (not 5432, to avoid clashing with
other local projects) with database/user/password `quizdr`.

### 2. Backend

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env        # then edit SECRET_KEY and INITIAL_ADMIN_PASSWORD to real random values
python3 -m alembic upgrade head
python3 -m app.seed
python3 -m uvicorn app.main:app --reload --port 8000
```

API is now at `http://localhost:8000`. Check `http://localhost:8000/api/health`.

Re-running `python3 -m app.seed` is safe (idempotent upsert keyed on
`source_file` + `question_number`) and won't undo admin deletions elsewhere,
since it never touches `is_active`. It also creates the initial admin account
(from `INITIAL_ADMIN_USERNAME`/`INITIAL_ADMIN_PASSWORD`) the first time it
runs, and leaves it alone on subsequent runs.

### 3. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # API URLs default to local port 8000
npm run dev
```

Open the printed local URL (usually `http://localhost:3000`, but Next will
pick another free port automatically if 3000 is taken — check the terminal
output). Visit `/login` to sign in — admins land on `/admin`, users land on
`/quiz`.

If your frontend ends up on a different port than 3000, add it to
`CORS_ORIGINS` in `backend/.env` (comma-separated) and restart the backend.
Browser API and image requests are always sent through the Next.js origin, so
the app works the same way locally and from another device on the network. The
server-side `BACKEND_API_BASE_URL` controls where Next.js forwards them.
For development, add the frontend computer's LAN address to
`ALLOWED_DEV_ORIGINS` (comma-separated) when it differs from the example.

## Roles

Two roles: **admin** and **user**, backed by real accounts (bcrypt-hashed
passwords, JWT session cookie) instead of the old shared `ADMIN_TOKEN`. The
first admin account is created by `python3 -m app.seed` from
`INITIAL_ADMIN_USERNAME`/`INITIAL_ADMIN_PASSWORD` in `backend/.env`; that
admin can then create more accounts from the Admin panel.

- **Admin** — manages the question bank, creates **tasks** (a named quiz:
  a question count, optionally scoped to one source file), creates user
  accounts, and assigns each user a task.
- **User** — logs in at `/login`, sees only their assigned task, and takes
  it. No self-serve question count anymore — the assigned task decides.

## Admin workflow

- `/admin` — sign in with an admin account.
- **Questions tab** — filter by source file/question number, soft-delete
  (sets `is_active = false`, keeping the row for audit/undo — no restore
  button yet, toggle "Include deleted" to see hidden ones), export JSON/CSV.
- **Tasks tab** — create a named task (question count + optional source file
  filter) that can be assigned to users.
- **Users tab** — create a user (username/password/role), and reassign any
  user's task at any time from the table.

## Student workflow

- `/login` → `/quiz` — see your assigned task, click Start, answer one
  question per card (auto-advances, Previous/Next to navigate), submit, see
  score and per-question correct answers. Submitted text-quiz attempts and
  their answers are saved to Postgres and shown in the task history. In-progress
  answers are saved to the browser so a refresh never loses them; logging out
  clears that local progress.

## Deploying later (Vercel + Supabase)

Not done yet — this is local-only for now. When ready: create a Supabase
project, point `DATABASE_URL` at it, run `alembic upgrade head` and
`python3 -m app.seed` once against it, then deploy `backend/` (FastAPI/ASGI
app, Vercel's Python runtime auto-detects `app.main:app`) and `frontend/`
(standard Next.js) as separate Vercel projects, wiring
`NEXT_PUBLIC_API_BASE_URL` to the deployed backend URL and `CORS_ORIGINS` to
the deployed frontend URL.
