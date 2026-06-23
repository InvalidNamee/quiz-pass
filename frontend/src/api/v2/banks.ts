import { api, apiUrl } from '../http'
import type { BankDownloadPackage, Page, Question, QuestionBankV2, QuestionBankTag } from '../types'

type BankListParams = { page?: number; page_size?: number; keyword?: string; owner_id?: number; owner?: string; tag_ids?: string; visibility?: string; generation_status?: string }

export function listBanks(scope: 'mine' | 'public' | 'favorites', params: BankListParams = {}) {
  const q = new URLSearchParams()
  q.set('scope', scope)
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBankV2>>(`/api/v2/banks?${q}`)
}

export function listRecentPracticeBanks(pageSize = 6) {
  return api<QuestionBankV2[]>(`/api/v2/banks/recent-practice?page_size=${pageSize}`)
}

export function getBank(bankId: number) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}`)
}

export function downloadBankPackage(bankId: number) {
  return api<BankDownloadPackage>(`/api/v2/banks/${bankId}/download-package`)
}

export function createBank(data: { title: string; visibility?: string; tag_names?: string[] }) {
  return api<QuestionBankV2>('/api/v2/banks', { method: 'POST', body: JSON.stringify(data) })
}

export function updateBank(bankId: number, data: Record<string, unknown>) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function updateBankAIContext(bankId: number, aiContext: string | null) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}/ai-context`, { method: 'PATCH', body: JSON.stringify({ ai_context: aiContext }) })
}

export function shareBank(bankId: number) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}/share`, { method: 'POST' })
}

export function deleteBank(bankId: number) {
  return api(`/api/v2/banks/${bankId}`, { method: 'DELETE' })
}

export function favoriteBank(bankId: number) {
  return api(`/api/v2/banks/${bankId}/favorites`, { method: 'POST' })
}

export function unfavoriteBank(bankId: number) {
  return api(`/api/v2/banks/${bankId}/favorites`, { method: 'DELETE' })
}

export function importJsonNewBank(form: FormData) {
  return api<QuestionBankV2>('/api/v2/banks/import-json', { method: 'POST', body: form })
}

export function importJsonToBank(bankId: number, form: FormData) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}/import-json`, { method: 'POST', body: form })
}

export function exportBankUrl(bankId: number) {
  return apiUrl(`/api/v2/banks/${bankId}/export-json`)
}

export function listTags(params: { keyword?: string; ids?: string; page_size?: number }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  return api<Page<QuestionBankTag>>(`/api/v2/banks/tags?${q}`)
}

export function listQuestions(bankId: number, params: { page?: number; page_size?: number; keyword?: string; all?: boolean } = {}) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<Question>>(`/api/v2/banks/${bankId}/questions?${q}`)
}

export function createQuestion(bankId: number, data: Record<string, unknown>) {
  return api<Question>(`/api/v2/banks/${bankId}/questions`, { method: 'POST', body: JSON.stringify(data) })
}

export function updateQuestion(questionId: number, data: Record<string, unknown>) {
  return api<Question>(`/api/v2/questions/${questionId}`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function deleteQuestion(questionId: number) {
  return api(`/api/v2/questions/${questionId}`, { method: 'DELETE' })
}
