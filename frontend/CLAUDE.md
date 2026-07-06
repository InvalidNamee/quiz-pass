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
npm run tauri:dev   # Tauri desktop app in dev mode
npm run tauri:build # Vite build + Tauri release build
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
- Tauri v2 desktop shell with local SQLite for downloaded-bank practice

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
| `src/features/utility-windows/` | Tauri child-window opener/event bridge for large form flows |
| `src/local/` | Local SQLite data access, downloaded bank storage, local practice/sync engine |
| `src/composables/` | `useToast` (ElMessage wrapper), `useBankList`, `usePracticeSession` |
| `src/styles/main.css` | Tailwind import, Element Plus overrides, layout utility classes (`qp-page`, `qp-section`, etc.) |
| `src-tauri/` | Desktop shell, capabilities, icons, Rust entry |

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

**Banks:** normal user-owned source banks should stay private/manageable. Public exposure is done by creating a static shared copy through `POST /api/v2/banks/{id}/share`; normal users must not directly set their source bank to public through create/edit/import/generation forms. Favorites work for readable banks. Tags use numeric IDs in query strings (`tag_ids=1,3`) not Chinese names. `generation_status` tracks bank body usability (extension workflows don't make successful banks unreadable). Non-owner on public/shared banks can view/favorite/practice/export/mistakes but not manage. Admins may still manage any bank.

**AI generation:** goes through extract → build → generate/parse → validate → repair → draft → confirm. AI output never enters formal questions without user confirmation. `knowledge_generate` mode creates from documents; `bank_parse` parses existing quiz docs. AI workflows support multiple `.txt/.pdf/.docx` source files, extra instructions, tags, four question types, per-type enabled/limited-count settings, retry/cancel, and optional bank context inheritance.

**Practice:** normal/mistake modes reveal answer+explanation after answering and lock that question; exam mode saves answers but hides correctness until final submit; sessions are recoverable in-progress; results show correct labels/text answers and unanswered state. Question types are `single`, `multiple`, `blank`, and `short_answer`. Blank answers allow empty strings and score wrong; short answer is currently stored but scored wrong. Mistake UI is backed by concrete wrong attempts tied to a specific practice answer, while aggregate mistake rows are only summary/cache.

**Desktop local practice:** readable server banks can be downloaded into local SQLite. Local pages support local practice, result, history, and local mistake attempts. Sync is bidirectional: local pending records upload to the server, and server records for downloaded banks can be pulled into local history. Re-downloading a bank updates active local questions without deleting existing local practice history.

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

## Current Frontend Backlog

The high-level UI migration is mostly done: public sharing actions, two bank
views, continue practice, author picker, workflow operation column cleanup,
question feature extraction, tag normalization, and desktop utility windows are
already implemented. Do **not** rework those areas unless a concrete regression
is found. Keep the dense Element Plus direction: compact table/grid layouts,
small action buttons, thin dividers, and no SaaS-style cards.

### P1: AI Workflow Failure Visibility and Recovery UX

Backend follow-up is expected around source-size validation, stale-workflow
watchdog, RQ failure callbacks, and failed JSON payload persistence. Frontend
should be ready to expose those states without leaking sensitive data.

Required frontend behavior:

- Workflow queue owner detail should show:
  - full owner-visible error message;
  - step timeline;
  - model/base URL snapshot;
  - failed raw/repaired JSON payload when backend provides it;
  - clear timeout/stale-failed status text.
- Public bank workflow logs must remain redacted:
  - no source text;
  - no source file name;
  - no extra instruction;
  - no full error message;
  - no AI config ID;
  - failure summary only.
- Source-too-large errors should surface as readable toast messages, not generic
  `请求失败` or 500 text.
- Polling should stop only on stable states: failed, cancelled, draft-ready,
  imported/succeeded.

Acceptance checks:

- Owner sees detailed failure/debug info in generation queue/detail.
- Public bank workflow page still only shows a concise failed summary.
- Oversized source material produces a readable message.
- Stale/timeout failures do not leave the UI spinning forever.

### P1: New Bank Metadata and Tag Search

Current gap: new-bank creation and retry need durable bank-level AI context, and
the create dialog tag selector should use the same remote-search behavior as tag
filtering.

Required frontend changes:

- Add `ai_context` / `AI 背景知识` field to create-bank flows:
  - AI knowledge generation;
  - bank parse;
  - JSON new-bank import if it creates a source bank.
- Keep meanings distinct:
  - `ai_context` is durable bank context saved on `QuestionBank`;
  - `extra_instruction` is per-workflow and should not be reused as durable
    context.
- Retry UI for `create_bank` must include and submit:
  - title;
  - description;
  - `ai_context`;
  - tags if still editable in the retry form.
- Replace create-bank tag entry with the shared tag selector behavior:
  - search existing tags remotely;
  - allow clean new tag names;
  - normalize through `features/tags/tagUtils.ts`;
  - never submit `null`, empty string, or `"none"`.
- JSON import remains single-file and should continue prefilling title,
  description, and tags from `bank` metadata.

Acceptance checks:

- Creating a bank can save AI background knowledge.
- Retrying a failed create-bank workflow preserves title, description, context,
  and tags.
- Selecting an existing tag submits a string tag name, not `None/null`.
- Switching create modes does not leak stale file/tag/context state.

### P1: Bank List Ownership Defaults and Shared-Copy Noise

Product rule: "我的题库" should primarily show editable source banks, not static
shared copies created for public exposure.

Required frontend behavior:

- Default "我的题库" view should hide `is_shared_copy=true`.
- Add an explicit toggle/filter such as `显示已分享副本` or `我的分享` if users need
  to inspect their shared copies.
- Keep public/shared copies visible in public banks, user profile public banks,
  and favorites when readable.
- Clearly label shared copies with `共享副本`.
- Continue deciding action visibility from `bank.permissions`, not owner/admin
  recomputation.

Acceptance checks:

- A user with one source bank and one shared copy sees only the source bank by
  default in "我的题库".
- Enabling the shared-copy filter shows both.
- Public/favorites/profile pages still show readable shared copies.

### P1: Question Rendering and Editing Details

These are small but user-facing authoring/display problems.

Required changes:

- Option content must allow line breaks:
  - use textarea/autosize textarea in option editors;
  - preserve `\n` when saving/importing/exporting;
  - render options through `MathText` with whitespace preserved in practice,
    result, mistakes, question management, draft preview, and local pages.
- Blank placeholders should be hidden in learner-facing views:
  - raw stem still stores `{{1}}`, `{{2}}`;
  - editor mode continues to show raw placeholders;
  - learner-facing mode renders inline blank markers such as `____` or compact
    `空 1` pills without showing braces.
- Keep the approved answer-card type ordering and W/S row-jump behavior unless
  product explicitly changes it again.

Acceptance checks:

- Multiline option text renders with line breaks everywhere questions are shown.
- A blank stem stores placeholders but learners never see raw `{{1}}`.
- Editor remains capable of editing the raw placeholder text.

### P1: Desktop Local Sync and Re-download QA

Current implementation:

- `syncPendingLocalSessions()` uploads local pending/failed sessions and pulls
  server sessions for downloaded banks into local history.
- Backend can update an existing offline in-progress session into a submitted
  session by the same `(device_id, client_session_id)`.
- Re-downloading a bank soft-updates questions using `is_active` instead of
  deleting local questions, so local histories are not cascaded away.
- Re-download now warns that the local bank snapshot will be overwritten.

Remaining frontend QA/polish:

- If a pulled server session cannot be imported because the local package lacks
  one or more remote questions, show a clear message such as `本地题库版本过旧，请先更新副本`.
- Show sync result details beyond upload/download counts when failures/skips
  happen.
- Provide a compact way to inspect local sync errors on `/local/history`.
- Decide whether local records can be manually deleted and whether deletion
  should only affect local SQLite or also queue a server deletion.
- Test real disconnect/reconnect flows in the Tauri app:
  - start local practice offline;
  - submit offline;
  - reconnect and sync;
  - update local bank package;
  - open older local result/history.

Acceptance checks:

- Re-downloading a changed bank does not remove old local sessions, answers, or
  result pages.
- Sync toast distinguishes upload, download, skipped, and failed work.
- Outdated local bank packages produce user-actionable guidance.

### P2: Local Small-Model Fallback for Blank Matching

Optional future enhancement. Do not start unless backend config/API support is
ready.

Rules:

- Only applies to `blank` questions after exact `strip()` matching fails.
- If enabled, call a configured local small model and ask for strict JSON:
  `{ "accepted": true|false, "reason": "" }`.
- Timeout, invalid JSON, or model failure must fall back to wrong and not block
  submission.
- Frontend should show any backend-provided grading reason in result detail only
  when available.

### P2: Retention, Audit, and Cleanup

- Practice record deletion exists, but policy still needs product confirmation:
  hard delete, soft delete, or redacted audit.
- Add UI only after backend policy is stable.
- Future audit-visible events may include session deletion, watchdog-forced
  workflow failure, and local model fallback grading.

### Lower Priority: Auth Page Visual Sync

The authenticated product pages are aligned to the compact local-bank visual
baseline. Login/register/forgot-password pages still use the older centered
auth-page treatment. This is acceptable for now; update them only after P1 items
are stable.

## Verification

Minimum before handing back:

```bash
npm run build
```

For UI-affecting work, also run the dev server and manually check login/register, sidebar, bank lists, bank detail, AI generation, queue, draft confirmation, practice flow, mistakes, history, and admin users if touched. If backend integration is touched, run relevant backend tests.
