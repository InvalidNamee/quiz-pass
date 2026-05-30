import { api } from '../http'
import type { Page, PracticeSession, MistakeAttempt, MistakeRecord, QuestionTypeSettings } from '../types'

export function createSession(data: { bank_id: number; mode: string; question_limit?: number; question_type_settings?: QuestionTypeSettings }) {
  return api<PracticeSession>('/api/v2/practice/sessions', { method: 'POST', body: JSON.stringify(data) })
}

export function getSession(sessionId: number) {
  return api<PracticeSession>(`/api/v2/practice/sessions/${sessionId}`)
}

export function getResumableSession(bankId: number) {
  return api<PracticeSession | null>(`/api/v2/banks/${bankId}/practice/resumable-session`)
}

export function getSessionQuestions(sessionId: number, shuffleOptions?: boolean) {
  const q = shuffleOptions ? '?shuffle_options=true' : ''
  return api<any[]>(`/api/v2/practice/sessions/${sessionId}/questions${q}`)
}

export function answerQuestion(sessionId: number, questionId: number, selectedOptionIds: number[], textAnswers: string[] = []) {
  return api<any>(`/api/v2/practice/sessions/${sessionId}/answers`, {
    method: 'POST',
    body: JSON.stringify({ question_id: questionId, selected_option_ids: selectedOptionIds, text_answers: textAnswers }),
  })
}

export function saveAnswerDraft(sessionId: number, questionId: number, selectedOptionIds: number[], textAnswers: string[] = []) {
  return api<{ ok: boolean; changed: boolean }>(`/api/v2/practice/sessions/${sessionId}/answers/${questionId}/draft`, {
    method: 'PUT',
    body: JSON.stringify({ question_id: questionId, selected_option_ids: selectedOptionIds, text_answers: textAnswers }),
  })
}

export function submitSession(sessionId: number, options: { commit_drafts?: boolean } = {}) {
  return api<PracticeSession>(`/api/v2/practice/sessions/${sessionId}/submit`, {
    method: 'POST',
    body: JSON.stringify({ commit_drafts: options.commit_drafts ?? true }),
  })
}

export function deleteSession(sessionId: number) {
  return api<{ ok: boolean }>(`/api/v2/practice/sessions/${sessionId}`, { method: 'DELETE' })
}

export function getResult(sessionId: number) {
  return api<any[]>(`/api/v2/practice/sessions/${sessionId}/result`)
}

export function listMistakes(bankId: number, resolved?: boolean, params: { page?: number; page_size?: number } = {}) {
  const q = new URLSearchParams()
  if (resolved !== undefined) q.set('resolved', String(resolved))
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  return api<Page<MistakeRecord>>(`/api/v2/banks/${bankId}/mistakes?${q}`)
}

export function listMistakeAttempts(bankId: number, resolved: boolean | undefined = false, params: { page?: number; page_size?: number } = {}) {
  const q = new URLSearchParams()
  if (resolved !== undefined) q.set('resolved', String(resolved))
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined) q.set(k, String(v)) })
  return api<Page<MistakeAttempt>>(`/api/v2/banks/${bankId}/mistake-attempts?${q}`)
}

export function createMistakeSession(bankId: number) {
  return api<PracticeSession>(`/api/v2/banks/${bankId}/mistakes/practice-sessions`, { method: 'POST' })
}

export function createMistakeSessionFromPracticeSession(sessionId: number) {
  return api<PracticeSession>(`/api/v2/practice/sessions/${sessionId}/mistake-practice-sessions`, { method: 'POST' })
}

export function resolveMistakeAttempt(bankId: number, attemptId: number) {
  return api(`/api/v2/banks/${bankId}/mistake-attempts/${attemptId}/resolve`, { method: 'POST' })
}

export function listHistory(params: { page?: number; page_size?: number; bank_id?: number; mode?: string; status?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<PracticeSession>>(`/api/v2/history/sessions?${q}`)
}
