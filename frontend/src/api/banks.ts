import { api } from './http'
import type { Page, QuestionBankV2, QuestionBankTag } from './types'

type BankListParams = {
  page?: number; page_size?: number; keyword?: string; owner_id?: number
  tag_ids?: string; visibility?: string; generation_status?: string
}

export function listMyBanks(params: BankListParams) {
  const q = new URLSearchParams()
  q.set('scope', 'mine')
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBankV2>>(`/api/v2/banks?${q}`)
}

export function listPublicBanks(params: BankListParams) {
  const q = new URLSearchParams()
  q.set('scope', 'public')
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBankV2>>(`/api/v2/banks?${q}`)
}

export function listFavorites(params: BankListParams) {
  const q = new URLSearchParams()
  q.set('scope', 'favorites')
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<QuestionBankV2>>(`/api/v2/banks?${q}`)
}

export function getBank(bankId: number) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}`)
}

export function createBank(data: { title: string; visibility?: string; tag_names?: string[] }) {
  return api<QuestionBankV2>('/api/v2/banks', { method: 'POST', body: JSON.stringify(data) })
}

export function updateBank(bankId: number, data: Record<string, unknown>) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}`, { method: 'PATCH', body: JSON.stringify(data) })
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

export function exportBankUrl(bankId: number) {
  return `/api/v2/banks/${bankId}/export-json`
}

export function importJsonNewBank(form: FormData) {
  return api<QuestionBankV2>('/api/v2/banks/import-json', { method: 'POST', body: form })
}

export function importJsonToBank(bankId: number, form: FormData) {
  return api<QuestionBankV2>(`/api/v2/banks/${bankId}/import-json`, { method: 'POST', body: form })
}

export function listTags(params: { keyword?: string; ids?: string; page_size?: number }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  return api<Page<QuestionBankTag>>(`/api/v2/banks/tags?${q}`)
}

export function extendWithAI(bankId: number, form: FormData) {
  return api<{ bank_id: number; workflow_id: number; job_id: number }>(`/api/v2/banks/${bankId}/ai-workflows`, { method: 'POST', body: form })
}
