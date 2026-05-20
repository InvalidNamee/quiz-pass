# Quiz Pass

AI-powered quiz practice platform.

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default development database is SQLite at `backend/quiz_pass.db`. Set `DATABASE_URL` in `backend/.env` to use MySQL, for example:

```env
DATABASE_URL=mysql+pymysql://quiz:password@127.0.0.1:3306/quiz_pass
```

Email verification and password reset use SMTP when configured. In development, if SMTP is not configured, verification/reset links are logged by the backend.

```env
FRONTEND_BASE_URL=http://localhost:5173
SMTP_HOST=
SMTP_PORT=587
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=
SMTP_USE_TLS=true
EMAIL_VERIFY_TOKEN_EXPIRE_HOURS=24
PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30
```

`SMTP_USE_TLS=true` uses STARTTLS for common ports such as 587, and SSL/TLS when `SMTP_PORT=465`.

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `0.0.0.0` and proxies `/api` and `/health` to `http://127.0.0.1:8000` by default. Set `VITE_DEV_API_PROXY_TARGET` if the backend is reachable at another address.

## Current Scope

- JWT login with email verification and password reset
- User profile with QQ-email avatar source
- User AI provider configs with encrypted API keys
- Question bank CRUD, public/private visibility, favorites, pagination
- Question CRUD
- Long-running generated bank job model with refresh-safe persisted status
- Practice session, history, and bank-scoped mistakes
