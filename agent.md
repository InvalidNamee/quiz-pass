# Quiz Pass Agent Notes

This document is the current engineering map for Quiz Pass. It records the
actual architecture, important product rules, completed milestones, and the
recommended next steps for future agents.

## Product Summary

Quiz Pass is an AI-assisted quiz bank and practice system. Users can create
question banks manually, import JSON, generate or parse banks from documents
with their own OpenAI-compatible model configuration, confirm editable AI
drafts before questions enter the formal bank, practice questions, review
results, and manage bank-scoped mistakes.

Core product principles:

- Question banks are user-owned source resources. Ordinary users do not publish
  mutable source banks directly; public exposure is done by creating a static
  shared copy. Management stays with the source owner or admin.
- Mistakes shown to users are concrete wrong attempts tied to a specific
  practice session/answer. The older aggregate mistake row remains as a summary
  cache, not the main review object.
- AI output is never inserted directly into formal questions. It goes through
  extraction, model generation/parsing, validation, optional repair, draft
  creation, user editing, and explicit confirmation.
- The desktop client is local-first for downloaded banks: users can practice
  against local SQLite and later sync complete sessions back to the server.
- Public workflow logs must be useful but redacted: no source text, source file
  name, extra instruction, full error message, or AI config ID.

## Current Architecture

### Backend

Backend is FastAPI + SQLAlchemy + Alembic, organized by domain under
`backend/app/domains`.

Main domains:

- `users`: auth, profile, email verification, password reset, AI provider
  configuration, admin user operations.
- `question_banks`: bank CRUD, permissions, queries, lifecycle, stats, tags,
  question CRUD, JSON import/export.
- `practice`: practice sessions, answer saving/submission, scoring, history,
  result detail, mistakes.
- `ai_generation`: workflow creation, LangGraph runtime, OpenAI-compatible
  client, prompts, validation, repair, drafts, confirmation, cancel/retry,
  workflow logs.

Important backend rules:

- `/api/v2` is the current API surface. Old v1 code has been removed or
  superseded.
- Alembic owns schema creation. Application startup should not depend on
  `Base.metadata.create_all`.
- `QuestionBank.generation_status` describes whether the bank body is usable.
  Extension workflow state is expressed by workflow records and
  `active_workflow`, not by making an existing successful bank unreadable.
- Admin can manage all banks and ordinary users, but must not grant admin role
  through the UI/API.
- API keys are encrypted at rest. They are accepted at create time and are not
  returned to the frontend.

### Frontend

Frontend is Vue 3 + TypeScript + Vite + Element Plus + Tailwind utilities. It
also includes a Tauri v2 desktop shell for local-first downloaded-bank practice.

Current UI direction:

- Avoid large SaaS-card layouts, heavy shadows, gradients, large rounded cards,
  and excess whitespace.
- Prefer dense desktop-style layouts: tables, thin borders, dividers, compact
  controls, and plain buttons.
- Use Element Plus components as the UI baseline.
- Logged-in main pages should use the same compact baseline as the local-bank
  pages: `qp-page`, `qp-titlebar`, `qp-section`, shallow borders, little/no
  shadow, and linear information layout.
- Sidebar navigation is grouped by learning-first categories:
  `学习`, `题库`, `AI`, and admin-only `管理`.

Main frontend structure:

- `frontend/src/api/v2`: typed v2 API wrappers.
- `frontend/src/pages`: route pages.
- `frontend/src/components`: shared UI components including bank creation,
  workflow table, MathText, practice controls, avatar/sidebar.
- `frontend/src/local`: local SQLite data access and local practice engine for
  downloaded banks.
- `frontend/src/features/utility-windows`: Tauri child-window infrastructure
  for large form flows; browser fallback still uses Element Plus dialogs.
- `frontend/src/stores/auth.ts`: auth state, token refresh, current user.
- `frontend/src-tauri`: Tauri app shell, capabilities, icons, and Rust entry.

Notable pages:

- `/banks`, `/banks/public`, `/favorites`: bank lists with query-friendly
  filters.
- `/banks/:bankId`: bank detail, practice/export/mistakes/workflow log/actions.
- `/banks/:bankId/workflows`: redacted bank workflow log for all readable users.
- `/banks/generation-jobs`: current user's full workflow queue.
- `/ai-generation/workflows/:workflowId/draft`: editable AI draft confirmation.
- `/practice/session/:sessionId`, `/practice/result/:sessionId`: practice flow.
- `/local/banks`, `/local/banks/:localBankId`, `/local/history`,
  `/local/practice/session/:localSessionId`, `/local/practice/result/:localSessionId`:
  downloaded-bank local practice flow.

## Data Model Highlights

Important tables:

- `users`: auth/profile/admin state, email verification timestamp.
- `email_auth_tokens`: hashed email verification and password reset tokens.
- `user_ai_provider_configs`: user-owned OpenAI-compatible configs, encrypted
  API keys, response format preference.
- `question_banks`: owner, visibility, desired visibility, stats, AI context,
  last model snapshots, `source_bank_id`, and `is_shared_copy`.
- `question_bank_tags` and `question_bank_tag_links`: global tag table and
  many-to-many bank links.
- `questions`, `question_options`, and `question_blanks`: formal bank content
  for single choice, multiple choice, blank, and short answer questions.
- `practice_sessions`, `practice_session_questions`, `practice_answers`:
  practice recovery, draft answer saving, submission, scoring, offline sync
  identity, and mistake-review source context.
- `mistake_attempts`: concrete wrong attempts tied to a session answer.
- `mistake_records`: aggregate mistake summary/cache.
- `ai_generation_workflows`: AI workflow source of truth.
- `ai_generation_workflow_steps`: node logs for extract/build/generate/validate/
  repair/write/fail/confirm.
- `ai_generation_drafts` and `ai_generation_draft_questions`: editable draft
  before formal import.
- `import_jobs`: thin queue/compat projection for workflows.
- Tauri local SQLite tables mirror downloaded banks and local sessions:
  `local_banks`, `local_questions`, `local_options`, `local_blanks`,
  `local_practice_sessions`, `local_session_questions`, `local_answers`,
  `local_mistake_attempts`, and sync metadata.

## Completed Capabilities

### Auth and Users

- Registration with email verification.
- Login by username or email.
- JWT access and refresh token flow.
- Password reset by email.
- Profile editing, password change, avatar URL/QQ email avatar source.
- Public user profile page.
- Admin user list with pagination/filtering, basic profile edits, enable/disable,
  and password reset. Admin role granting is intentionally unavailable.

### AI Provider Configuration

- Users can store multiple AI provider configs.
- Display name may be empty; UI falls back to model name.
- API key is entered plainly during creation, then hidden and non-editable.
- Configs support `json_object` and `json_schema` response format preference.
- AI calls use the OpenAI Python SDK against user-provided OpenAI-compatible
  `base_url`.

### Question Banks and Questions

- Bank CRUD with owner/admin management permissions.
- Ordinary user publishing is implemented through static shared copies; admins
  can still manage visibility directly for operations.
- Favorites for readable banks.
- Bank tags with independent tag table and multi-tag OR filtering by numeric ID.
- JSON import/export.
- Question CRUD with single/multiple/blank/short-answer validation.
- Owner/admin can manage all questions; non-owner public readers can view/export/
  practice/mistakes but cannot manage.
- Bank lists support table and dense grid views, visible primary actions, latest
  practice progress, and resume buttons from DTO state without per-row calls.

### AI Workflow

- New bank creation and bank extension workflows.
- Modes:
  - `knowledge_generate`: create questions from knowledge material.
  - `bank_parse`: parse existing bank-like documents.
- Workflow persistence with steps, source text snapshot, model snapshots,
  repair attempts, and error message.
- Prompt path: extract document -> build context -> generate/parse -> validate ->
  repair -> draft -> user confirm.
- Draft page supports editing before import.
- Cancel draft/failed workflow.
- Retry failed workflow into a new child workflow; once retried, the old failed
  workflow cannot be retried or cancelled again.
- Bank AI context can be inherited by extension workflows.
- Existing question stems can optionally be sent to AI for extension, but only
  type + stem, with a context character budget and truncation notice.
- Per-bank workflow log page for all readable users, with sensitive fields
  redacted.

### Practice and Mistakes

- Practice, exam, and mistake sessions.
- Normal practice gives immediate feedback and locks submitted questions.
- Exam mode saves answers but does not reveal correctness until final submit.
- Exam final submit accepts a `commit_drafts` choice, so cached unlocked answers
  can either be counted or ignored as unanswered.
- Users can leave and resume in-progress sessions. The current practice page
  starts direct entries at the first question and uses `?resume=1` for explicit
  continue/resume behavior.
- Result page includes question content, options, user selection, correct labels,
  explanation, and unanswered state.
- Blank answers allow empty strings and score wrong rather than validation
  failing; short-answer questions are currently stored but scored wrong.
- Users can delete their own practice records.
- Mistake page is bank-scoped but backed by concrete wrong attempts. Each card
  has the question snapshot, user answer, correct answer, explanation, wrong
  time, and source session. Resolving one attempt removes only that attempt.
- Mistake-practice sessions can start from a bank's unresolved attempts or from
  a specific practice record's unresolved attempts, and unfinished
  mistake-practice sessions can be resumed.

### Desktop Local Practice

- Tauri desktop shell is present under `frontend/src-tauri`.
- Users can download readable banks as local packages.
- Local SQLite stores downloaded bank snapshots, local sessions, local answers,
  and local mistake attempts.
- Local practice/result/history pages exist and reuse the same four question
  types and scoring semantics.
- `/api/v2/banks/{bank_id}/download-package` downloads readable bank packages.
- `/api/v2/offline/practice-sync` uploads local sessions idempotently by
  `(user_id, device_id, client_session_id)`.

### Frontend UX

- Element Plus based dense desktop UI.
- KaTeX formula rendering through `MathText`.
- WASD/arrow navigation in practice pages.
- Generation polling for unstable workflow/bank states.
- Shared workflow table for generation queue and bank workflow logs.
- Main logged-in pages are now aligned to the local-bank visual language:
  compact `qp-section`/`qp-titlebar` surfaces, thin borders, reduced shadows,
  dense tables, and shallow icon buttons.
- Sidebar navigation is grouped into `学习`, `题库`, `AI`, and admin-only
  `管理`.
- Tauri desktop uses independent utility windows for larger form flows such as
  bank generation, AI config, practice setup, bank edit, filters, admin user
  edit, and submit-practice choices. These windows render page-style forms, not
  nested dialogs.

## Known Issues and Technical Debt

- Authentication pages still use their older centered visual treatment. This is
  acceptable for now because the main UI sync intentionally targeted
  authenticated product pages.
- Browser fallback dialogs still exist for Web mode. Desktop/Tauri should prefer
  utility-window pages for larger form flows.
- Toast coverage is still uneven in some flows and should continue to use
  parsed backend error messages plus precise success messages.
- AI workflow failures need stronger production guardrails: source-size
  validation, stale-workflow watchdog, RQ failure callbacks/dead-letter
  guidance, and owner-visible failed JSON payloads.
- New-bank metadata still needs final product review around durable
  `ai_context`/background knowledge creation and retry preservation.
- Option content should allow authoring and rendering multiline text.
- Learner-facing blank placeholder rendering should hide raw `{{1}}`/`{{2}}`
  while keeping raw placeholders in editor mode.
- Email delivery is configured through SMTP and logs links in development when
  SMTP is incomplete. Production deployment must verify SMTP credentials and
  sender policy.

## Recommended Next Steps

### Done: Repository Hygiene and Generated Artifacts

- `test_quiz_pass.db` and `frontend/tsconfig.tsbuildinfo` have been removed from
  Git tracking with `git rm --cached`.
- `.gitignore` now ignores the root test database and frontend TypeScript build
  info file.

### Done: Workflow List Performance and DTO Hardening

- Workflow list endpoints use batch DTO assembly for draft counts, imported
  counts, jobs, and retry children.
- Public bank workflow logs stay redacted by default.
- Tests cover public readable bank logs for extension workflows in pending,
  draft-ready, failed, cancelled, and imported states.

### Done: Frontend Feature Cleanup

- KaTeX utility is now `mathText.ts`.
- Question editor/table logic lives in `features/questions`.
- Tag normalization lives in `features/tags`.
- Keep Element Plus dense layout and remove remaining large-card patterns.

### Done: Main Page UI Sync and Sidebar Classification

- Done: logged-in main pages now share the local-bank visual baseline:
  `qp-page`, `qp-titlebar`, `qp-section`, thin borders, compact padding, reduced
  shadow, and dense Element Plus tables.
- Done: high-traffic pages were aligned: dashboard, bank lists, bank detail,
  history, generation tasks, AI providers, admin users, public profile bank
  list, question management, bank workflow logs, mistake page, result page, and
  practice card/navigator components.
- Done: sidebar navigation is grouped into `学习`, `题库`, `AI`, and admin-only
  `管理`, using one lucide icon style.
- Done: table operation columns are left-aligned and use shared shallow
  `qp-icon-button` actions.
- Done: desktop utility-window forms remain page-style instead of nested
  `el-dialog` windows.
- Verified in the latest UI sync pass:
  - `cd frontend && npm run build`
  - `cd frontend && npm run tauri:build`
  - `git diff --check`

### Done: Backend Service Boundary Cleanup

- Removed the legacy top-level `backend/app/services` package.
- Moved AI compatibility functions to `domains/ai_generation/facade.py`.
- Moved question bank tag helpers to `domains/question_banks/tags.py`.
- Moved SMTP delivery to `infrastructure/email.py`.

### Partially Done: AI Workflow Operations

- Done: owner workflow detail drawer/page exists with input snapshot, context
  flags, step list, model info, repair attempts, and full error message.
- Done: failed/cancelled/draft-ready final-head workflows can be retried, and
  retried old nodes cannot be retried/cancelled/confirmed again.
- Remaining: add optional manual "re-run repair" for invalid draft questions if
  product rules still need it.

### Partially Done: Production Readiness

- Done: long-running AI workflows can run through RQ + Redis.
- Done: RQ worker concurrency is configurable with `AI_WORKFLOW_WORKER_COUNT`,
  and Docker Compose also supports `--scale worker=N`.
- Done: runtime nodes check cancellation before continuing.
- Done: minimal audit events exist for workflow retry/cancel/confirm, bank
  share/delete, and admin user operations.
- Done: deployment docs cover Docker Compose, MySQL, Redis, worker scaling, and
  key environment variables.
- Remaining: add structured application logging, stale-workflow watchdog, and
  production failure callbacks/dead-letter guidance.

### Partially Done: Desktop Local Practice Migration

- Done: Tauri v2 shell builds from `frontend/src-tauri`.
- Done: local SQLite schema and services store downloaded bank snapshots,
  local practice sessions, answers, local mistake attempts, and sync metadata.
- Done: backend exposes `download-package` and idempotent
  `/api/v2/offline/practice-sync`.
- Done: local banks, local bank detail, local practice, local result, and local
  history pages exist.
- Done: local practice follows the same four-question-type scoring direction:
  choice questions, blank exact matching with empty-string support, and short
  answer scored wrong for now.
- Remaining: harden offline sync UX, retry/failure states, local record cleanup,
  and broader manual QA under real disconnect/reconnect conditions.

### Done: Public Sharing and Bank Ownership Rules

Ordinary users can no longer directly turn a managed bank into a mutable public
bank. Public exposure happens through a separate static shared copy.

- Done: non-admin create/update/import/AI generation paths cannot directly
  create public source banks.
- Done: `POST /api/v2/banks/{bank_id}/share` creates a static public copy.
- Done: shared copies store `source_bank_id` and `is_shared_copy`.
- Done: shared copies copy current metadata, tags, questions, options, blanks,
  answers, and explanations at share time.
- Done: source edits do not mutate already shared copies.
- Done: ordinary users cannot manage shared copies; admins can manage all banks.
- Done: frontend exposes share actions in bank detail and bank list views.

Implementation notes:

- Remaining release cleanup: decide how to handle any old user-created mutable
  public banks before production data is considered stable.

### Done: Continue Practice from Bank

Users should be able to resume the latest unfinished practice session for a
bank directly from bank lists and bank detail.

- Done: backend can fetch the current user's latest resumable session for a
  bank.
- Done: "continue practice" resumes only `in_progress` sessions for the same
  `user_id + bank_id`.
- Done: if no resumable session exists, the action is hidden/disabled and
  normal "start practice" remains available.
- Done: exam sessions can be resumed if still `in_progress`; submitted sessions
  go to result, not continue.
- Done: bank list DTO exposes `resumable_session` in batch, so UI does not need
  per-row calls for the continue button.

### Done: Recent Practice Progress and Home Continue Entry

- Done: `QuestionBankV2Out.latest_practice_session` exposes the current user's
  latest practice progress for bank lists and bank detail.
- Done: `/api/v2/banks/recent-practice` returns recently practiced readable
  banks for the home page.
- Done: bank table/grid cards and home recent-practice cards can show progress
  bars and continue/start actions.
- Done: practice history shows progress based on answered/total or score.

### Done: Bank List Views and External Actions

The bank list component has two dense views, and key actions are visible outside
nested detail pages.

- Done: current table/list view remains available.
- Done: dense grid view exists.
- Done: both views expose start practice, continue practice, share bank, and
  delete actions.
- Done: selected view mode is persisted in local storage.
- Remaining polish: continue removing oversized card styling if it reappears
  during future frontend work.

### Done: Import and Question Management Fixes

- Done: AI new-bank and extension workflows allow multiple uploaded source
  files.
- Done: backend extracts each file and concatenates source text with file-name
  section markers.
- Done: AI workflow source snapshot preserves file names and combined text.
- Done: JSON import remains single-file.
- Done: question management uses `all=true` for owner/admin and loads all bank
  questions without visible pagination.
- Done: ordinary readable users cannot use `all=true`.
- Done: question editor disables adding options after 26 options, and backend
  schemas/JSON IO/draft confirm reject more than 26 options.
- Done: draft confirmation reads current persisted
  `ai_generation_draft_questions`, so edited/deleted draft questions are what
  get imported.

### Done: Four Question Types and Type Count Configuration

- Done: question model/API supports `single`, `multiple`, `blank`, and
  `short_answer`.
- Done: blank questions use `question_blanks` and `text_answers`.
- Done: AI prompts/schema/validator support all four question types.
- Done: AI generation and retry dialogs send `question_type_settings`.
- Done: fixed per-type AI generation quotas are validated and repaired.
- Done: practice setup dialog lets users choose enabled types and optional
  per-type limited counts.
- Done: answer/result/mistake/question-management views display the four
  question types.
- Done: RQ worker names are unique across multi-process workers.

### Partially Done: Frontend Polish Follow-Up

- Done: author filter uses a separate picker dialog like tags.
- Done: workflow table operation column has a compact action layout.
- Remaining: toast coverage is still uneven in some flows and should continue
  to use parsed backend error messages plus precise success messages.

### Done: Practice Stability, Blank Answers, and Session Record Control

- Done: direct session entry starts from the first question, while explicit
  continue/resume links use `?resume=1`.
- Done: submitted sessions redirect to result when opened through the practice
  route.
- Done: blank text answers are normalized to dense arrays so clearing any blank
  input does not create sparse-array crashes.
- Done: blank questions can be submitted with empty strings and score wrong
  instead of returning validation errors.
- Done: short-answer questions are stored but currently score wrong by default.
- Done: exam final submit supports `commit_drafts`, letting users decide whether
  cached unlocked answers count toward the result.
- Done: draft-save failures should be surfaced as toast messages without
  destroying local input or navigating away.
- Done: users can delete their own practice records from history.

### Done: Mistake Records as Concrete Wrong Attempts

- Done: `mistake_attempts` records concrete wrong attempts with
  `practice_session_id`, `practice_answer_id`, question snapshot, user answer
  snapshot, `wrong_at`, and resolution state.
- Done: new wrong answers write a concrete attempt and update the aggregate
  `mistake_records` summary/cache.
- Done: the bank mistake page uses concrete attempts and resolving one card only
  resolves that attempt.
- Done: mistake practice can be started from unresolved attempts for a bank or
  from unresolved attempts belonging to a specific practice record.
- Done: unfinished mistake-practice sessions are resumable by source context.
- Done: wrong-at timestamps are formatted through the shared local-time
  formatter.

### P1: AI Workflow Failure Visibility, Timeout Recovery, and Payload Debugging

Current state:

- `OpenAICompatibleClient` uses a long `timeout=1200`.
- Workflow status is advanced through runtime nodes, but there is no clear
  stale-processing recovery path if the model call or network dies outside the
  expected exception path.
- Failed workflow owner details show error text, but failed JSON payloads are
  not yet a first-class debug artifact.
- Very large source text can still reach lower layers and surface as a generic
  500.

Batch 1 should make failures observable and bounded:

- Add explicit source-size validation before creating workflows:
  - Validate total extracted text length after multi-file extraction.
  - Return 413 or 422 with a readable message such as "材料过长，请拆分文件或减少
    文本量".
  - Store limits in config, e.g. `AI_SOURCE_TEXT_MAX_CHARS`.
- Add workflow heartbeat/stale recovery:
  - Add `last_heartbeat_at` to `ai_generation_workflows` or update a step-level
    heartbeat before/after long calls.
  - Add a watchdog service/command that marks workflows stuck in
    `extracting/calling_model/validating/repairing` beyond a configured timeout
    as failed.
  - In RQ mode, configure job timeout and failure callback to call the same
    failure marker.
  - In BackgroundTasks mode, still fail gracefully on caught exceptions.
- Preserve failed JSON payload for the workflow owner:
  - When `validate_payload` fails, persist the raw/repaired payload into a
    structured debug field or failed step output.
  - Owner-only workflow detail should show a collapsible "模型返回 JSON" block.
  - Public bank workflow logs must stay redacted and only show failure summary.
- Make error messages actionable:
  - Include mode, model snapshot, base URL host, step name, and truncated error.
  - For validation failures, include question index/type/stem snippet/field.
  - For source-too-large, do not create a workflow stuck in pending/processing.

Tests for this batch:

- A source text over the limit returns a readable non-500 response.
- A simulated model timeout marks workflow/job failed and bank state correct.
- A validation failure stores failed JSON in owner detail, not public logs.
- A stale processing workflow is marked failed by the watchdog.

### P1: New Bank Creation Metadata and Tag Search

Current state:

- `GenerateBankDialog.vue` exposes title, description, tags, extra instruction,
  and AI description generation, but not the bank-level `ai_context`/background
  knowledge field.
- New-bank tags use an `el-select` with local selected options only; it does not
  actually search existing tags like the list filter dialog.
- Retry UI can update title/description, but product feedback says the
  description can disappear or fail to enter the retried bank.

Fix plan:

- Add "AI 背景知识 / 给 AI 看的题库描述" to new-bank creation:
  - For create-bank workflows, accept an optional `ai_context` form field.
  - Store it on the created `QuestionBank` before scheduling the workflow.
  - Keep `extra_instruction` separate: `ai_context` is durable bank context,
    extra instruction is per-workflow.
- Make retry preserve and submit description/context:
  - Retry form for `create_bank` should include title, description, and
    `ai_context`.
  - Backend retry should update the reused bank shell with all three fields.
  - If the original bank shell was deleted after cancel, copy
    `bank_title_snapshot`, description snapshot, and context snapshot into the
    new shell.
- Replace new-bank tag input with the shared tag selector:
  - Use the same remote tag search behavior as `TagFilterDialog`, while still
    allowing new tag names.
  - Normalize values through `features/tags/tagUtils.ts`.
  - Backend remains defensive: ignore `None/null/empty`, reject overlong tags.
- Keep JSON import metadata behavior:
  - JSON import remains single-file.
  - JSON `bank.title/description/tags` should still prefill the dialog.

Tests for this batch:

- Creating a workflow with `ai_context` stores it on the bank.
- Retrying a failed create-bank workflow keeps title, description, and context.
- Selecting an existing tag in the new-bank dialog submits its name, not `None`.
- Creating a new tag in the same control submits a clean string.

### P1: Bank List Ownership Defaults and Sharing Noise

Current state: `scope=mine` lists all banks owned by the user, including static
shared copies. Product feedback asks for "我的题库" to default-filter shared/public
copies out.

Plan:

- For `scope=mine`, default to source/manageable banks:
  - Exclude `is_shared_copy=true` by default.
  - Add an optional filter such as `include_shared=true` or a UI toggle "显示已分享
    副本".
  - Keep admin scope unaffected.
- Clarify visibility filters:
  - Ordinary source banks should generally be private under the sharing model.
  - Public banks in "我的题库" are likely shared copies or admin-managed banks, so
    label them clearly.
- Frontend:
  - "我的题库" default view should show editable source banks.
  - Public shared copies should be discoverable from public banks, user profile,
    or an explicit "我的分享" filter.

Tests:

- Owner with one source bank and one shared copy sees only source bank by
  default in `scope=mine`.
- `include_shared=true` returns both.
- Public and favorites scopes continue to include readable shared copies.

### P1: Question Rendering and Editing Details

Small but important authoring/display issues:

- Option content must allow newlines:
  - Use textarea or autosize input in question editors for option content.
  - Preserve `\n` in storage/import/export.
  - Render options through `MathText` with whitespace preserved, not collapsed.
- Blank placeholders should not show raw `{{1}}` to learners:
  - Store stems with `{{1}}`, `{{2}}`.
  - Render learner-facing stems by replacing placeholders with inline blank
    markers such as `____` or a small "空 1" pill.
  - Editor mode should still expose raw placeholders so authors can control
    placement.
- Keep answer-card section order as currently approved by product feedback; do
  not rework the current ordering unless explicitly requested again.

Tests:

- An option containing multiple lines renders with line breaks in practice,
  result, mistakes, question management, and draft preview.
- A blank stem stores `{{1}}` but practice/result render does not show braces.

### P2: Local Small-Model Fallback for Blank Matching

Goal: exact matching stays deterministic, but when a blank answer fails exact
matching, the backend can optionally ask a local small model whether the answer
is acceptable.

Rules:

- Only apply to `blank` questions.
- First pass remains exact matching after `strip()`.
- If exact matching fails and the feature is enabled, call a configured local
  model such as `qwen3.5:0.8b`.
- The model receives only:
  - blank label/index
  - stem
  - accepted answers for that blank
  - submitted answer
  - strict instruction to return JSON `{ "accepted": true|false, "reason": "" }`
- If local model accepts all failed blanks, mark the blank question correct.
- If local model errors, times out, or returns invalid JSON, fall back to wrong
  and include a small debug reason in result detail for the owner/user.
- Add config:
  - `BLANK_FALLBACK_GRADER_ENABLED=false`
  - `BLANK_FALLBACK_BASE_URL`
  - `BLANK_FALLBACK_MODEL`
  - `BLANK_FALLBACK_TIMEOUT_SECONDS=10`
- Do not call this fallback for exam final scoring until the deterministic path
  and user-facing messaging are stable.

Tests:

- Exact match succeeds without model call.
- Exact mismatch calls fallback when enabled.
- Fallback accept marks correct; fallback reject marks wrong.
- Timeout/invalid JSON marks wrong and does not break submission.

### P2: Records Retention and Audit

Practice record deletion exists. The remaining work is policy and observability:

- Decide whether deleted practice records should hard-delete linked concrete
  `mistake_attempts`, soft-delete them, or keep a redacted audit trail.
- Add audit entries for session deletion, workflow forced failure by watchdog,
  and local model fallback scoring if enabled.
- Document retention expectations for local SQLite records versus synced server
  records.

## Verification Commands

Use these before reporting work as complete:

```bash
cd backend
.venv/bin/python -m compileall app
.venv/bin/python -m pytest tests -q
.venv/bin/alembic upgrade head

cd ../frontend
npm run build
npm run tauri:build
```
