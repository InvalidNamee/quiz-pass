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
- Mistakes are scoped by `user_id + bank_id + question_id`.
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
- `questions` and `question_options`: formal bank content.
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
- Question CRUD with single/multiple answer validation.
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
- Users can leave and resume in-progress sessions.
- Result page includes question content, options, user selection, correct labels,
  explanation, and unanswered state.
- Mistake page is bank-scoped and displays full question detail, correct labels,
  explanation, wrong count, and last wrong time.

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
- Background work still uses FastAPI `BackgroundTasks`. For production-scale
  long-running jobs, introduce a queue such as RQ/Celery/Arq plus Redis.
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

### P2: AI Workflow Operations

- Add workflow detail drawer/page for owner: input snapshot, context flags, step
  list, model info, repair attempts, and full error message.
- Add retry from draft-ready or cancelled only if product rules require it.
- Add optional manual “re-run repair” for invalid draft questions.

### P2: Production Readiness

- Move long-running AI workflows to a real queue.
- Add job cancellation checks inside runtime nodes.
- Add structured logging and minimal audit events for admin operations,
  workflow confirmation, and bank deletion.
- Add deployment docs for MySQL, SMTP, CORS, encryption key, and reverse proxy.

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
