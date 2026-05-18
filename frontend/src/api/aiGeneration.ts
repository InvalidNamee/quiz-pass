import { api } from './http'
import type { Page, AIGenerationDraft, GenerationJob } from './types'

export function createJob(form: FormData) {
  return api<{ bank_id: number; job_id: number }>('/api/v1/ai-generation/question-bank-jobs', { method: 'POST', body: form })
}

export function listJobs(params: { page?: number; page_size?: number; status?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<GenerationJob>>(`/api/v1/ai-generation/jobs?${q}`)
}

export function getJob(jobId: number) {
  return api<GenerationJob>(`/api/v1/ai-generation/jobs/${jobId}`)
}

export function cancelJob(jobId: number) {
  return api(`/api/v1/ai-generation/jobs/${jobId}/cancel`, { method: 'POST' })
}

export function confirmJob(jobId: number) {
  return api<{ ok: boolean; bank_id: number }>(`/api/v1/ai-generation/jobs/${jobId}/confirm`, { method: 'POST' })
}

export function getDraft(jobId: number) {
  return api<AIGenerationDraft>(`/api/v1/ai-generation/jobs/${jobId}/draft`)
}

export function updateDraft(jobId: number, data: Record<string, unknown>) {
  return api<AIGenerationDraft>(`/api/v1/ai-generation/jobs/${jobId}/draft`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function discardDraft(jobId: number) {
  return api(`/api/v1/ai-generation/jobs/${jobId}/discard`, { method: 'POST' })
}
