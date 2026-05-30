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

- Question banks are user-owned resources. Public banks are readable by other
  users, but management stays with the owner or admin.
- Mistakes are currently scoped by `user_id + bank_id + question_id`, but the
  next mistake-system revision should move user-facing review to concrete wrong
  answer records so mistakes can be resumed from a specific practice history
  item.
- AI output is never inserted directly into formal questions. It goes through
  extraction, model generation/parsing, validation, optional repair, draft
  creation, user editing, and explicit confirmation.
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

Frontend is Vue 3 + TypeScript + Vite + Element Plus + Tailwind utilities.

Current UI direction:

- Avoid large SaaS-card layouts, heavy shadows, gradients, large rounded cards,
  and excess whitespace.
- Prefer dense desktop-style layouts: tables, thin borders, dividers, compact
  controls, and plain buttons.
- Use Element Plus components as the UI baseline.

Main frontend structure:

- `frontend/src/api/v2`: typed v2 API wrappers.
- `frontend/src/pages`: route pages.
- `frontend/src/components`: shared UI components including bank creation,
  workflow table, MathText, practice controls, avatar/sidebar.
- `frontend/src/stores/auth.ts`: auth state, token refresh, current user.

Notable pages:

- `/banks`, `/banks/public`, `/favorites`: bank lists with query-friendly
  filters.
- `/banks/:bankId`: bank detail, practice/export/mistakes/workflow log/actions.
- `/banks/:bankId/workflows`: redacted bank workflow log for all readable users.
- `/banks/generation-jobs`: current user's full workflow queue.
- `/ai-generation/workflows/:workflowId/draft`: editable AI draft confirmation.
- `/practice/session/:sessionId`, `/practice/result/:sessionId`: practice flow.

## Data Model Highlights

Important tables:

- `users`: auth/profile/admin state, email verification timestamp.
- `email_auth_tokens`: hashed email verification and password reset tokens.
- `user_ai_provider_configs`: user-owned OpenAI-compatible configs, encrypted
  API keys, response format preference.
- `question_banks`: owner, visibility, desired visibility, stats, AI context,
  last model snapshots.
- `question_bank_tags` and `question_bank_tag_links`: global tag table and
  many-to-many bank links.
- `questions`, `question_options`, and `question_blanks`: formal bank content
  for single choice, multiple choice, blank, and short answer questions.
- `practice_sessions`, `practice_session_questions`, `practice_answers`:
  practice recovery, draft answer saving, submission, scoring.
- `mistake_records`: bank-scoped mistake records.
- `ai_generation_workflows`: AI workflow source of truth.
- `ai_generation_workflow_steps`: node logs for extract/build/generate/validate/
  repair/write/fail/confirm.
- `ai_generation_drafts` and `ai_generation_draft_questions`: editable draft
  before formal import.
- `import_jobs`: thin queue/compat projection for workflows.

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
- Public/private visibility, favorites for both public and own private banks.
- Bank tags with independent tag table and multi-tag OR filtering by numeric ID.
- JSON import/export.
- Question CRUD with single/multiple/blank/short-answer validation.
- Owner/admin can manage all questions; non-owner public readers can view/export/
  practice/mistakes but cannot manage.

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
- Users can leave and resume in-progress sessions. The current practice page
  resumes at the first unanswered question; product feedback now asks for newly
  entered sessions to start at the first question unless the user explicitly
  chooses a continue/resume flow.
- Result page includes question content, options, user selection, correct labels,
  explanation, and unanswered state.
- Mistake page is bank-scoped and displays full question detail, correct labels,
  explanation, wrong count, and last wrong time. The current record shape is
  aggregated by question, which makes some "mark resolved" and review-from-
  history flows ambiguous.

### Frontend UX

- Element Plus based dense desktop UI.
- KaTeX formula rendering through `MathText`.
- WASD/arrow navigation in practice pages.
- Generation polling for unstable workflow/bank states.
- Shared workflow table for generation queue and bank workflow logs.

## Known Issues and Technical Debt

- KaTeX rendering has been renamed to `frontend/src/utils/mathText.ts`.
- `features/questions` now owns the shared question table/editor/option editor
  used by question management and AI draft confirmation.
- `features/tags` now owns tag normalization so tag submission filters
  `null`/empty/`none` before sending to the backend.
- Workflow list DTOs now use batch aggregation for jobs, drafts, imported
  counts, and retry child links; public bank logs remain redacted.
- The old top-level `backend/app/services` package has been removed:
  AI compatibility helpers live in `domains/ai_generation/facade.py`, tag
  helpers live in `domains/question_banks/tags.py`, and SMTP delivery lives in
  `infrastructure/email.py`.
- AI workflow execution supports FastAPI `BackgroundTasks` for local development
  and RQ + Redis for deployment. RQ worker concurrency can be increased with
  `AI_WORKFLOW_WORKER_COUNT` or Docker Compose `--scale worker=N`.
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

### P1: Practice Stability, Blank Answers, and Session Record Control

These issues were reported after the four-question-type work and should be
fixed before expanding scoring logic further.

Already done:

- Submitted sessions redirect to result when opened from the practice route.
- Partial blank draft saving is supported; formal blank submission still needs
  the white-paper behavior below.

Observed code touchpoints:

- `frontend/src/components/practice/QuestionCard.vue`: blank inputs are rendered
  directly from `textAnswers[index]` and emit a copied sparse array.
- `frontend/src/composables/usePracticeSession.ts`: `load()` jumps to the first
  unanswered question; draft-save errors currently bubble up from navigation
  helpers and can interrupt the page.
- `backend/app/domains/practice/services.py`: blank submit requires answer count
  matching blanks, short answers are currently treated as correct when non-empty,
  and session submit does not distinguish cached drafts from locked/submitted
  answers.

Batch 1 should handle pure practice correctness and UX:

- Fix the "second blank backspace can crash" class of bugs:
  - Always initialize blank `text_answers` to a dense array with one string per
    blank when questions load.
  - In `setTextAnswers`, clone to the question blank count and normalize
    `undefined/null` to `""`.
  - Add frontend tests or component-level smoke coverage for clearing the second
    blank, clearing the first blank, and switching questions after clearing.
- Allow blank questions to be submitted blank:
  - Backend `answer_question` should accept `blank` text answers with empty
    strings as long as the number of answers matches the number of blanks.
  - Empty blank answers score wrong, not validation error.
  - Frontend submit button for blank questions should be enabled even when all
    blank inputs are empty.
  - Exam final submit must treat uncommitted blank fields according to the new
    "submit cached drafts?" choice described below.
- Treat short-answer questions as wrong for now:
  - Change `_is_text_correct()` so `short_answer` returns `False`.
  - Keep storing the submitted text and explanation/rubric.
  - Do not call any AI grader yet; that belongs to a later scoring feature.
- Start practice sessions at the first question by default:
  - `load()` should set `currentIndex = 0` for direct session entry.
  - The bank "continue practice" entry can pass a query flag such as
    `?resume=1` if the desired behavior is to jump to the first unanswered
    question.
  - Keep result redirects for submitted sessions.
- Make draft-save failures non-destructive:
  - Navigation should not kick the user out because a draft save returned 422.
  - Show a toast with question number and reason, keep the user on the current
    question, and keep local input intact.
  - Add backend error details for invalid draft payloads so the toast is not just
    "请求参数校验失败".
- Final submit should ask what to do with cached unlocked answers:
  - Add an `include_drafts` or `commit_cached_answers` boolean to
    `POST /api/v2/practice/sessions/{id}/submit`.
  - If the user chooses yes, save and submit current local answers before
    scoring.
  - If the user chooses no, only already-submitted/locked answers count; cached
    local input is ignored and appears as unanswered.
  - The confirmation dialog should state this plainly because it changes score.
- Allow users to delete their own practice records:
  - Add `DELETE /api/v2/practice/sessions/{session_id}` for the owner.
  - Deleting a session should delete session questions and answers; it should
    not delete formal questions or bank-level mistake records unless the new
    mistake-record design below explicitly links them.
  - Frontend history page should add a compact delete action with confirmation.

Tests for this batch:

- Blank answer with `["", ""]` submits and scores wrong without 422.
- Clearing the second blank then switching questions preserves page state.
- Short-answer non-empty submit is stored and scored wrong.
- Directly opening `/practice/session/:id` lands on question 1; continuing with
  `resume=1` can land on the first unanswered question.
- Submitted sessions redirect to result; deleted sessions are no longer visible
  in history.

### P1: Mistake Records as Concrete Wrong Attempts

Current state: `mistake_records` aggregates by `user_id + bank_id + question_id`.
This makes "错题消失不了了" hard to reason about because resolving one question
does not map to a specific practice history item, and new wrong attempts reset
the same aggregate record.

Target model:

- Keep a lightweight aggregate for counters if useful, but add a concrete wrong
  attempt table, for example `mistake_attempts`:
  - `id`
  - `user_id`
  - `bank_id`
  - `question_id`
  - `practice_session_id`
  - `practice_answer_id`
  - `question_snapshot_json`
  - `user_answer_json`
  - `is_resolved`
  - `wrong_at`
  - `resolved_at`
- A wrong attempt belongs to one practice answer/result row.
- Mistake lists should default to unresolved concrete attempts, not only the
  aggregate question row.
- "Mark mastered/resolved" should resolve the selected wrong attempt, or all
  attempts for that question only when the UI explicitly says so.
- Mistake practice should be creatable from:
  - a bank's unresolved mistakes
  - a specific practice record's wrong attempts
  - the latest unfinished mistake-practice session for the same source context
- Mistake practice itself should be resumable through the same session recovery
  mechanism as normal practice.
- Time display:
  - Store all timestamps as UTC-aware datetimes.
  - Frontend should format `wrong_at/last_wrong_at` with one shared local-time
    formatter, not raw ISO strings.

Migration path:

- Add `mistake_attempts`.
- On new wrong answers, write both the aggregate row and the concrete attempt.
- Keep existing bank mistake page temporarily backed by aggregate rows, but add
  a new endpoint for concrete attempts.
- Move the UI to concrete attempts.
- Once stable, decide whether aggregate `mistake_records` remains as a cached
  summary or becomes rebuildable derived data.

Tests for this batch:

- User A and user B wrong attempts in the same public bank are isolated.
- Resolving one wrong attempt removes that card from unresolved view.
- Starting mistake practice from a history record includes only that record's
  wrong questions.
- Resuming an unfinished mistake-practice session returns the same session.
- Wrong-at timestamps render in browser local time.

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

### P2: Records, Deletion, and Audit

After the P1 practice/mistake fixes, add user-level record controls:

- Users can delete their own practice history records.
- Deleting a practice record should:
  - remove `practice_session_questions` and `practice_answers`
  - either cascade linked concrete `mistake_attempts` or mark them deleted,
    depending on whether the mistake page should still show historical wrongs
  - not modify the formal question bank
- Add audit entries for:
  - session deletion
  - workflow forced failure by watchdog
  - local model fallback scoring if enabled

Keep this separate from P1 because it touches data retention semantics.

## Verification Commands

Use these before reporting work as complete:

```bash
cd backend
.venv/bin/python -m compileall app
.venv/bin/python -m pytest tests -q
.venv/bin/alembic upgrade head

cd ../frontend
npm run build
```
