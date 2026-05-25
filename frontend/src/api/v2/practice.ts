import { api } from '../http'
import type { Page, PracticeSession, MistakeRecord, QuestionTypeSettings } from '../types'

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

export function submitSession(sessionId: number) {
  return api<PracticeSession>(`/api/v2/practice/sessions/${sessionId}/submit`, { method: 'POST' })
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

export function createMistakeSession(bankId: number) {
  return api<PracticeSession>(`/api/v2/banks/${bankId}/mistakes/practice-sessions`, { method: 'POST' })
}

export function resolveMistake(bankId: number, questionId: number) {
  return api(`/api/v2/banks/${bankId}/mistakes/${questionId}/resolve`, { method: 'POST' })
}

export function listHistory(params: { page?: number; page_size?: number; bank_id?: number; mode?: string; status?: string }) {
  const q = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)) })
  return api<Page<PracticeSession>>(`/api/v2/history/sessions?${q}`)
}
