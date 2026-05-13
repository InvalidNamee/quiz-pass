# Quiz Pass

AI-powered quiz practice platform.

## Backend

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/alembic -c ../alembic.ini upgrade head
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Default development database is SQLite at `backend/quiz_pass.db`. Set `DATABASE_URL` in `backend/.env` to use MySQL, for example:

```env
DATABASE_URL=mysql+pymysql://quiz:password@127.0.0.1:3306/quiz_pass
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server listens on `0.0.0.0` and proxies `/api` and `/health` to `http://127.0.0.1:8000` by default. Set `VITE_DEV_API_PROXY_TARGET` if the backend is reachable at another address.

## Current Scope

- JWT registration and login
- User profile with QQ-email avatar source
- User AI provider configs with encrypted API keys
- Question bank CRUD, public/private visibility, favorites, pagination
- Question CRUD
- Long-running generated bank job model with refresh-safe persisted status
- Practice session, history, and bank-scoped mistakes
