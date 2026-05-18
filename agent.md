# Quiz Pass Agent Architecture Plan

> 本文档根据 `prompt.md` 制定项目架构与实施边界。当前阶段只做架构决策，不开始编写项目代码。

## 1. 产品定位

Quiz Pass 是一个面向个人和小团队的 AI 刷题平台。系统允许用户创建、导入、维护题库，并通过上传文档自动生成选择题。核心体验不是“题库展示站”，而是一个高频使用的练习工具：创建题库、生成题目、练习、复盘、导出，流程应短、清楚、可恢复。

## 2. 总体架构

采用前后端分离架构：

- 前端：Vue 3 + TypeScript + Vite 8 + Tailwind CSS 4
- 后端：Python FastAPI + SQLAlchemy
- 数据库：MySQL
- 认证：JWT access token + refresh token
- AI：用户自定义 OpenAI 兼容 Chat Completions API 配置
- 文件处理：后端接收上传文件，抽取文本后调用 AI 生成题目

推荐仓库结构：

```text
Quiz/
  agent.md
  README.md
  docker-compose.yml
  .env.example
  frontend/
    package.json
    vite.config.ts
    tsconfig.json
    src/
      app/
      pages/
      features/
      components/
      layouts/
      router/
      stores/
      api/
      types/
      utils/
      styles/
  backend/
    pyproject.toml
    alembic.ini
    app/
      main.py
      core/
      db/
      models/
      schemas/
      api/
      services/
      repositories/
      tasks/
      utils/
    alembic/
    tests/
```

## 3. 架构原则

1. 前端负责交互状态与展示，不承载业务真相。
2. 后端负责权限、题目判分、练习记录、错题归档、AI 生成流程。
3. 数据库保存结构化题库、练习记录和生成任务元数据；上传原文件默认不长期保存，除非后续产品明确需要。
4. AI 输出必须经过后端校验和规范化，不允许直接入库。
5. 所有用户资源默认私有；公开题库需要显式发布。
6. 管理员权限只扩展管理能力，不绕过审计与数据模型约束。

## 4. 前端架构

### 4.1 页面划分

```text
/login
/register
/dashboard
/profile
/users/:userId
/banks
/banks/new
/banks/:bankId
/banks/:bankId/edit
/banks/:bankId/questions
/banks/:bankId/import
/banks/:bankId/generate
/practice/setup
/practice/session/:sessionId
/practice/result/:sessionId
/banks/:bankId/mistakes
/history
/settings/prompt
/settings/ai-providers
/admin/users
```

### 4.2 模块划分

- `app/`：应用启动、全局 provider、错误边界。
- `pages/`：路由页面，尽量只组合 feature 组件。
- `features/auth/`：登录、注册、token 刷新、用户状态。
- `features/users/`：我的资料、其他用户公开资料、用户公开题库入口。
- `features/question-banks/`：题库 CRUD、导入导出、公开/私有状态、题库收藏。
- `features/questions/`：题目编辑、选项维护、答案设置、分页筛选。
- `features/ai-generation/`：文件上传、AI 配置选择、Prompt 预览、生成中题库恢复、生成任务状态、生成结果查看。
- `features/ai-providers/`：用户 AI 配置管理，包括 `api_base_url`、`api_key`、`model`。
- `features/practice/`：练习设置、答题会话、判分、模拟考试。
- `features/mistakes/`：题库下的错题列表、分页筛选、错题练习、错题导出。
- `features/history/`：练习历史分页筛选与统计。
- `features/admin/`：用户管理。
- `components/`：跨业务通用 UI。
- `api/`：HTTP client、请求拦截、API wrapper。
- `stores/`：Pinia stores，主要保存认证、用户设置和当前练习轻状态。

### 4.3 UI 风格

这是一个高频工具型应用，应使用安静、清晰、密度适中的后台式界面：

- 左侧主导航 + 顶部用户区域。
- 题库、错题、历史使用表格或紧凑列表。
- 题库、题目、错题、历史列表都应提供分页、搜索框和基础筛选控件。
- 题库列表和题库详情显示收藏数；登录用户在有读取权限的题库上看到收藏/取消收藏按钮和自己的收藏状态。
- 用户自己的题库列表应显示生成中、生成失败、生成完成等状态；页面刷新后仍能看到正在生成的题库和任务进度入口。
- 练习页突出题干、选项、进度和提交按钮，减少装饰。
- AI 生成页使用分步骤流程：上传文件、配置参数、生成中、生成完成后查看结果。
- 移动端保留核心刷题体验，管理类页面可做响应式降级。

### 4.4 状态管理

- 服务端数据使用 API 请求封装，后续可引入 TanStack Query for Vue，但初版可用组合式函数管理。
- Pinia 只保存：
  - 当前用户与 token 状态
  - 全局偏好设置
  - 当前选择的 AI 配置 ID，不保存 API key 明文
  - 当前练习过程中的临时答题状态
- 练习提交以后，以后端记录为准。

## 5. 后端架构

### 5.1 目录职责

```text
backend/app/
  main.py                  # FastAPI 应用入口
  core/
    config.py              # 环境变量与配置
    security.py            # 密码哈希、JWT、权限工具
    errors.py              # 统一异常
  db/
    session.py             # SQLAlchemy session
    base.py                # declarative base
  models/                  # SQLAlchemy ORM
  schemas/                 # Pydantic 请求/响应模型
  api/
    deps.py                # 认证、权限、DB 依赖
    v1/
      router.py
      auth.py
      users.py
      ai_provider_configs.py
      question_banks.py
      questions.py
      imports.py
      ai_generation.py
      practice.py
      mistakes.py
      history.py
      admin.py
  repositories/            # 数据访问
  services/                # 业务逻辑
  tasks/                   # 后台任务，初版可用 FastAPI BackgroundTasks
  utils/
    document_extractors.py # txt/docx/pdf 文本抽取
    json_io.py             # JSON 导入导出
```

### 5.2 分层约定

- API 层只做参数校验、依赖注入、响应组装。
- Service 层承载业务流程，例如创建练习、判分、AI 生成结果校验。
- Repository 层封装数据库查询，避免 SQL 分散在 API 中。
- Model 层只表达数据结构和关系，避免放复杂业务逻辑。
- Schema 层区分 request、response、internal DTO。

## 6. 数据库设计

### 6.1 核心表

#### users

- `id`
- `email`
- `username`
- `display_name`
- `avatar_url`
- `bio`
- `avatar_source`：`manual` / `qq_email` / `default`
- `password_hash`
- `role`：`user` / `admin`
- `is_active`
- `created_at`
- `updated_at`

用户信息分为私有信息和公开基础信息。`email`、`role`、`is_active` 只在用户本人或管理员上下文返回；其他用户页面只返回 `id`、`username`、`display_name`、`avatar_url`、`bio`、`created_at` 以及公开题库统计。

头像策略：

- 用户可以手动设置 `avatar_url`。
- 如果用户邮箱是 QQ 邮箱，例如 `123456@qq.com`，且用户选择 `avatar_source = qq_email`，后端可根据 QQ 号生成头像 URL。
- QQ 邮箱头像生成建议使用独立 helper，例如 `build_qq_avatar_url(email)`，只接受当前登录用户自己的邮箱。
- 公开用户信息只返回最终 `avatar_url`，不返回邮箱；前端不能根据公开资料反推出 QQ 邮箱。
- 如果没有手动头像，也没有启用 QQ 邮箱头像，则使用默认头像。

#### user_prompt_templates

- `id`
- `user_id`
- `name`
- `content`
- `is_default`
- `created_at`
- `updated_at`

每个用户可维护多个模板，但初版 UI 可以只暴露一个默认模板。

#### user_ai_provider_configs

- `id`
- `user_id`
- `name`
- `api_base_url`
- `api_key_encrypted`
- `model`
- `is_default`
- `is_active`
- `last_used_at`
- `created_at`
- `updated_at`

每个用户可以配置多个 OpenAI 兼容 API。`api_key` 只能在创建或更新时由前端提交，后端必须加密后保存；列表和详情接口永远不返回明文 key，只返回是否已配置 key。

#### question_banks

- `id`
- `owner_id`
- `title`
- `description`
- `visibility`：`private` / `public`
- `desired_visibility`：`private` / `public`，生成成功后的目标可见性
- `generation_status`：`none` / `pending` / `processing` / `succeeded` / `failed`
- `active_generation_job_id`：可空，当前正在生成的任务
- `question_count`
- `favorite_count`
- `ai_provider_config_id`：可空，最近一次用于该题库 AI 生成的用户配置
- `ai_model_name`：可空，题库最近一次 AI 生成使用的 model 快照
- `ai_base_url_host`：可空，仅保存 host 或脱敏 base url，便于用户识别来源
- `created_at`
- `updated_at`

#### question_bank_favorites

- `id`
- `user_id`
- `bank_id`
- `created_at`

用户可以收藏自己有读取权限的题库，包括公开题库和自己的私有题库。`question_banks.favorite_count` 保存冗余计数，便于题库列表和详情页直接展示收藏数。收藏只表达用户偏好，不授予额外读取或编辑权限。

#### questions

- `id`
- `bank_id`
- `type`：`single` / `multiple`
- `stem`
- `explanation`
- `difficulty`：可选，`easy` / `medium` / `hard`
- `source`：`manual` / `json_import` / `ai_generated`
- `generated_model`：可空，AI 生成题目时使用的 model 快照
- `created_at`
- `updated_at`

#### question_options

- `id`
- `question_id`
- `label`
- `content`
- `is_correct`
- `sort_order`

答案由 `question_options.is_correct` 表达，避免额外答案字符串和选项不同步。

#### import_jobs

- `id`
- `user_id`
- `bank_id`
- `type`：`json` / `document_ai`
- `status`：`pending` / `processing` / `succeeded` / `failed`
- `desired_visibility`：`private` / `public`，任务成功后题库应切换到的可见性
- `file_name`
- `ai_provider_config_id`：可空，AI 导入时选择的用户配置
- `ai_base_url_snapshot`：可空，脱敏后的 base url 快照
- `ai_model_snapshot`：可空，当次生成使用的 model 快照
- `error_message`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

#### practice_sessions

- `id`
- `user_id`
- `bank_id`
- `mode`：`practice` / `exam` / `mistake_review`
- `status`：`in_progress` / `submitted` / `abandoned`
- `total_questions`
- `correct_count`
- `score`
- `started_at`
- `submitted_at`

#### practice_answers

- `id`
- `session_id`
- `question_id`
- `selected_option_ids`：JSON
- `is_correct`
- `answered_at`

#### mistake_records

- `id`
- `user_id`
- `bank_id`
- `question_id`
- `wrong_count`
- `last_wrong_at`
- `resolved_at`

错题由 `user_id + bank_id + question_id` 共同决定。同一道题如果出现在不同题库中，或用户在不同题库场景下练习，应分别记录错题状态。这样错题复习始终发生在某个题库上下文中，而不是用户全局错题池。

### 6.2 关系与约束

- `users.email` 唯一。
- `user_ai_provider_configs.user_id` 指向 `users.id`。
- `question_banks.owner_id` 指向 `users.id`。
- `question_banks.ai_provider_config_id` 指向 `user_ai_provider_configs.id`，可空。
- `question_banks.active_generation_job_id` 指向 `import_jobs.id`，可空。
- `question_bank_favorites.user_id` 指向 `users.id`。
- `question_bank_favorites.bank_id` 指向 `question_banks.id`。
- `question_bank_favorites` 对 `(user_id, bank_id)` 建唯一索引。
- `questions.bank_id` 指向 `question_banks.id`。
- `question_options.question_id` 指向 `questions.id`。
- `mistake_records.bank_id` 指向 `question_banks.id`。
- `mistake_records.question_id` 指向 `questions.id`。
- `mistake_records` 对 `(user_id, bank_id, question_id)` 建唯一索引。
- 应用层必须保证 `mistake_records.question_id` 所属题库等于 `mistake_records.bank_id`。
- 同一用户只能有一个默认 AI 配置，应用层保证，数据库可用条件唯一索引增强。
- 题库查询常用索引：
  - `(owner_id, updated_at)`
  - `(owner_id, generation_status, updated_at)`
  - `(visibility, updated_at)`
  - `(visibility, favorite_count)`
  - `(owner_id, ai_model_name)`
  - `(user_id, created_at)` for favorites
  - `(bank_id, created_at)` for questions
  - `(user_id, bank_id, last_wrong_at)` for mistakes

## 7. API 设计

统一前缀：`/api/v1`

### 7.0 Pagination and Filtering

所有列表接口使用统一分页响应：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "total_pages": 0
}
```

分页规则：

- `page` 从 1 开始。
- `page_size` 默认 20，最大 100。
- `sort` 使用白名单字段，例如 `created_at_desc`、`updated_at_desc`、`favorite_count_desc`、`score_desc`。
- `keyword` 做基础模糊搜索；题库检索匹配 `title`、`description`，题目和错题检索匹配题干。
- 后端必须对筛选字段做白名单校验，不能把前端传入值直接拼接为 SQL。

### 7.1 Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`

### 7.2 Users

- `GET /users/me`
- `PATCH /users/me`
- `GET /users/{user_id}`
- `GET /users/{user_id}/public-question-banks`
- `GET /users/me/prompt-templates`
- `POST /users/me/prompt-templates`
- `PATCH /users/me/prompt-templates/{template_id}`
- `DELETE /users/me/prompt-templates/{template_id}`
- `GET /users/me/ai-provider-configs`
- `POST /users/me/ai-provider-configs`
- `GET /users/me/ai-provider-configs/{config_id}`
- `PATCH /users/me/ai-provider-configs/{config_id}`
- `DELETE /users/me/ai-provider-configs/{config_id}`
- `POST /users/me/ai-provider-configs/{config_id}/set-default`
- `POST /users/me/ai-provider-configs/{config_id}/test`

用户响应模型约定：

- `GET /users/me` 返回 `UserMe`：包含 `id`、`email`、`username`、`display_name`、`avatar_url`、`avatar_source`、`bio`、`role`、`is_active`、`created_at`、`updated_at`。
- `GET /users/{user_id}` 返回 `UserPublic`：包含 `id`、`username`、`display_name`、`avatar_url`、`bio`、`created_at`、`public_bank_count`，不包含邮箱和权限字段。
- `GET /users/{user_id}/public-question-banks` 只返回该用户已发布的公开题库，并支持统一分页参数与 `keyword`、`sort`。
- `PATCH /users/me` 可更新 `display_name`、`avatar_url`、`avatar_source`、`bio`；当 `avatar_source = qq_email` 时，后端根据当前登录用户邮箱生成头像。

### 7.3 Question Banks

- `GET /question-banks`
- `GET /question-banks/public`
- `GET /question-banks/favorites`
- `POST /question-banks`
- `GET /question-banks/{bank_id}`
- `PATCH /question-banks/{bank_id}`
- `DELETE /question-banks/{bank_id}`
- `POST /question-banks/{bank_id}/publish`
- `POST /question-banks/{bank_id}/unpublish`
- `POST /question-banks/{bank_id}/favorite`
- `DELETE /question-banks/{bank_id}/favorite`
- `GET /question-banks/{bank_id}/export`
- `POST /question-banks/import-json`

题库列表支持分页、检索和基础筛选：

- 通用分页参数：`page`、`page_size`，默认 `page = 1`、`page_size = 20`，最大 `page_size = 100`。
- `GET /question-banks` 查询当前用户可管理的题库，支持 `keyword`、`visibility`、`generation_status`、`ai_model_name`、`created_from`、`created_to`、`sort`。
- `GET /question-banks/public` 查询公开且生成完成的题库，支持 `keyword`、`owner_id`、`ai_model_name`、`min_question_count`、`sort`，可按 `favorite_count` 排序。
- `GET /question-banks/favorites` 查询当前用户收藏且仍有读取权限的题库，支持 `keyword`、`owner_id`、`visibility`、`sort`。
- 题库列表项返回 `favorite_count`；登录用户可访问的题库列表和详情页额外返回当前用户的 `is_favorited`。

### 7.4 Questions

- `GET /question-banks/{bank_id}/questions`
- `POST /question-banks/{bank_id}/questions`
- `GET /questions/{question_id}`
- `PATCH /questions/{question_id}`
- `DELETE /questions/{question_id}`

题目列表支持 `page`、`page_size`、`keyword`、`type`、`difficulty`、`source`、`generated_model`、`sort`。

### 7.5 AI Generation

- `POST /ai-generation/question-bank-jobs`
- `POST /question-banks/{bank_id}/ai-generation/jobs`
- `GET /ai-generation/jobs`
- `GET /ai-generation/jobs/{job_id}`
- `POST /ai-generation/jobs/{job_id}/confirm`
- `POST /ai-generation/jobs/{job_id}/cancel`

`POST /ai-generation/question-bank-jobs` 用于从文档直接创建一个生成中的题库。后端应先创建 `question_banks` 记录，并设置 `visibility = private`、`desired_visibility = 用户选择值`、`generation_status = pending`，再创建生成任务并返回 `bank_id` 和 `job_id`。这样即使用户刷新页面，生成中的题库和任务也能通过接口恢复。

`GET /ai-generation/jobs` 查询当前用户自己的生成任务，支持 `page`、`page_size`、`bank_id`、`status`、`created_from`、`created_to`、`sort`，用于刷新后恢复生成中列表。

“生成型题库”任务成功后，后端应自动将校验通过的题目写入该题库，并按 `desired_visibility` 更新题库：如果用户预设为 `public`，则将题库切为公开；如果预设为 `private`，则保持私有。`confirm` 接口主要用于后续“生成到已有题库前先预览确认”的增强路径，首版生成新题库不依赖前端确认才能入库。

### 7.6 Practice

- `POST /practice/sessions`
- `GET /practice/sessions/{session_id}`
- `POST /practice/sessions/{session_id}/answers`
- `POST /practice/sessions/{session_id}/submit`
- `GET /practice/sessions/{session_id}/result`

### 7.7 Mistakes and History

- `GET /question-banks/{bank_id}/mistakes`
- `POST /question-banks/{bank_id}/mistakes/practice-sessions`
- `POST /question-banks/{bank_id}/mistakes/{question_id}/resolve`
- `GET /history/sessions`
- `GET /history/stats`

记录类列表支持分页和基础筛选：

- `GET /question-banks/{bank_id}/mistakes` 支持 `page`、`page_size`、`keyword`、`resolved`、`wrong_count_min`、`last_wrong_from`、`last_wrong_to`、`sort`。
- `GET /history/sessions` 支持 `page`、`page_size`、`bank_id`、`mode`、`status`、`started_from`、`started_to`、`score_min`、`score_max`、`sort`。

### 7.8 Admin

- `GET /admin/users`
- `PATCH /admin/users/{user_id}`
- `DELETE /admin/users/{user_id}`

管理员用户列表支持统一分页和基础筛选：

- `GET /admin/users` 支持 `page`、`page_size`、`keyword`、`role`、`is_active`、`created_from`、`created_to`、`sort`。
- `keyword` 匹配 `email`、`username`、`display_name`。
- `sort` 白名单包括 `created_at_desc`、`created_at_asc`、`updated_at_desc`、`username_asc`。

## 8. AI 生成题目流程

### 8.1 输入

- 文件类型：`.txt`、`.docx`、`.pdf`
- 参数：
  - 题目数量
  - 单选/多选比例，可选
  - 难度，可选
  - 用户 Prompt 模板
  - 用户 AI 配置 ID，包含 `api_base_url`、`api_key`、`model`

生成任务必须显式选择一个当前用户拥有且启用的 AI 配置；如果请求未传入配置 ID，则使用用户默认 AI 配置。用户没有可用配置时，后端应返回可读错误，引导用户先添加 AI 配置。

生成题库时还需要传入题库元信息：

- `title`
- `description`
- `desired_visibility`：用户希望生成成功后的题库可见性

无论用户选择公开还是私有，生成中的题库都必须先以 `visibility = private` 保存，避免半成品被其他用户读取。

### 8.2 文档解析

- txt：按 UTF-8 读取，必要时检测编码作为后续增强。
- docx：使用 `python-docx` 抽取段落文本。
- pdf：使用 `pypdf` 或 `pdfplumber` 抽取文本。
- 初版限制文件大小和抽取文本长度，防止超出模型上下文。

### 8.3 Prompt 结构

系统 Prompt 负责固定输出规范：

- 只能输出 JSON。
- 每题必须包含题干、类型、选项、正确答案、解析。
- 单选题只能有一个正确选项，多选题至少两个正确选项。
- 选项数量默认 4 个。

用户 Prompt 模板作为补充约束，不允许覆盖 JSON 输出格式要求。

### 8.4 AI 配置使用规则

- `api_base_url`、`api_key`、`model` 来自 `user_ai_provider_configs`，不再使用全局 OpenAI key。
- 后端调用 AI 前必须校验配置归属当前用户且 `is_active = true`。
- 生成任务创建后，将 `model` 和脱敏后的 `api_base_url` 写入 `import_jobs` 快照。
- 生成型题库写入题目成功后，将当次 `model` 写入 `question_banks.ai_model_name` 和每道 AI 题目的 `questions.generated_model`。
- 题库展示应显示最近一次 AI 生成使用的 model；如果题库完全由手动或 JSON 导入创建，则显示为空或 `未使用 AI`。
- 如果同一个题库多次使用不同 model 生成，题库级 `ai_model_name` 表示最近一次使用的 model，题目级 `generated_model` 保留每道题的真实来源。

### 8.5 生成中题库状态机

题库生成可能持续较长时间，必须以数据库状态为准，而不是依赖前端页面生命周期。

状态流转：

```text
question_banks.generation_status = pending
  -> processing
  -> succeeded / failed
```

流程规则：

- 创建生成型题库时，立即持久化 `question_banks` 和 `import_jobs`，并返回 `bank_id`、`job_id`。
- 生成中题库必须保持 `visibility = private`，只对 `owner_id` 用户可见。
- 前端刷新后通过 `GET /question-banks?generation_status=pending|processing` 或 `GET /ai-generation/jobs?status=pending|processing` 恢复生成中题库。
- AI 生成成功后，后端先将规范化题目写入题库，再将 `generation_status` 更新为 `succeeded`。
- 如果 `desired_visibility = public`，只有在题目写入成功并且题库不为空后，才把 `visibility` 更新为 `public`。
- 如果 `desired_visibility = private`，生成成功后仍保持私有。
- 生成失败时，题库保持私有，`generation_status = failed`，`import_jobs.error_message` 保存可读错误。用户可以删除该题库，或后续通过重试任务继续生成。
- 任务取消时，题库保持私有并标记失败或取消状态；如果需要更细粒度，后续可把 `cancelled` 加入状态枚举。

### 8.6 输出格式

```json
{
  "questions": [
    {
      "type": "single",
      "stem": "题干",
      "options": [
        {"label": "A", "content": "选项 A", "is_correct": true},
        {"label": "B", "content": "选项 B", "is_correct": false}
      ],
      "explanation": "解析",
      "difficulty": "medium"
    }
  ]
}
```

### 8.7 校验规则

- 必须是合法 JSON。
- `questions` 必须非空。
- `type` 只能为 `single` 或 `multiple`。
- 每题至少 2 个选项，推荐 4 个。
- 单选题正确项数量必须为 1。
- 多选题正确项数量必须大于等于 2。
- 题干和选项内容不能为空。
- 校验失败时 job 标记为 failed，并保存可读错误。

## 9. JSON 导入导出格式

导出格式应与 AI 生成格式兼容，并包含题库元信息：

```json
{
  "version": 1,
  "bank": {
    "title": "题库名称",
    "description": "题库描述"
  },
  "questions": []
}
```

导入策略：

- 支持创建新题库导入。
- 支持导入到已有题库。
- 不做复杂去重，初版只按题干完全相同给出提示或跳过策略。

## 10. 练习与判分

### 10.1 练习模式

- 普通练习：答一题可立即显示对错与解析。
- 模拟考试：全部答完后统一判分。
- 错题练习：题目来源为当前用户在指定题库下的错题记录。

### 10.2 随机策略

- 题目顺序可随机。
- 选项顺序可随机。
- 后端创建 session 时确定题目集合；前端不能自行扩大题目范围。

### 10.3 判分规则

- 单选：选择项等于唯一正确项。
- 多选：选择集合与正确集合完全一致才算正确。
- 漏选、错选、多选均判错。

### 10.4 错题处理

- 提交答案后如果错误，按当前 session 的 `user_id`、`bank_id` 和 `question_id` 创建或更新 `mistake_records`。
- 答对错题时不自动删除，可设置为 `resolved_at`。
- 用户可以在指定题库下手动标记某道错题已掌握。

## 11. 权限模型

资源访问规则：

- 用户可以查看自己的完整资料，包括邮箱、角色和账户状态。
- 用户可以查看其他用户的公开基础资料，但不能看到邮箱、AI 配置、Prompt 模板、练习记录或错题记录。
- 其他用户页面可以显示头像，但头像 URL 必须来自用户公开资料字段，不能额外暴露邮箱。
- 用户可以查看其他用户公开发布的题库列表。
- 用户可以访问自己的私有题库。
- 所有人可以读取公开题库。
- 生成中、生成失败或尚未完成写入的题库即使 `desired_visibility = public`，也必须保持实际 `visibility = private`，不能出现在公开题库列表。
- 登录用户可以收藏自己有读取权限的题库，包括公开题库和自己的私有题库；不能收藏无权访问的私有题库。
- 用户取消收藏不影响题库本身，收藏计数需要随收藏关系创建或删除同步更新。
- 只有 owner 可以编辑、删除自己的题库和题目。
- 管理员可以查看和管理所有用户，但管理题库的能力需要单独在 API 中明确控制。
- 练习记录、错题记录始终只属于创建者，管理员默认不进入用户隐私练习详情，除非后续产品明确要求。

## 12. 安全设计

- 密码使用 `passlib[bcrypt]` 哈希。
- JWT 包含 `sub`、`role`、`exp`。
- Access token 短有效期，refresh token 较长有效期。
- 上传文件限制大小、扩展名和 MIME 类型。
- 用户 AI API key 由后端加密保存，不在任何读取接口返回明文。
- AI 配置属于用户私有资源，管理员列表也不应展示 API key 明文。
- 调用 AI 时只在服务端解密 key，日志中必须过滤 `Authorization` 和 key 字段。
- 所有写操作必须鉴权。
- 管理接口必须校验 admin role。
- 错误响应不泄露堆栈、数据库细节、AI provider 原始敏感响应。

## 13. 配置项

`.env` 关键配置：

```text
APP_ENV=development
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/quiz_pass
JWT_SECRET_KEY=change-me
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=14
AI_CONFIG_ENCRYPTION_KEY=change-me-32-byte-key
UPLOAD_MAX_MB=10
AI_MAX_TEXT_CHARS=30000
```

OpenAI 兼容 API 的 `api_base_url`、`api_key`、`model` 由用户在应用内配置，不放在 `.env` 作为业务默认值。`.env` 只保存加密用户 key 所需的服务端密钥和系统级限制。

## 14. 后台任务策略

初版可以使用 FastAPI `BackgroundTasks` 处理 AI 生成任务，适合单机开发和轻量部署。

后续增强：

- 引入 Celery/RQ + Redis。
- 支持任务进度。
- 支持长文档分块生成。
- 支持失败重试和取消。

## 15. 测试策略

### 后端测试

- Auth：注册、登录、刷新、权限失败。
- Question bank：私有/公开访问控制。
- Question bank favorites：可访问题库收藏、取消收藏、收藏数更新、重复收藏幂等处理、无权题库收藏拒绝。
- Pagination and filtering：题库、题目、错题、练习历史、管理员用户列表的分页边界、筛选白名单和排序白名单。
- Question validation：单选、多选、非法答案。
- Practice：创建 session、提交答案、判分、错题记录。
- JSON import/export：格式兼容与错误处理。
- AI generation：mock OpenAI 响应，测试校验与 job 状态。
- AI generated banks：测试生成中题库刷新可恢复、仅 owner 可见、成功后按 `desired_visibility` 切换公开状态、失败后保持私有。
- AI provider configs：测试用户只能访问自己的配置，读取接口不返回 key 明文，生成任务使用正确 model 快照。

### 前端测试

- 登录态路由守卫。
- 题库 CRUD 表单。
- 练习答题交互。
- AI 生成流程状态展示。
- 关键组件可以使用 Vitest + Vue Test Utils。

## 16. 开发实施顺序

建议按可运行闭环推进：

1. 后端项目骨架、配置、数据库连接、迁移。
2. 用户注册登录、JWT 鉴权、`/auth/me`。
3. 题库与题目 CRUD。
4. 前端基础布局、登录注册、题库列表与编辑。
5. JSON 导入导出。
6. 普通练习 session、判分、结果页。
7. 错题记录与错题练习。
8. 用户 AI 配置管理，包括 key 加密、默认配置、连通性测试。
9. AI 文件上传、文本抽取、生成任务、结果确认，并记录题库 model。
10. 练习历史与统计。
11. 管理员用户管理。
12. 测试补齐与部署整理。

## 17. 首版范围

首版必须完成：

- 用户注册登录
- 私有题库 CRUD
- 题目 CRUD
- JSON 导入导出
- 普通练习与模拟考试
- 错题自动记录
- 用户 Prompt 模板
- 用户多 AI 配置：`api_base_url`、`api_key`、`model`
- 文档上传 AI 生成题目
- 题库展示最近一次 AI 生成使用的 model

<!-- 首版暂不做：
- 复杂公开题库市场
- AI 长文档分章节生成
-->

## 18. 主要风险与决策

- AI 输出不稳定：必须使用严格 JSON schema 校验；生成型题库只有校验通过并成功写入题目后才可标记成功或公开。
- PDF 文本质量不稳定：初版只做文本型 PDF，扫描件 OCR 暂不支持。
- 练习状态一致性：以后端 session 为准，前端刷新后应能恢复当前 session。
- 公开题库权限：公开只代表可读，不代表可复制、编辑或查看 owner 私密信息。
- 多选判分争议：首版采用完全匹配才正确，保持规则简单明确。

## 19. Definition of Done

项目完成一个功能时应满足：

- API 有明确 request/response schema。
- 关键权限路径已覆盖。
- 前端页面能处理 loading、empty、error 状态。
- 数据库迁移可重复执行。
- 失败时返回用户可理解的错误。
- 至少有对应的后端测试，复杂交互补前端测试。

## 20. 当前实现盘点（2026-05-18）

本节是对当前仓库状态和本文档初始目标的对照。前面的章节保留为初始架构意图；本节记录现在已经落地的能力、仍未完成的部分，以及后续改进方案。

### 20.1 当前代码结构现状

后端已经从最初的 `api/v1 + services` 单层业务编排，演进为“v1 兼容 + v2/domain 分层”的过渡结构：

```text
backend/app/
  api/v1/                      # 兼容旧前端路径，部分已降级为 domain wrapper
  api/v2/                      # 新资源化 API 聚合入口
  domains/
    question_banks/            # 题库、题目、标签、收藏、导入导出、权限、统计、生命周期
    practice/                  # 练习 session、答题、结果、错题
    ai_generation/             # workflow、prompt、OpenAI client、校验、修复、草稿、LangGraph runtime
    users/                     # 用户资料、AI 配置、管理员用户管理
  models/                      # SQLAlchemy ORM
  schemas/                     # Pydantic DTO
  services/ai_generation.py    # AI 兼容 facade，保留 v1/测试 monkeypatch 表面
```

前端已经从单一 `api/client.ts` 类型和请求聚合，演进为“兼容 client + domain API 模块 + v2 API 模块”的过渡结构：

```text
frontend/src/
  api/
    http.ts                    # fetch wrapper
    types.ts                   # v1/v2 shared types
    auth.ts banks.ts ...       # v1/兼容 API 模块
    v2/                        # v2 banks/practice/users/aiGeneration
  components/
    App*.vue                   # 基础 UI
    bank/                      # BankCard、CreateBankModal
    practice/                  # 答题页组件
  composables/                 # useBankList、usePracticeSession、useCreateOrExtendBank
  pages/                       # 路由页面
```

数据库迁移已改为 Alembic 显式建表，不再在应用启动时默认 `Base.metadata.create_all`。当前开发路线允许重建开发库，`0001_initial.py` 是当前干净 schema。

### 20.2 已完成目标

#### 账号与用户

- 已实现注册、登录、当前用户信息。
- 登录支持用户名或邮箱。
- 注册和 FastAPI 422 错误已向前端可读错误靠拢。
- 已实现用户资料编辑、修改密码、公开用户页、用户搜索。
- 头像支持 QQ 邮箱头像策略。
- 管理员用户管理已具备分页检索、基础资料修改、启用/禁用、重置普通用户密码。
- 管理员不能给其他用户授权 admin role。

#### AI 配置

- 用户可维护多个 OpenAI 兼容 AI Provider 配置。
- 支持 `api_base_url`、`api_key`、`model`、默认配置、启用状态、连通性测试。
- API key 后端加密保存，读取接口不返回明文。
- API key 创建后禁止 patch 更新，只能删除配置重建。
- AI Provider 删除后，历史 workflow/job 保留 model/base url snapshot，外键 `SET NULL`。

#### 题库、题目、标签和收藏

- 已实现题库 CRUD、题目 CRUD、JSON 新建导入、JSON 追加导入、JSON 导出。
- 已实现公开题库、我的题库、我的收藏列表。
- 公开题库和私有题库在有读取权限时都可收藏。
- 已实现收藏数冗余统计和 `is_favorited`。
- 已实现题库级标签独立表和题库-标签关联表。
- 题库创建、编辑、AI 生成、JSON 导入支持标签。
- 题库列表支持关键词、作者、可见性、生成状态、标签 ID 多选筛选。
- 标签筛选 URL 使用数字 ID，如 `tag_ids=1,3,8`，不使用中文标签名。
- v2 题库 DTO 已返回 `owner`、`tags`、`stats`、`permissions`、`active_workflow`。

#### 权限模型

- 题库权限已抽到 `QuestionBankPermissionService`。
- owner 可管理自己的题库。
- 非 owner 可读取公开题库，可收藏、练习、查看自己的错题、导出。
- 非 owner 不可编辑/删除/导入追加/管理题目/AI 扩展公开题库。
- 非 owner 不能读取私有题库。
- admin 可管理所有题库。
- 错题、练习记录仍按当前登录用户隔离。

#### 练习、结果、历史和错题

- 已实现普通练习、模拟考试、错题练习。
- 创建 session 时由后端确定题目集合。
- 答题时校验题目属于当前 session 的题库，防跨题库提交。
- 普通/错题练习答题后即时反馈并锁定。
- 模拟考试答题时只保存并锁定，交卷后才显示答案解析。
- 支持恢复未完成 session。
- 历史记录返回题库名、开始时间、提交时间、最后作答时间、已做/全部。
- 结果页返回完整题面、选项、用户选择、正确答案 label、未作答状态、解析。
- 错题维度已固定为 `user_id + bank_id + question_id`。
- 题库下错题页后端返回题面、选项、正确答案 label、解析、错误次数、最后错误时间。

#### AI 生成与 workflow

- AI 调用已改用 OpenAI Python SDK，并支持用户配置任意 OpenAI 兼容 `base_url`。
- 已支持两类模式：
  - `knowledge_generate`：从知识库/文档生成题目，可固定题数或自适应题数。
  - `bank_parse`：从已有题库文档解析题目，不要求用户指定题数。
- 已支持用户额外指令，后端限制长度并声明不能覆盖系统硬规则。
- 已支持 AI 生成题库描述。
- AI prompt 已强调单选只能一个正确答案、多选至少两个正确答案。
- AI 输出经过后端结构化校验。
- AI 生成已升级为 workflow-first：
  - 文档提取
  - build context
  - generate/parse
  - validate
  - repair
  - write draft
  - confirm draft
- workflow、step、draft、draft questions 已持久化。
- `ImportJob` 已降级为队列/兼容投影，单向指向 workflow。
- 用户确认草稿前不写正式题目。
- 草稿支持编辑后确认入库；确认失败 rollback，不增加正式题目。
- 支持扩展已有题库，扩展时读取已有题目摘要和历史 workflow 上下文。
- AI 服务已拆成 `prompts.py`、`client.py`、`validator.py`、`drafts.py`、`workflow_runtime.py`、`workflow_state.py`、`context.py`，旧 `app/services/ai_generation.py` 只保留兼容 facade。

#### 数据库与迁移

- 已移除 `AIGenerationWorkflow.job_id`、`AIGenerationDraft.job_id` 和 `QuestionBank.active_generation_job_id` 数据库字段。
- 已解除 `ImportJob <-> AIGenerationWorkflow` 循环外键。
- 已补核心 `ON DELETE CASCADE`：
  - 题库删除级联 questions/options/favorites/tag links/practice/mistakes/workflows/steps/drafts/jobs。
- AI Provider 删除对历史 workflow/job 使用 `SET NULL`，保留 snapshot。
- SQLite 开发/测试环境已启用外键约束。
- 后端测试通过 Alembic upgrade 创建测试库。

#### 前端体验

- 前端已使用 Vue 3、Pinia、Vue Router、Tailwind CSS v4。
- 已拆出基础 UI 组件、BankListView、BankCard、CreateBankModal、练习页组件。
- 已实现侧边栏和头像用户菜单。
- 题库列表、公开题库、收藏题库已使用统一列表组件。
- 多数列表筛选和分页已走 URL query，可刷新恢复。
- 做题页已支持答题卡、上一题/下一题、W/S 跳行、A/D/方向键、数字键、Enter。
- 题干、选项、解析展示态已接入 MathJax。
- 已有 v2 API 模块，部分页面已经开始使用 `/api/v2`。

#### 测试

- 后端已有较完整的 `tests/test_api.py`，覆盖账号、题库权限、标签、收藏、练习判分、错题、AI workflow、草稿确认、v2 banks/practice/users/admin/questions/import/export。
- 当前后端验证命令：

```bash
cd backend
.venv/bin/python -m compileall app
.venv/bin/python -m pytest tests -q
```

最近一次验证结果：`20 passed`。

### 20.3 未完成或与初始目标不一致的部分

#### 文档与实现不一致

- 本文档前面章节仍有旧设计残留：
  - `active_generation_job_id` 已不再是数据库字段。
  - AI 生成不再是成功后直接入库，而是先生成草稿，用户确认后入库。
  - 后端已存在 `/api/v2`，不再只有 `/api/v1`。
  - 后端业务已进入 `domains/` 分层，不再是单纯 `services/`。
  - JWT refresh token 仍未完整落地，当前主要是 access token。
  - `user_prompt_templates` 模型仍在，但前端和业务流程没有成为核心能力。

#### 前端迁移未完成

- 前端仍处在 v1/v2 混用阶段，部分页面使用 v1 job API，部分页面使用 v2 workflow/bank API。
- 草稿确认路由仍以 `/ai-generation/jobs/:jobId/draft` 命名，和 v2 workflow-first 语义不完全一致。
- 部分页面仍从 `api/client.ts` 兼容层取类型或请求。
- 前端需要继续统一到 `api/http.ts` + `api/types.ts` + domain API 模块。
- 前端缺少系统化测试，主要依赖 `npm run build` 和手动验证。

#### UI 和信息密度

- 题库卡片、详情页、生成队列等已经开始压缩，但整体还需要统一到“高频工具型、信息密度适中”的风格。
- 题库列表应继续减少大卡片感，尽量像紧凑记录行。
- 草稿确认页在题目多时仍可能偏长，需要更强的折叠、目录或批量编辑能力。
- AI 配置页、开始答题页、编辑题库页仍需继续检查宽度、间距和信息密度一致性。

#### 后端分层仍在过渡

- v1 路由已部分降级为 domain wrapper，但并未全部清理。
- `QuestionBankImportExportService`、`QuestionService`、`PracticeSessionService`、`AIGenerationWorkflowService` 已存在，但一些兼容函数仍留在 v1 或 facade。
- 统一错误响应 `{ error: { code, message, details } }` 尚未落地。
- Repository 层仍不完整；当前更接近 “Domain Service + Query Service + SQLAlchemy session”。
- 部分 DTO/schema 仍有 v1/v2 并行重复。

#### AI workflow 能力仍是首版

- LangGraph workflow 已落地，但未引入独立队列系统。
- BackgroundTasks 仍是当前执行方式，重启进程时 pending/running workflow 不能自动恢复执行。
- workflow 没有 checkpoint saver，也没有 retry/cancel/re-run 的完整产品化入口。
- 修复策略是整包 payload 修复，不支持“只修复单道坏题”。
- 没有多模型 fallback。
- 没有对长文档做分块、去重、覆盖度统计和增量生成质量评估。

#### 数据库与部署

- 当前迁移采用开发库可重建路线，不适合直接作为生产在线迁移。
- MySQL 本地配置示例和部署说明仍需完善。
- `__pycache__`、构建产物、测试 DB 等需要持续确保不进入提交。
- 生产需要明确 Alembic upgrade 流程，应用启动不再自动建表。

#### 安全与权限增强

- refresh token、logout token 失效机制未完整实现。
- 文件上传大小、MIME、文本长度限制需要系统化配置和测试。
- AI 日志敏感信息过滤需要继续审查。
- 管理员可管理题库，但 AI workflow 源文档和额外指令默认只对创建者可见；这条规则需要在所有新接口中继续保持。

### 20.4 下一步改进方案

#### P0：先修正前端 workflow-first 语义和构建稳定性

目标：前端清楚地区分 v1 job 和 v2 workflow，避免把 workflow id 当成 job id 使用。

- 新增或调整路由：
  - `/ai-generation/workflows/:workflowId/draft`
  - 保留 `/ai-generation/jobs/:jobId/draft` 作为 v1 兼容入口，或在页面内部根据来源分别调用 API。
- `BankDetailPage` 的 `active_workflow` 草稿入口应跳转 workflow 路由。
- `GenerationDraftPage` 支持 workflow ID 调用 `/api/v2/ai/workflows/{workflow_id}/draft`、confirm、discard。
- `GenerationJobsPage` 如果仍展示 v1 job，应使用 job id；如果切 v2 workflow 队列，则改名和数据结构。
- 跑通：

```bash
cd frontend
npm run build
```

#### P1：完成前端 v2 增量迁移

目标：前端展示权限、题库统计、active workflow 统一以 v2 DTO 为准。

- 题库列表、题库详情、题目管理、导入导出优先统一到 `/api/v2/banks`。
- 练习 session、结果、错题优先统一到 `/api/v2/practice` 和 `/api/v2/banks/{bank_id}/mistakes`。
- 用户资料、AI Provider、管理员用户管理逐步统一到 `/api/v2/users` 和 `/api/v2/admin/users`。
- `api/client.ts` 最终只保留兼容 re-export 或被移除。
- 前端按钮显示尽量使用后端 `permissions`，减少重复 owner/admin 判断。

#### P1：继续压缩题库与列表 UI

目标：保留功能但提升屏幕信息密度。

- `BankCard.vue` 改为更接近紧凑记录行：
  - 标题、状态、收藏按钮同一行。
  - 描述默认一行截断。
  - 作者、标签、题数、收藏数、模型放入紧凑 metadata 行。
  - padding 优先 `p-3`/`p-4`，减少 `gap-4`/`p-6`。
- `BankListView.vue` 头部继续紧凑化，筛选 chip 不占大区域。
- 详情页保留必要信息，但操作区和统计区减少卡片堆叠。
- 生成队列失败信息保留完整，但默认只在失败项中展开或以紧凑错误块展示。

#### P1：补齐后端统一错误和 API 约定

目标：前后端错误展示稳定，不依赖 FastAPI 默认结构。

- 引入统一错误响应：

```json
{
  "error": {
    "code": "QUESTION_VALIDATION_FAILED",
    "message": "第 3 题校验失败",
    "details": {}
  }
}
```

- 先在 v2 API 落地，v1 保持兼容。
- 前端 `api/http.ts` 同时兼容：
  - FastAPI `detail: string`
  - FastAPI `detail: []`
  - 新 `{ error }`

#### P2：AI workflow 产品化

目标：让 AI workflow 不只是后台任务，而是可恢复、可重试、可扩展的业务资产。

- 增加 workflow retry：
  - 从失败节点或从头重跑。
  - 保留旧 step 记录，新增 retry batch 标识。
- 增加 cancel 的后端一致性：
  - 已 draft_ready 的取消应变为 discarded/cancelled。
  - running 中取消需要在节点边界检查状态。
- 增加“只修复草稿坏题”能力：
  - 草稿题单题校验。
  - 对非法题调用修复 prompt。
- 增加扩展题库去重：
  - 读取已有题干摘要。
  - 后端校验近似重复并提示用户。
- 后续把 BackgroundTasks 替换为 RQ/Celery + Redis，支持进程重启后恢复 pending workflow。

#### P2：完善导入导出和题库维护

- JSON 导入支持更清晰的错误定位：第几题、字段、原因。
- 追加导入可选去重策略：
  - 跳过同题干。
  - 覆盖同题干。
  - 全部追加。
- 导出格式版本升级时保持向后兼容。
- 题库标签支持管理页：合并标签、重命名标签、清理未使用标签。

#### P2：补前端测试和端到端冒烟

- 引入 Vitest + Vue Test Utils 覆盖：
  - `useBankList` query 同步。
  - `usePracticeSession` 答题锁定、exam reveal。
  - `GenerationDraftPage` 保存和确认。
- 以 Playwright 或轻量脚本做冒烟：
  - 登录
  - 创建题库
  - 导入 JSON
  - 开始练习
  - 查看结果
  - 查看错题
  - AI 生成队列和草稿页

#### P3：部署与运维整理

- 完善 `.env.example`：
  - SQLite 开发默认。
  - MySQL 示例。
  - CORS、JWT、AI key encryption、上传限制。
- README 增加：
  - 初始化 venv。
  - `alembic upgrade head`。
  - 启动后端/前端。
  - 重建开发库步骤。
- 增加 `.gitignore` 检查项：
  - `node_modules`
  - `dist`
  - `__pycache__`
  - `*.db`
  - `frontend/tsconfig.tsbuildinfo`

### 20.5 当前优先级建议

建议下一轮按以下顺序推进：

1. 修正前端 workflow/job 路由语义，确保 AI 草稿确认入口稳定。
2. 跑 `npm run build`，修复前端类型和构建错误。
3. 把题库列表和题库详情完全稳定在 v2 DTO，并用 `permissions` 驱动按钮。
4. 压缩题库卡片和列表 UI，提高信息密度。
5. 补统一错误响应，先从 v2 API 和前端 `api/http.ts` 开始。
6. 再做 AI workflow retry/cancel/partial repair。
