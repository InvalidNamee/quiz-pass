export type Page<T> = {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    if (typeof error.detail === 'string') throw new Error(error.detail)
    if (Array.isArray(error.detail)) {
      const message = error.detail
        .map((item: { loc?: unknown[]; msg?: string }) => {
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : ''
          return field ? `${field}: ${item.msg ?? '校验失败'}` : item.msg ?? '校验失败'
        })
        .join('；')
      throw new Error(message || '请求参数校验失败')
    }
    throw new Error('请求失败')
  }
  return response.json()
}

export type UserMe = {
  id: number
  email: string
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
