# Quiz Dr

A QCM (multiple-choice) test system built from a scanned Khmer-language
midwifery exam bank. Admins curate the question bank; users take
scored quizzes, and every submitted answer is stored. Stack: FastAPI (Render)
+ Postgres (Supabase) + Next.js (Vercel). Runs fully locally too.

## Layout

```
backend/                     FastAPI app, SQLAlchemy models, Alembic migrations
backend/data/questions.json  the question bank (text only), loaded into Postgres by app.seed
backend/docker-compose.yml   optional local Postgres for development
frontend/                    Next.js app (quiz + admin panel), client-rendered
```

Only these go to GitHub (see `.gitignore`). The scanned PDFs and the
`split-pdf/` tools that turned them into `questions.json` stay on the
author's computer.

## Where the questions live

The questions are in the **backend** (`backend/data/questions.json` →
`questions` table), not in the frontend bundle:

- The browser only ever receives question text and the four choices. The
  correct answers stay on the server, which grades each submission and stores
  it (`quiz_attempts` + `quiz_attempt_answers`).
- There is one copy of the bank, so admin edits (soft-delete, review filter)
  apply to the quiz immediately.
- A quiz only downloads the questions it needs (20 questions ≈ 13 KB), chosen
  at random by Postgres in about 1.5 ms. With Render and Supabase in the same
  region, a quiz start costs one round trip from the user to that region.

`questions.json` is a copy of `split-pdf/outputjson/all.json`: all 7 source
PDFs in one file (1,945 questions), each row tagged with its `source_file`, so
tasks can still be limited to one PDF. Every question was checked against the
scans (`split-pdf/fixes.json`). 47 questions are marked `needs_review: true`
(for example, a scan that printed fewer than 4 options, filled with "none of the
above"). Find them in the admin panel with "Needs review only".

To update the bank: re-run `split-pdf/text_to_json.py`, copy
`split-pdf/outputjson/all.json` over `backend/data/questions.json`, then run
`python3 -m app.seed` again.

## Local setup

### 1. Start Postgres

```bash
cd backend
docker compose up -d
```

This runs Postgres on `localhost:5433` (not 5432, to avoid clashing with
other local projects) with database/user/password `quizdr`. Or skip it and
point `DATABASE_URL` in `backend/.env` at Supabase (see Deploying).

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

On a database that already has the old question bank, `alembic upgrade head`
(migration `d4f7a2c91b3e`) removes the old questions, the old attempt history
and the image-quiz tables. Users and tasks are kept. `app.seed` then loads the
new bank.

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
Browser API requests are always sent through the Next.js origin, so the app
works the same way locally and from another device on the network. The
server-side `BACKEND_API_BASE_URL` controls where Next.js forwards them.
For development, add the frontend computer's LAN address to
`ALLOWED_DEV_ORIGINS` (comma-separated) when it differs from the example.

## Roles

Two roles: **admin** and **user**, backed by real accounts (bcrypt-hashed
passwords, JWT session cookie). The first admin account is created by
`python3 -m app.seed` from `INITIAL_ADMIN_USERNAME` (a username or an email)
and `INITIAL_ADMIN_PASSWORD` in `backend/.env`; that admin can then create
more accounts from the Admin panel. Changing these values later doesn't
change an account that already exists.

- **Admin** — manages the question bank, creates **tasks** (a named quiz:
  a question count, optionally limited to one source file) and user accounts.
- **User** — logs in at `/login`, picks a task, and takes it.

## Admin workflow

- `/admin` — sign in with an admin account.
- **Questions tab** — filter by source file/question number, soft-delete
  (sets `is_active = false`, keeping the row for audit/undo — no restore
  button yet, toggle "Include deleted" to see hidden ones), export JSON/CSV.
- **Tasks tab** — create a named task (question count + optional source file
  filter) that users can pick.
- **Users tab** — create a user (username/password/role) and change roles.

## User workflow

- `/login` → `/quiz` — pick a task, click it to start, answer one question per
  card (auto-advances, Previous/Next to navigate), submit, see score and
  per-question correct answers. Submitted attempts and their answers are saved
  to Postgres and shown in the attempt history. In-progress answers are saved
  to the browser so a refresh never loses them; logging out clears that local
  progress.

## Deploying (Supabase + Render + Vercel)

Put Supabase and Render in the same region, close to the users (e.g.
Singapore). Vercel's region setting doesn't matter here. Every page is static
and client-rendered, so Vercel serves the pages from its global CDN. The only
server work is the FastAPI backend.

1. **Supabase** — create a project. Under *Connect*, copy the **Session
   pooler** connection string (Render can't reach the IPv6-only direct
   connection) and put your database password in it. Special characters in
   the password must be URL-encoded (e.g. `/` → `%2F`). The URL can stay
   `postgresql://...`; the backend switches it to the psycopg driver itself.
2. **Load the database once**, from your computer: put the URL in
   `backend/.env` as `DATABASE_URL`, then
   ```bash
   cd backend
   python3 -m alembic upgrade head
   python3 -m app.seed
   ```
   The seed creates the admin account from `INITIAL_ADMIN_USERNAME` (an email
   works) and `INITIAL_ADMIN_PASSWORD` in `backend/.env`. Run both again
   whenever `questions.json` changes or a new migration is added.
   Migrations turn on row level security for every table, which shuts
   Supabase's public Data API out of them (the backend owns the tables, so it
   isn't affected). A migration that adds a table must enable RLS on it too.
3. **Render** — new Web Service from this repo, root directory `backend`,
   build `pip install -r requirements.txt`, start
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Environment:
   `DATABASE_URL` (same as step 2), `SECRET_KEY` (long random string),
   `COOKIE_SECURE=true`, `CORS_ORIGINS=https://<your-app>.vercel.app`.
   The `INITIAL_ADMIN_*` values aren't needed there. Render's free plan
   sleeps after 15 idle minutes, and the next request then takes up to about a
   minute. A paid instance (or a periodic ping of `/api/health`) avoids that.
4. **Vercel** — import the repo with root directory `frontend`, and set
   `BACKEND_API_BASE_URL=https://<your-service>.onrender.com`. It's read at
   build time, so redeploy after changing it. The browser only talks to
   Vercel, which proxies `/api/*` to Render. That keeps the login cookie
   first-party.
