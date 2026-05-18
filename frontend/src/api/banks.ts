import { api, authHeader } from './http'
import type { Page, QuestionBank, QuestionBankTag } from './types'

type BankListParams = {
  page?: number; page_size?: number; keyword?: string; owner_id?: number
  tag_ids?: string; visibility?: string; generation_status?: string
}

export function listMyBanks(params: BankListParams) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBank>>(`/api/v1/question-banks?${q}`)
}

export function listPublicBanks(params: BankListParams) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBank>>(`/api/v1/question-banks/public?${q}`)
}

export function listFavorites(params: BankListParams) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBank>>(`/api/v1/question-banks/favorites?${q}`)
}

export function getBank(bankId: number) {
  return api<QuestionBank>(`/api/v1/question-banks/${bankId}`)
}

export function createBank(data: { title: string; visibility?: string; tag_names?: string[] }) {
  return api<QuestionBank>('/api/v1/question-banks', { method: 'POST', body: JSON.stringify(data) })
}

export function updateBank(bankId: number, data: Record<string, unknown>) {
  return api<QuestionBank>(`/api/v1/question-banks/${bankId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteBank(bankId: number) {
  return api(`/api/v1/question-banks/${bankId}`, { method: 'DELETE' })
}

export function favoriteBank(bankId: number) {
  return api(`/api/v1/question-banks/${bankId}/favorite`, { method: 'POST' })
}

export function unfavoriteBank(bankId: number) {
  return api(`/api/v1/question-banks/${bankId}/favorite`, { method: 'DELETE' })
}

export function exportBankUrl(bankId: number) {
  return `/api/v1/question-banks/${bankId}/export`
}

export function importJsonNewBank(form: FormData) {
  return api<QuestionBank>('/api/v1/question-banks/import-json', { method: 'POST', body: form })
}

export function importJsonToBank(bankId: number, form: FormData) {
  return api<QuestionBank>(`/api/v1/question-banks/${bankId}/import-json`, { method: 'POST', body: form })
}

export function listTags(params: { keyword?: string; ids?: string; page_size?: number }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  return api<Page<QuestionBankTag>>(`/api/v1/question-banks/tags?${q}`)
}

export function extendWithAI(bankId: number, form: FormData) {
  return api<{ bank_id: number; job_id: number }>(`/api/v1/question-banks/${bankId}/ai-generation/extend-jobs`, { method: 'POST', body: form })
}
