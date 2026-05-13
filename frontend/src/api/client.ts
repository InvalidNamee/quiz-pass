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
    throw new Error(typeof error.detail === 'string' ? error.detail : '请求失败')
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
  question_count: number
  favorite_count: number
  ai_model_name: string | null
  is_favorited: boolean
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

export type PracticeSession = {
  id: number
  user_id: number
  bank_id: number
  mode: string
  status: string
  total_questions: number
  answered_count: number
  correct_count: number
  score: number
  started_at: string
  submitted_at: string | null
}

export type MistakeRecord = {
  id: number
  bank_id: number
  question_id: number
  wrong_count: number
  last_wrong_at: string
  resolved_at: string | null
}
