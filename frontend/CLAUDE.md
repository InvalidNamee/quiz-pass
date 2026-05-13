# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quiz Pass is a full-stack AI-powered quiz practice platform. The frontend (Vue 3 SPA) lives in `frontend/`, the backend (FastAPI) lives in `backend/`. The repo root is `/Users/wangyafei/Projects/Quiz` — CWD is typically `frontend/` for UI work or `backend/` for API work.

## Commands

### Frontend (in `frontend/`)
```bash
npm run dev              # Vite dev server on 0.0.0.0:5173, proxies /api → localhost:8000
npm run build            # vue-tsc type-check + vite build
npm run preview          # Preview production build
```

### Backend (in `backend/`)
```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
.venv/bin/alembic -c ../alembic.ini upgrade head   # Run migrations
.venv/bin/python -m pytest tests/ -v                # Run tests
```

## Architecture

### Backend (`backend/app/`)
- **FastAPI** with lifespan-managed DB table creation (auto-creates tables, Alembic for migrations)
- **Layered structure**: `models/` (SQLAlchemy ORM) → `schemas/` (Pydantic) → `api/v1/` (route handlers) → `services/` (business logic) → `utils/`
- **Auth**: JWT (HS256) via `python-jose`. Passwords: bcrypt over SHA-256 digest. Dependency `get_current_user` in `api/deps.py` injects the authenticated `User` into routes. `require_admin` gates admin endpoints.
- **DB**: SQLAlchemy 2.0 with `SessionLocal` generator. Supports SQLite (default) and MySQL via `DATABASE_URL`. `check_same_thread=False` for SQLite. `pool_pre_ping=True` for MySQL.
- **Config**: `core/config.py` uses `pydantic-settings` reading from `backend/.env`. `CORS_ORIGINS` parsed from comma-separated string.
- **API key encryption**: Fernet symmetric encryption in `utils/crypto.py`, key derived via SHA-256 from `AI_CONFIG_ENCRYPTION_KEY` or `JWT_SECRET_KEY`.
- **AI generation**: `services/ai_generation.py` calls OpenAI-compatible APIs. Supports two modes: `knowledge_generate` (create questions from material) and `bank_parse` (extract existing questions from a document). Runs as FastAPI background task. Validates single/multiple-choice answer counts strictly before persisting.
- **Pagination**: `utils/pagination.py` — `paginate(db, stmt, page, page_size)` returns `(items, total, page, page_size)`. Page capped at 100, page_size clamped to 1-100.
- **Document extraction**: `utils/document_extractors.py` handles `.txt`, `.pdf` (pypdf), `.docx` (python-docx).
- **Key models**: `User`, `QuestionBank`, `Question`, `QuestionOption`, `QuestionBankFavorite`, `ImportJob`, `PracticeSession`, `PracticeSessionQuestion`, `PracticeAnswer`, `MistakeRecord`, `UserAIProviderConfig`, `UserPromptTemplate`.
- **Question bank states**: `generation_status` tracks AI generation lifecycle (`none`/`pending`/`processing`/`succeeded`/`failed`). `desired_visibility` is the user's target; actual `visibility` stays `private` until generation succeeds.

### Frontend (`frontend/src/`)
- **Stack**: Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS v4
- **API client** (`api/client.ts`): Thin `fetch` wrapper — auto-attaches `Authorization: Bearer` from localStorage, sets `Content-Type: application/json` (skipped for FormData), parses FastAPI validation error detail arrays. All type definitions (`UserMe`, `QuestionBank`, `Question`, `PracticeSession`, etc.) live here.
- **Auth store** (`stores/auth.ts`): Pinia store with `user`, `token`, `login`, `register`, `loadMe`, `logout`. Token persisted in localStorage.
- **Router** (`router.ts`): `createWebHistory` with `meta.auth` guards. BeforeEach hook calls `auth.loadMe()` on token-present-but-no-user, redirects to `/login` if unauthenticated.
- **Reusable component**: `BankListView.vue` — paginated, filterable bank list used by BanksPage, PublicBanksPage, FavoritesPage. Props control which filters/actions are shown.
- **No build-step CSS framework** — Tailwind v4 via `@tailwindcss/vite` plugin (zero-config, CSS-first config in `styles/main.css`).
- **Vite proxy**: `/api` and `/health` proxied to backend. Override target via `VITE_DEV_API_PROXY_TARGET` env var.

### API Routes (`/api/v1`)
| Prefix | Module | Purpose |
|--------|--------|---------|
| `/auth` | `auth.py` | register, login, me |
| `/users` | `users.py` | profile CRUD, password change, AI configs, user search, public profiles |
| `/question-banks` | `question_banks.py` | CRUD, public list, favorites, JSON export/import |
| `/questions` | `questions.py` | CRUD under banks (routes use `/question-banks/{id}/questions` and `/questions/{id}`) |
| `/ai-generation` | `ai_generation.py` | Create generation jobs (multipart form), list/cancel/confirm jobs |
| `/practice` | `practice.py` | Sessions, answers, submission, results, mistakes, history |
| `/admin` | `admin.py` | User listing (admin-only) |
