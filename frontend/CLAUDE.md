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

**Banks:** normal user-owned source banks should stay private/manageable. Public exposure is done by creating a static shared copy through `POST /api/v2/banks/{id}/share`; normal users must not directly set their source bank to public through create/edit/import/generation forms. Favorites work for readable banks. Tags use numeric IDs in query strings (`tag_ids=1,3`) not Chinese names. `generation_status` tracks bank body usability (extension workflows don't make successful banks unreadable). Non-owner on public/shared banks can view/favorite/practice/export/mistakes but not manage. Admins may still manage any bank.

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

## Current Frontend Backlog

The following items remain after the latest backend/frontend P1 work. Do **not** rework the task queue operation column/toast cleanup or the author filter dialog unless a concrete bug is found; those were already handled. Keep the dense Element Plus direction: compact table/grid layouts, small action buttons, thin dividers, no SaaS-style cards.

### 1. Public Sharing UI and Ownership Rules

Backend facts already available:

- `QuestionBankV2` includes `source_bank_id`, `is_shared_copy`, `permissions.can_share`, `permissions.can_manage`, `permissions.can_extend_ai`, `permissions.can_practice`, `resumable_session`.
- `src/api/v2/banks.ts` already exports `shareBank(bankId)`.
- Normal users should not directly publish source banks. Public copies are created through `shareBank`.

Required frontend changes:

- In `src/components/GenerateBankDialog.vue`, remove the public checkbox entirely:
  - Remove `isPublic` from visible UI for AI generation, AI parsing, and JSON new-bank import.
  - Do not submit `visibility=public` for JSON import.
  - Do not submit `desired_visibility=public` for AI workflow creation.
  - Submit/create as private by default. Backend will enforce this too, but the UI must not imply direct publishing is possible.
- In `src/pages/BankDetailPage.vue`, remove direct public/private editing for normal users:
  - Hide the `公开题库` edit checkbox unless the logged-in user is admin and backend permissions allow management.
  - A non-admin owner should edit title/description/tags/AI context, but not make the source bank public.
  - Shared copies (`bank.is_shared_copy === true`) should show a small `共享副本` marker and should not show normal owner management actions unless `bank.permissions.can_manage` is true.
- Add a `分享题库` action wherever bank actions are shown:
  - `BankDetailPage.vue`: show when `bank.permissions.can_share` is true.
  - `BankListView.vue`: show in both table view and future grid view when `row.permissions.can_share` is true.
  - Use `shareBank(row.id)` / `shareBank(bank.id)`.
  - On success, show a clear toast: `已生成公开副本「标题」`.
  - Refresh the current list/detail after sharing. If on detail page, also consider routing to the returned shared copy detail `/banks/${shared.id}` if that feels clearer; keep behavior consistent and explicit.
- The shared copy is static:
  - Do not present AI extend/import/questions/edit/delete controls on a shared copy for normal users.
  - Always decide action visibility from `bank.permissions`, not by recomputing owner/admin in the component.
- Public list display:
  - Show `共享副本` as a small info tag next to visibility/status when `is_shared_copy` is true.
  - Keep author clickable.
  - If `source_bank_id` is present, do not assume the source bank is readable; linking source bank is optional and should handle 404 gracefully.

Acceptance checks:

- New bank dialog no longer has any “公开/生成后自动公开” checkbox.
- JSON import dialog no longer allows choosing public visibility.
- Non-admin cannot find a UI path that directly changes `visibility` to public.
- Owner can share a source bank, gets a new public copy, and original bank remains private/manageable.
- Shared copy hides normal management actions for non-admin users.

### 2. Bank List Two-View Refactor

`src/components/BankListView.vue` currently uses a dense `el-table`. Keep it as the default table/original view, then add a compact grid view. The grid must be dense, not large cards.

Required behavior:

- Add a view switch in the toolbar:
  - Values: `table` and `grid`.
  - Persist in route query as `view=table|grid`.
  - Default to `table` when query is missing or invalid.
  - Switching view should preserve `page`, `keyword`, `owner_id`, `tag_ids`, `visibility`, and `generation_status`.
- Table view:
  - Keep current `el-table` as the original view.
  - Add all primary bank actions outside hidden menus: `开始练习`, `继续练习`, `分享题库`, `删除`.
  - Keep favorite as a visible star; make sure row click does not trigger when clicking buttons.
- Grid view:
  - Use a compact multi-column layout, for example `grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-2`.
  - Each item should be a small bordered panel, not a large card:
    - `border border-slate-200`, `rounded` or `rounded-md`, `p-2`/`p-3`, no shadow, no gradient.
    - Title one line with `truncate`.
    - Description at most one line.
    - Metadata line: author, question count, favorite count, model/status.
    - Tags limited to 2-3 chips plus `+N`.
  - Actions must be directly visible, not buried:
    - `继续练习` when `bank.resumable_session` exists.
    - `开始练习` when `bank.permissions.can_practice`.
    - `分享题库` when `bank.permissions.can_share`.
    - `删除` when `bank.permissions.can_manage` and the bank can be deleted by current user.
  - Use small Element Plus buttons (`size="small"`). Avoid full-width huge CTAs.
- Shared action implementation:
  - Extract small helper methods in `BankListView.vue`: `openPractice`, `continuePractice`, `share`, `delete`.
  - Prefer using existing `PracticeSetupDialog` for start practice.
  - Use `ElMessageBox.confirm` before delete.
  - After share/delete/favorite, call `load()` to refresh list state.

Acceptance checks:

- Table and grid views both preserve filters and pagination in URL query.
- Both views expose `开始练习`, `继续练习`, `分享题库`, and `删除` according to backend permissions.
- Grid view shows substantially more banks per screen than old large-card layouts.
- No large rounded cards, shadows, gradients, or oversized whitespace are introduced.

### 3. Continue Practice UI Completion

Backend and base frontend support already exist:

- Bank DTO has `resumable_session`.
- `GET /api/v2/banks/{bank_id}/practice/resumable-session` exists.
- Current list/detail already have a basic `继续练习` button.

Remaining UI work:

- Ensure `继续练习` is present in both table and grid views.
- In the bank detail page, keep `继续练习` near `开始练习`, not in a secondary menu.
- Button copy:
  - Use `继续练习` in detail and grid.
  - Short `继续` is acceptable only in dense table rows if width is tight.
- Optional metadata:
  - If space allows, show `已做 X/Y` using `resumable_session.answered_count` and `resumable_session.total_questions`.
  - Do not add per-row API calls; use the DTO field only.

Acceptance checks:

- If a bank has an in-progress session, list/detail show continue.
- If no in-progress session exists, no disabled clutter is shown; normal start practice remains.
- Exam sessions continue only while `in_progress`; submitted sessions should not show continue.

### 4. AI / Import Dialog Cleanup

`GenerateBankDialog.vue` already supports multi-file AI source uploads. Keep JSON import single-file.

Required cleanup:

- Rename user-facing upload text so behavior is clear:
  - AI knowledge generation / bank parse: “可上传多个 `.txt/.pdf/.docx` 文件”.
  - JSON import: “上传一个 `.json` 文件”.
- Keep JSON import `:limit="1"` and `multiple=false`.
- For AI generation/parse, keep `multiple=true` and append each file as `files`.
- When switching mode between JSON and AI:
  - Clear the selected files or ensure stale multi-file state cannot be accidentally submitted to JSON mode.
  - If clearing Element Plus internal file list requires an upload ref, add it cleanly.
- File title autofill:
  - New source-bank creation from non-JSON files should use the first file stem as default title when title is empty.
  - Extension mode should not show title/description/tags/public fields that only apply to creating a new source bank.
- Question count UI:
  - `knowledge_generate`: checkbox “指定题数”; when unchecked, submit adaptive mode.
  - `bank_parse`: hide question count completely.

Acceptance checks:

- JSON import cannot select or submit multiple files.
- AI generation/parse can submit multiple files.
- Switching modes cannot leak stale files or public visibility fields.
- Extension JSON import does not show new-bank-only metadata fields.

### 5. Question Management and Draft Editing Guardrails

Backend support already exists:

- `GET /api/v2/banks/{id}/questions?all=true` loads all questions for owner/admin.
- Manual question API, JSON import, and draft confirm reject more than 26 options.
- Draft confirm imports persisted `ai_generation_draft_questions`.

Required frontend checks:

- `src/pages/QuestionsPage.vue` should keep using `all=true` for management.
- Do not add visible pagination to question management unless performance becomes a real issue.
- `src/features/questions/OptionEditor.vue` must keep disabling “添加选项” after 26 options.
- `QuestionEditorDrawer.vue` should surface validation errors from `validateQuestionForm()` before submitting.
- `GenerationDraftPage.vue` must save the draft before confirm:
  - Current flow should call `persistDraft()` first.
  - Only after save succeeds, show the second confirmation and call confirm API.
  - If save fails, do not call confirm.
- Adding a draft question:
  - Use drawer-local state first.
  - Only insert into `draft.questions` when user clicks confirm/save in the drawer.
- Editing a draft question:
  - Clone current row into drawer.
  - Replace row only after drawer confirm.
  - Avoid mutating the list while the user is still editing/cancelling.

Acceptance checks:

- A bank with more than 20 questions shows all questions in management.
- Option editor cannot create AA/overflow labels.
- Editing/deleting draft questions changes the final imported question count and content.

### 6. Personal/Public Bank Lists Using Shared Bank UI

Some pages may still render their own bank tables, especially `src/pages/UserPublicPage.vue`. Align these with the shared list style without introducing bulky cards.

Required changes:

- Prefer reusing small shared bank row/grid subcomponents if introduced for `BankListView.vue`.
- User profile public bank list should show:
  - title, shared/public marker, tags, question count, favorite count, author if useful.
  - visible actions allowed for current viewer: start/continue/favorite/share only when permission says so.
- Keep layout compact and consistent with `BankListView.vue`.

Acceptance checks:

- Personal/public profile bank list no longer looks like an old isolated style.
- Actions and tags are visually consistent with main bank lists.

## Verification

Minimum before handing back:

```bash
npm run build
```

For UI-affecting work, also run the dev server and manually check login/register, sidebar, bank lists, bank detail, AI generation, queue, draft confirmation, practice flow, mistakes, history, and admin users if touched. If backend integration is touched, run relevant backend tests.
