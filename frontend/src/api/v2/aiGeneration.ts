import { api } from '../http'
import type { Page, AIGenerationDraft, QuestionBankV2 } from '../types'

type WorkflowListItem = {
  id: number; bank_id: number; purpose: string; generation_mode: string
  status: string; source_file_name: string | null; ai_model_snapshot: string | null
  repair_attempts: number; error_message: string | null
  draft_question_count: number; can_confirm: boolean
  created_at: string; finished_at: string | null
}

export function createWorkflow(form: FormData) {
  return api<{ workflow_id: number; bank_id: number; job_id: number }>('/api/v2/ai/workflows', { method: 'POST', body: form })
}

export function extendWorkflow(bankId: number, form: FormData) {
  return api<{ workflow_id: number; bank_id: number; job_id: number }>(`/api/v2/banks/${bankId}/ai-workflows`, { method: 'POST', body: form })
}

export function listWorkflows(params: { page?: number; page_size?: number; status?: string; bank_id?: number }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<WorkflowListItem>>(`/api/v2/ai/workflows?${q}`)
}

export function getWorkflow(workflowId: number) {
  return api<WorkflowListItem>(`/api/v2/ai/workflows/${workflowId}`)
}

export function getDraft(workflowId: number) {
  return api<AIGenerationDraft>(`/api/v2/ai/workflows/${workflowId}/draft`)
}

export function updateDraft(workflowId: number, data: Record<string, unknown>) {
  return api<AIGenerationDraft>(`/api/v2/ai/workflows/${workflowId}/draft`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function confirmDraft(workflowId: number) {
  return api(`/api/v2/ai/workflows/${workflowId}/draft/confirm`, { method: 'POST' })
}

export function discardDraft(workflowId: number) {
  return api(`/api/v2/ai/workflows/${workflowId}/draft/discard`, { method: 'POST' })
}
