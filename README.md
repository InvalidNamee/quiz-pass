# Quiz Pass

Quiz Pass is an AI-assisted quiz bank and practice platform. Users can create
question banks, import JSON, generate or parse questions from documents with
their own OpenAI-compatible model, confirm editable AI drafts, practice, review
results, and track bank-scoped mistakes.

## Features

- Email-verified registration, username/email login, JWT refresh token, password
  reset by email.
- User profile, public user page, QQ-email avatar source, admin user management.
- User-owned AI provider configs with encrypted API keys and model-specific
  response format selection.
- Question banks with public/private visibility, favorites, tags, pagination,
  search, JSON import/export, and owner/admin management.
- AI workflow pipeline: document extraction, LangGraph generation/parsing,
  backend validation, AI repair, editable draft, explicit confirmation.
- Bank extension workflows with optional bank AI context and optional existing
  question stem context.
- Public redacted workflow logs under each readable bank.
- Practice, exam, result review, recoverable in-progress sessions, and
  bank-scoped mistakes.
- Element Plus dense desktop UI with KaTeX formula rendering.

## Requirements

- Python 3.13 recommended
- Node.js 20+ recommended
- SQLite for local development, MySQL optional

## Backend Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default development database:

```env
DATABASE_URL=sqlite:///./quiz_pass.db
```

Example MySQL configuration:

```env
DATABASE_URL=mysql+pymysql://quiz:password@127.0.0.1:3306/quiz_pass
```

Useful backend environment variables:

```env
APP_ENV=development
JWT_SECRET_KEY=change-me
FRONTEND_BASE_URL=http://localhost:5173
AI_CONFIG_ENCRYPTION_KEY=
UPLOAD_MAX_MB=10
AI_MAX_TEXT_CHARS=30000
CORS_ORIGINS=*
```

Email verification and password reset use FastAPI-Mail/SMTP when configured. In
development, if SMTP is incomplete, verification and reset links are logged by
the backend.

```env
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
EMAIL_VERIFY_TOKEN_EXPIRE_HOURS=24
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30
```

`SMTP_USE_TLS=true` uses STARTTLS for common ports such as 587 and SSL/TLS for
port 465.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `0.0.0.0` and proxies `/api` and `/health` to
`http://127.0.0.1:8000` by default. Override the backend target with:

```env
VITE_DEV_API_PROXY_TARGET=http://127.0.0.1:8000
```

Production build:

```bash
cd frontend
npm run build
```

## Database and Migrations

Alembic is the schema source of truth:

```bash
cd backend
.venv/bin/alembic upgrade head
```

For a fresh local SQLite database, remove the local database file and run the
upgrade command again. For MySQL, create the database first, set `DATABASE_URL`,
then run Alembic.

## AI Workflow

Users configure their own OpenAI-compatible provider:

- `api_base_url`
- `api_key`
- `model`
- `response_format_type`: `json_object` or `json_schema`

AI generated content is saved as a draft first. Formal questions are written
only after the user confirms the draft.

Workflow statuses are stored separately from the question bank body. Extending a
successful public bank does not make the bank unreadable; the extension state is
visible through the bank workflow log.

## Verification

Backend:

```bash
cd backend
.venv/bin/python -m compileall app
.venv/bin/python -m pytest tests -q
```

Frontend:

```bash
cd frontend
npm run build
```

Before committing, check that generated/local artifacts are not included:

```bash
git status --short
```

`test_quiz_pass.db` and `frontend/tsconfig.tsbuildinfo` are generated/local
artifacts and are ignored by Git.

## Next Engineering Priorities

1. Batch workflow list aggregation to avoid N+1 queries.
2. Rename the KaTeX utility from the old MathJax filename.
3. Extract reusable frontend feature modules for questions, tags, and bank
   creation workflows.
4. Move long-running AI workflow execution from FastAPI `BackgroundTasks` to a
   real queue for production use.
