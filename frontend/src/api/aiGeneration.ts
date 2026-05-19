import { api } from './http'
import type { Page, AIGenerationDraft } from './types'
import type { WorkflowListItem } from './v2/aiGeneration'

export function createJob(form: FormData) {
  return api<{ bank_id: number; workflow_id: number; job_id: number }>('/api/v2/ai/workflows', { method: 'POST', body: form })
}

export function listJobs(params: { page?: number; page_size?: number; status?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<WorkflowListItem>>(`/api/v2/ai/workflows?${q}`)
}

export function getJob(workflowId: number) {
  return api<WorkflowListItem>(`/api/v2/ai/workflows/${workflowId}`)
}

export function cancelJob(_workflowId: number) {
  return Promise.reject(new Error('v2 workflow cancellation is not available yet'))
}

export function confirmJob(workflowId: number) {
  return api<{ ok: boolean; bank_id: number }>(`/api/v2/ai/workflows/${workflowId}/draft/confirm`, { method: 'POST' })
}

export function getDraft(workflowId: number) {
  return api<AIGenerationDraft>(`/api/v2/ai/workflows/${workflowId}/draft`)
}

export function updateDraft(workflowId: number, data: Record<string, unknown>) {
  return api<AIGenerationDraft>(`/api/v2/ai/workflows/${workflowId}/draft`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function discardDraft(workflowId: number) {
  return api(`/api/v2/ai/workflows/${workflowId}/draft/discard`, { method: 'POST' })
}
