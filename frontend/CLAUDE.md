# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Snapshot

Quiz Pass is an AI-powered quiz bank and practice platform. The frontend is a Vue 3 SPA in `frontend/`; the backend is FastAPI in `backend/`.

Current frontend work should focus on adapting to the backend domain/v2 direction while preserving all existing user-visible features. Do not do a visual reset. Improve consistency and information density with small, careful changes.

## Commands

Run from `frontend/`:

```bash
npm run dev         # Vite dev server on 0.0.0.0:5173
npm run build       # vue-tsc -b && vite build
npm run preview     # vite preview --host
```

Backend for local integration, from `backend/`:

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest tests -q
```

The Vite dev server proxies `/api` and `/health` to `http://127.0.0.1:8000`. Override with `VITE_DEV_API_PROXY_TARGET`.

## Stack

- Vue 3 + `<script setup>` + TypeScript (ES2022, strict, bundler module resolution)
- Vue Router 4 (hash-less `createWebHistory`)
- Pinia (one store: `auth.ts`)
- Vite 7 + `@vitejs/plugin-vue` + `@tailwindcss/vite` + Tailwind CSS v4
- Element Plus (zh-CN locale, dense table-oriented CSS overrides in `styles/main.css`)
- KaTeX via `MathText.vue` and `utils/mathText.ts`

## Key Files and Structure

| Path | Purpose |
|------|---------|
| `src/App.vue` | Shell: sidebar placement, mobile overlay, auth-gated rendering |
| `src/router.ts` | 20+ routes, auth guard, lazy user loading |
| `src/stores/auth.ts` | Token/user state, login/register/loadMe/logout |
| `src/api/http.ts` | Shared fetch with auto-refresh, error parsing, `buildQuery`, `statusVariant` |
| `src/api/types.ts` | Shared types: Page, QuestionBank, UserMe, PracticeSession, MistakeRecord, v2 types |
| `src/api/v2/*.ts` | Domain-split typed API modules (auth, banks, practice, aiGeneration, users) |
| `src/pages/*.vue` | One page per route, 20 pages total |
| `src/components/**` | Shared UI: AppSidebar, App.. base, practice/*, BankCard, WorkflowTable, MathText |
| `src/features/questions/` | QuestionTable, QuestionEditorDrawer, OptionEditor, questionForm |
| `src/features/tags/tagUtils.ts` | Tag normalization (filters null/empty/none before sending) |
| `src/composables/` | `useToast` (ElMessage wrapper), `useBankList`, `usePracticeSession` |
| `src/styles/main.css` | Tailwind import, Element Plus overrides, layout utility classes (`qp-page`, `qp-section`, etc.) |

`api/client.ts` still exists for compat but new/touched code should use `api/http.ts` + `api/v2/*`.

## Backend API Surface (`/api/v2`)

- `/api/v2/banks` — bank CRUD, JSON import/export
- `/api/v2/banks/{id}/questions` — question CRUD
- `/api/v2/practice/sessions` — practice sessions, answers, results
- `/api/v2/ai/workflows` — AI generation workflows, drafts, confirmation
- `/api/v2/users` — profile, providers, public page
- `/api/v2/admin/users` — admin user management

Key shape changes: AI generation is workflow-first; generated banks create drafts before formal import; bank permissions come from `bank.permissions` (not frontend owner recomputation).

## Product Rules

**Auth:** login by username or email; JWT access+refresh tokens with auto-refresh in `http.ts`; API keys entered plainly on creation, never shown/edited after; admin can manage users but must not grant admin role.

**Banks:** public/private visibility; favorites work for both; tags use numeric IDs in query strings (`tag_ids=1,3`) not Chinese names; `generation_status` tracks bank body usability (extension workflows don't make successful banks unreadable); non-owner on public bank can view/favorite/practice/export/mistakes but not manage.

**AI generation:** goes through extract → build → generate/parse → validate → repair → draft → confirm. AI output never enters formal questions without user confirmation. `knowledge_generate` mode creates from documents (optional fixed/adaptive count, optional AI description). `bank_parse` mode parses existing quiz docs (no question count field). Both support extra instructions and tags.

**Practice:** normal/mistake modes reveal answer+explanation after answering and lock that question; exam mode saves answers but hides correctness until final submit; sessions are recoverable in-progress; results show ABCD correct labels and unanswered state; mistakes are `user_id + bank_id + question_id` scoped.

## Design Direction

Quiet, utilitarian, information-dense. Tailwind utilities + Element Plus components only. No custom CSS beyond `styles/main.css` tokens. No SaaS card layouts, heavy shadows, gradients, large rounding, or excess whitespace. `p-3`/`p-4` not `p-6` for cards. `text-sm`/`text-xs` for metadata. Compact rows over editorial cards.

## Route Query Convention

All list pages (banks, public banks, favorites, jobs, history) read filters from and write filters to query strings: `page`, `keyword`, `owner_id`, `tag_ids`, `visibility`, `generation_status`, `status`. Do not store filter state only in component refs.

## Things To Avoid

- No additional UI frameworks
- No large custom CSS files
- No old `/api/v1` calls
- No bank cards larger than current density
- No hide existing functionality while improving layout
- No Chinese tag names in URLs
- No exposing API keys after creation

## Verification

Minimum before handing back:

```bash
npm run build
```

For UI-affecting work, also run the dev server and manually check login/register, sidebar, bank lists, bank detail, AI generation, queue, draft confirmation, practice flow, mistakes, history, and admin users if touched. If backend integration is touched, run relevant backend tests.
