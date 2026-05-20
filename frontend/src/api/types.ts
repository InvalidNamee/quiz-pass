export type Page<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export type UserMe = {
  id: number
  email: string
  email_verified_at: string | null
  username: string
  display_name: string | null
  avatar_url: string | null
  avatar_source: string
  bio: string | null
  role: string
  is_active: boolean
}

export type UserPublic = {
  id: number
  username: string
  display_name: string | null
  avatar_url: string | null
  bio: string | null
  created_at: string
  public_bank_count: number
}

export type QuestionBank = {
  id: number
  owner_id: number
  owner_username: string | null
  owner_display_name: string | null
  owner_avatar_url: string | null
  title: string
  description: string | null
  visibility: string
  desired_visibility: string
  generation_status: string
  active_generation_job_id: number | null
  question_count: number
  favorite_count: number
  ai_model_name: string | null
  tags: QuestionBankTag[]
  is_favorited: boolean
}

export type QuestionBankTag = {
  id: number
  name: string
}

export type AIProviderConfig = {
  id: number
  name: string
  api_base_url: string
  model: string
  is_default: boolean
  is_active: boolean
  has_api_key: boolean
}

export type QuestionOption = {
  id?: number
  label: string
  content: string
  is_correct?: boolean
  sort_order?: number
}

export type Question = {
  id: number
  bank_id: number
  type: 'single' | 'multiple'
  stem: string
  explanation: string | null
  difficulty: string | null
  source: string
  generated_model: string | null
  options: QuestionOption[]
}

export type AIGenerationDraftQuestion = {
  id: number
  type: 'single' | 'multiple'
  stem: string
  explanation: string | null
  difficulty: string | null
  options: Array<{ label: string; content: string; is_correct: boolean }>
  validation_status: string
  validation_message: string | null
}

export type AIGenerationDraft = {
  id: number
  workflow_id: number
  job_id: number
  bank_id: number
  bank_description: string | null
  validation_summary: string | null
  status: string
  questions: AIGenerationDraftQuestion[]
}

export type PracticeSession = {
  id: number
  user_id: number
  bank_id: number
  bank_title: string | null
  bank_visibility: string | null
  bank_generation_status: string | null
  mode: string
  status: string
  total_questions: number
  answered_count: number
  correct_count: number
  score: number
  started_at: string
  submitted_at: string | null
  last_answered_at: string | null
}

export type MistakeRecord = {
  id: number
  user_id: number
  bank_id: number
  question_id: number
  type: 'single' | 'multiple'
  stem: string
  options: Array<{ id: number; label: string; content: string }>
  correct_option_ids: number[]
  correct_labels: string[]
  explanation: string | null
  wrong_count: number
  last_wrong_at: string
  resolved_at: string | null
}

// --- v2 types ---

export type BankOwner = {
  id: number
  username: string
  display_name: string | null
  avatar_url: string | null
}

export type BankStats = {
  question_count: number
  favorite_count: number
}

export type BankPermissions = {
  can_read: boolean
  can_manage: boolean
  can_export: boolean
  can_practice: boolean
  can_view_mistakes: boolean
  can_extend_ai: boolean
}

export type ActiveWorkflowInfo = {
  id: number
  status: string
  purpose: string
  draft_question_count: number
}

export type QuestionBankV2 = {
  id: number
  title: string
  description: string | null
  visibility: string
  desired_visibility: string
  generation_status: string
  ai_model_name: string | null
  is_favorited: boolean
  created_at: string
  updated_at: string
  owner: BankOwner
  tags: QuestionBankTag[]
  stats: BankStats
  permissions: BankPermissions
  active_workflow: ActiveWorkflowInfo | null
}

export type GenerationJob = {
  id: number
  bank_id: number | null
  workflow_id: number | null
  type: string
  status: string
  workflow_status: string | null
  draft_question_count: number
  repair_attempts: number
  can_confirm: boolean
  file_name: string | null
  ai_model_snapshot: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}
