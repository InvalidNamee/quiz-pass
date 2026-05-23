import { api } from '../http'
import type { Page, AIGenerationDraft } from '../types'

export type WorkflowListItem = {
  id: number; bank_id: number | null; purpose: string; generation_mode: string
  status: string; source_file_name: string | null; source_text_snapshot: string | null
  bank_title_snapshot: string | null; requested_count: number | null
  generate_description: string; extra_instruction: string | null
  ai_provider_config_id: number | null; inherit_context: boolean
  include_existing_questions: boolean
  retry_of_workflow_id: number | null; retried_by_workflow_id: number | null
  ai_model_snapshot: string | null
  repair_attempts: number; error_message: string | null; cancel_reason: string | null
  error_summary: string | null
  draft_question_count: number; imported_question_count: number; question_delta: number
  can_confirm: boolean; can_retry: boolean; can_cancel: boolean
  queue_job_id: string | null; enqueued_at: string | null; started_at: string | null
  created_at: string; finished_at: string | null
}

export type WorkflowStep = {
  id: number; workflow_id: number; step_name: string; status: string
  input_json: string | null; output_json: string | null; error_message: string | null
  started_at: string | null; finished_at: string | null; created_at: string
}

export type WorkflowDetail = WorkflowListItem & { steps: WorkflowStep[] }

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

export function listBankWorkflows(bankId: number, params: { page?: number; page_size?: number; status?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<WorkflowListItem>>(`/api/v2/banks/${bankId}/ai-workflows?${q}`)
}

export function getWorkflow(workflowId: number) {
  return api<WorkflowListItem>(`/api/v2/ai/workflows/${workflowId}`)
}

export function getWorkflowDetail(workflowId: number) {
  return api<WorkflowDetail>(`/api/v2/ai/workflows/${workflowId}/detail`)
}

export function getDraft(workflowId: number) {
  return api<AIGenerationDraft>(`/api/v2/ai/workflows/${workflowId}/draft`)
}

export function updateDraft(workflowId: number, data: Record<string, unknown>) {
  return api<AIGenerationDraft>(`/api/v2/ai/workflows/${workflowId}/draft`, { method: 'PATCH', body: JSON.stringify(data) })
}

export function confirmDraft(workflowId: number) {
  return api<{ ok: boolean; bank_id: number }>(`/api/v2/ai/workflows/${workflowId}/draft/confirm`, { method: 'POST' })
}

export function discardDraft(workflowId: number) {
  return api(`/api/v2/ai/workflows/${workflowId}/draft/discard`, { method: 'POST' })
}

export function cancelWorkflow(workflowId: number, reason?: string) {
  const form = new FormData()
  if (reason) form.set('cancel_reason', reason)
  return api(`/api/v2/ai/workflows/${workflowId}/cancel`, { method: 'POST', body: form })
}

export function retryWorkflow(workflowId: number, form: FormData) {
  return api<{ workflow_id: number; bank_id: number; job_id: number }>(`/api/v2/ai/workflows/${workflowId}/retry`, { method: 'POST', body: form })
}
