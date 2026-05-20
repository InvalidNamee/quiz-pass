# CLAUDE.md

This file is the working context for Claude Code when changing the Quiz Pass frontend.

## Project Snapshot

Quiz Pass is an AI-powered quiz bank and practice platform. The frontend is a Vue 3 SPA in `frontend/`; the backend is FastAPI in `backend/`.

Current frontend work should focus on adapting to the backend domain/v2 direction while preserving all existing user-visible features. Do not do a visual reset. Improve consistency and information density with small, careful changes.

## Commands

Run from `frontend/`:

```bash
npm run dev
npm run build
npm run preview
```

Backend for local integration, from `backend/`:

```bash
.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
.venv/bin/alembic upgrade head
.venv/bin/python -m pytest tests -q
```

The Vite dev server listens on `0.0.0.0:5173`. It proxies `/api` and `/health` to the backend. `VITE_DEV_API_PROXY_TARGET` can override the proxy target.

## Current Frontend Architecture

Stack:

- Vue 3 + `<script setup>`
- Vue Router
- Pinia
- Tailwind CSS v4 through `@tailwindcss/vite`
- MathJax via `MathText.vue` and `utils/mathjax.ts`

Important files:

- `src/App.vue`: app shell, sidebar placement, mobile overlay, toast container.
- `src/router.ts`: page routes and auth guard.
- `src/stores/auth.ts`: token/user state, login/register/loadMe/logout.
- `src/api/http.ts`: shared fetch wrapper.
- `src/api/types.ts`: shared frontend API types.
- `src/api/*.ts`: typed API modules split by domain.
- `src/components/App*.vue`: base UI primitives.
- `src/components/AppSidebar.vue`: main navigation and user menu.
- `src/components/BankListView.vue`: shared bank list screen.
- `src/components/bank/BankCard.vue`: bank list item/card.
- `src/components/bank/CreateBankModal.vue`: quick manual bank creation.
- `src/components/practice/*`: practice session UI pieces.
- `src/pages/*.vue`: route pages.

Prefer the newer split API modules over putting new calls into the old `api/client.ts`. `api/client.ts` still exists for compatibility and some pages still import it, but new or touched code should move toward `api/http.ts`, `api/types.ts`, and domain-specific modules.

## Backend API Context

The backend now exposes only the `/api/v2` domain-shaped API. Do not add new `/api/v1` calls.

Current v2 areas:

- `/api/v2/banks`
- `/api/v2/banks/{bank_id}/questions`
- `/api/v2/banks/import-json`
- `/api/v2/banks/{bank_id}/import-json`
- `/api/v2/banks/{bank_id}/export-json`
- `/api/v2/practice/sessions`
- `/api/v2/ai/workflows`
- `/api/v2/ai/workflows/{workflow_id}/draft`
- `/api/v2/users`
- `/api/v2/admin/users`

Key backend shape changes to remember:

- AI generation is workflow-first internally.
- A generated/parsed bank now creates a draft first; user confirmation imports questions into the real bank.
- `ImportJob` is a queue/projection layer, not the core AI entity.
- Bank permissions come from backend DTOs. Prefer `bank.permissions` over frontend owner/admin recomputation.

## Product Rules To Preserve

Authentication and users:

- Login supports username or email.
- API keys are entered plainly on creation, but are not displayed or editable after save. Replacing a key means deleting/recreating the config.
- User menu should show only one avatar in the sidebar. The popover can show full account details and links.
- User menu entries: personal homepage, account settings, logout.
- Admin users can edit basic user info, enable/disable ordinary users, and reset passwords. Admins must not grant other users admin role.

Question banks:

- My banks, public banks, and favorites all support pagination, search, tag filtering, and route-query restoration.
- Tag filter URLs must use numeric IDs, e.g. `tag_ids=1,3,8`, not long Chinese tag names.
- Banks can be public/private and both can be favorited if readable.
- Non-owner on public bank can view, favorite, practice, view their own mistakes, and export.
- Non-owner on public bank cannot edit bank, delete bank, manage questions, append import, or AI-extend.
- Admin can manage all banks.
- Private banks are invisible to ordinary non-owners.

AI generation:

- "新建题库" covers two modes:
  - `knowledge_generate`: generate from knowledge/document, optional fixed/adaptive count, optional AI-generated description.
  - `bank_parse`: parse an existing quiz document, no question count field.
- Both modes support user extra instruction.
- Both modes support tags at creation.
- AI workflows produce drafts; drafts must be editable before confirmation.
- Generation queue should show job/workflow state, type, repair attempts, draft count, and full error message.
- If draft is ready, user can continue to draft confirmation from the queue or bank detail.

Practice:

- Practice starts from a specific bank, not a global bank selector.
- Normal practice and mistake practice reveal answer/explanation after answering and lock that question.
- Exam mode saves and locks answers but does not reveal correctness until final submission.
- Results show question stem, options, user selection, correct labels as ABCD, explanation, and unanswered state.
- History should allow resuming in-progress sessions.
- Mistakes belong to `user_id + bank_id + question_id`. The bank mistake page shows only the current user's mistakes for that bank.

## Frontend Design Direction

Use Tailwind CSS utilities and existing base components. Avoid custom CSS unless it is a small shared token or animation in `styles/main.css`.

The current target style is quiet, utilitarian, linear, and information-dense. Do not use bloated SaaS card layouts. The UI should feel closer to traditional desktop software, table systems, and document-style tools than to a marketing dashboard.

- Prefer compact list rows, table-like sections, and document-like blocks over large editorial cards.
- Avoid oversized bank cards. They currently take too much vertical space.
- Keep card padding modest: usually `p-3` or `p-4`, not `p-6`, unless it is a top-level detail header.
- Bank list items should fit more records on one screen.
- Use one-line title rows, compact metadata, small chips, and `line-clamp-1` or `line-clamp-2`.
- Do not make nested cards inside cards.
- Avoid large empty vertical gaps.
- Avoid big hero-like headers inside app pages.
- Avoid large rounded corners, heavy shadows, gradients, and decorative surfaces.
- Prefer thin borders, divider lines, compact spacing, plain buttons, and straightforward alignment.
- Keep radius restrained. Prefer subtle `rounded-md`/`rounded-lg`; avoid large pill/card rounding unless an existing base component requires it.
- Use shadows sparingly. Most surfaces should rely on borders, background contrast, and dividers.
- Avoid large whitespace as a primary visual device. Density and scanability matter more here.
- Keep filters in a modal or compact toolbar; do not consume an entire screen band for every filter.
- Use existing `AppButton`, `AppBadge`, `AppAvatar`, `AppPagination`, `AppEmpty`, `AppLoading`, `AppModal`, and toast utilities.

Bank list/card density guidance:

- `BankCard.vue` should read more like a dense record row than a marketing card.
- Suggested layout: title/status/favorite in first row; description as one short line; tags/author/question count/favorite count/model in a compact metadata row.
- Prefer `text-sm` and `text-xs` for metadata.
- Prefer `gap-2` over `gap-4`.
- Favorite action can be a small text/icon button, not a large visual CTA.

Page density guidance:

- `BankListView.vue`: keep header compact; show active filters as small chips; list uses `grid gap-2`.
- `BankDetailPage.vue`: header can be larger than list rows, but action sections should be compact.
- `PracticeSetupPage.vue`: should match the newer card style and not look like legacy form UI.
- `GenerationDraftPage.vue`: draft editing can be spacious enough to edit safely, but avoid huge repeated blocks when many questions exist.
- `AIProvidersPage.vue`: creation/edit cards should share page width and not create mismatched narrow forms.

## Frontend Work Needed Next

### 1. Use Backend Permissions For Button Visibility

Use `bank.permissions` for bank UI decisions:

- readable actions: favorite, practice, mistakes, export.
- management actions: edit bank, delete bank, questions, append import, AI extend.

Keep route guards defensive. If a user manually opens a management route and backend denies it, show a toast and route back to bank detail.

### 2. Improve Bank List Density

Refactor `src/components/bank/BankCard.vue` first. Preserve all displayed information, but make it denser:

- Reduce padding and gaps.
- Keep title/status/favorite in one row.
- Clamp description to one line on desktop, two on mobile if necessary.
- Move author, tags, counts, model into compact metadata.
- Keep author clickable.
- Keep tags visible but small.

Then adjust `BankListView.vue` only if needed to support the denser item.

### 3. Keep Route Query Behavior

All list pages with filters/pagination must read from and write to query strings:

- `page`
- `keyword`
- `owner_id`
- `tag_ids`
- `visibility`
- `generation_status`
- `status` for job/history queues where applicable

Do not store filter state only in component refs if refresh/back/forward would lose it.

### 4. AI Draft And Queue UX

Generation queue should remain compact but informative:

- Show purpose/type: new bank vs extend bank, knowledge generation vs bank parse.
- Show status, repair attempts, draft question count.
- If failed, show full `error_message` in a readable pre-wrap block.
- If draft is ready, show a clear "确认草稿" action.

Draft confirmation page must preserve editing of:

- bank description
- question type
- stem
- options
- correct options
- explanation
- deleting questions
- adding questions

On confirm failure, show backend validation details as-is; do not collapse detailed error messages into "请求失败".

### 5. Practice And Mistakes UI Consistency

Practice pages should keep the result-page style:

- Use `MathText` for stems, options, and explanations.
- Answer card should scroll internally if long and must not stretch the question area.
- Normal/mistake practice: immediate feedback and locked answer.
- Exam: no correctness/analysis until submit.
- Right answer card colors should be soft, not saturated.
- Mistake page should look like result cards but only show current user's mistakes in the current bank.

## Things To Avoid

- Do not introduce another UI framework.
- Do not add large custom CSS files.
- Do not rewrite the whole frontend in one pass.
- Do not add old-version API calls; the frontend should target `/api/v2`.
- Do not make bank cards or list rows larger than they are now.
- Do not hide existing functionality while improving layout.
- Do not use Chinese tag names in URL query; use tag IDs.
- Do not expose API keys after creation.

## Verification

Minimum before handing back:

```bash
npm run build
```

For UI-affecting work, also run the dev server and manually check:

- login/register
- sidebar/user menu
- public banks
- my banks
- favorites
- bank detail
- new bank / AI generation
- generation queue
- draft confirmation
- practice setup/session/result
- mistakes
- history
- admin users if touched

If backend integration is touched, run at least the relevant backend tests or state clearly that backend tests were not run.
