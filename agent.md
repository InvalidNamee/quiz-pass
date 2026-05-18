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
