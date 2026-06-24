import { api } from '../api/http'
import type { OfflinePracticeSyncResult, QuestionType } from '../api/types'
import { getResult, getSessionQuestions, listHistory } from '../api/v2/practice'
import { getLocalDb } from './db'
import { getLocalBank, getLocalQuestions, listLocalBanks } from './banks'
import type { LocalBlank, LocalOption, LocalPracticeAnswerResult, LocalPracticeQuestion, LocalPracticeResult, LocalPracticeSession, LocalQuestion } from './types'

type SessionRow = {
  id: number
  client_session_id: string
  local_bank_id: number
  remote_bank_id: number
  mode: string
  status: string
  total_questions: number
  correct_count: number
  score: number
  started_at: string
  submitted_at: string | null
  sync_status: string
  sync_error: string | null
  remote_session_id: number | null
}

type AnswerRow = {
  local_question_id: number
  selected_option_ids_json: string
  text_answers_json: string
  is_correct: number
  is_submitted: number
  answered_at: string
}

type SessionQuestionRow = {
  local_question_id: number
  sort_order: number
}

function nowIso() {
  return new Date().toISOString()
}

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID()
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function rowToSession(row: SessionRow): LocalPracticeSession {
  return {
    id: row.id,
    client_session_id: row.client_session_id,
    local_bank_id: row.local_bank_id,
    remote_bank_id: row.remote_bank_id,
    mode: row.mode,
    status: row.status,
    total_questions: row.total_questions,
    correct_count: row.correct_count,
    score: row.score,
    started_at: row.started_at,
    submitted_at: row.submitted_at,
    sync_status: row.sync_status,
    sync_error: row.sync_error,
    remote_session_id: row.remote_session_id,
  }
}

function normalizeTextAnswers(question: LocalQuestion, values: string[] = []) {
  if (question.type === 'blank') {
    return Array.from({ length: question.blanks.length }, (_, index) => String(values[index] ?? ''))
  }
  if (question.type === 'short_answer') return [String(values[0] ?? '')]
  return values.map((value) => String(value ?? ''))
}

function isTextCorrect(question: LocalQuestion, textAnswers: string[]) {
  if (question.type === 'short_answer') return false
  if (question.type !== 'blank') return false
  if (textAnswers.length !== question.blanks.length) return false
  return question.blanks.every((blank, index) => {
    const submitted = String(textAnswers[index] ?? '').trim()
    return blank.answers.map((answer) => String(answer).trim()).includes(submitted)
  })
}

function isChoiceCorrect(question: LocalQuestion, selectedOptionIds: number[]) {
  const correctIds = question.options.filter((option) => option.is_correct).map((option) => option.remote_option_id).sort((a, b) => a - b)
  const selected = [...selectedOptionIds].sort((a, b) => a - b)
  return correctIds.length === selected.length && correctIds.every((id, index) => id === selected[index])
}

function correctLabels(options: LocalOption[]) {
  return options.filter((option) => option.is_correct).map((option) => option.label)
}

function correctTextAnswers(blanks: LocalBlank[]) {
  return blanks.map((blank) => blank.answers)
}

function answerSnapshot(question: LocalQuestion, selectedOptionIds: number[], textAnswers: string[]) {
  const optionById = Object.fromEntries(question.options.map((option) => [option.remote_option_id, option]))
  return {
    selected_option_ids: selectedOptionIds,
    selected_labels: selectedOptionIds.map((id) => optionById[id]?.label).filter(Boolean),
    text_answers: textAnswers,
  }
}

function questionSnapshot(question: LocalQuestion) {
  return {
    type: question.type,
    stem: question.stem,
    options: question.options.map((option) => ({ id: option.remote_option_id, label: option.label, content: option.content })),
    blanks: question.blanks.map((blank) => ({ id: blank.remote_blank_id, label: blank.label, sort_order: blank.sort_order })),
    correct_option_ids: question.options.filter((option) => option.is_correct).map((option) => option.remote_option_id),
    correct_labels: correctLabels(question.options),
    correct_text_answers: correctTextAnswers(question.blanks),
    explanation: question.explanation,
  }
}

export async function createLocalSession(localBankId: number, mode = 'practice') {
  const bank = await getLocalBank(localBankId)
  if (!bank) throw new Error('本地题库不存在')
  const questions = await getLocalQuestions(localBankId)
  if (!questions.length) throw new Error('本地题库没有题目')
  const db = await getLocalDb()
  const startedAt = nowIso()
  await db.execute(
    `INSERT INTO local_practice_sessions (client_session_id, local_bank_id, remote_bank_id, mode, status, total_questions, started_at, sync_status)
     VALUES ($1, $2, $3, $4, 'in_progress', $5, $6, 'pending')`,
    [uuid(), localBankId, bank.remote_bank_id, mode, questions.length, startedAt],
  )
  const rows = await db.select<Array<{ id: number }>>('SELECT id FROM local_practice_sessions WHERE local_bank_id = $1 ORDER BY id DESC LIMIT 1', [localBankId])
  const sessionId = rows[0]?.id
  if (!sessionId) throw new Error('本地练习创建失败')
  for (const [index, question] of questions.entries()) {
    await db.execute('INSERT INTO local_session_questions (session_id, local_question_id, sort_order) VALUES ($1, $2, $3)', [sessionId, question.id, index])
  }
  return sessionId
}

export async function getLocalSession(sessionId: number) {
  const db = await getLocalDb()
  const rows = await db.select<SessionRow[]>('SELECT * FROM local_practice_sessions WHERE id = $1', [sessionId])
  return rows[0] ? rowToSession(rows[0]) : null
}

async function orderedQuestionsForSession(sessionId: number) {
  const db = await getLocalDb()
  const rows = await db.select<SessionQuestionRow[]>('SELECT local_question_id, sort_order FROM local_session_questions WHERE session_id = $1 ORDER BY sort_order ASC', [sessionId])
  if (!rows.length) return []
  const session = await getLocalSession(sessionId)
  if (!session) return []
  const questions = await getLocalQuestions(session.local_bank_id, { includeInactive: true })
  const byId = new Map(questions.map((question) => [question.id, question]))
  return rows.map((row) => byId.get(row.local_question_id)).filter(Boolean) as LocalQuestion[]
}

export async function getLocalSessionQuestions(sessionId: number): Promise<LocalPracticeQuestion[]> {
  const session = await getLocalSession(sessionId)
  if (!session) throw new Error('本地练习不存在')
  const db = await getLocalDb()
  const questions = await orderedQuestionsForSession(sessionId)
  const answerRows = await db.select<AnswerRow[]>('SELECT * FROM local_answers WHERE session_id = $1', [sessionId])
  const answersByQuestion = new Map(answerRows.map((answer) => [answer.local_question_id, answer]))
  const reveal = session.mode !== 'exam' || session.status === 'submitted'
  return questions.map((question) => {
    const answer = answersByQuestion.get(question.id)
    const selectedIds = answer ? JSON.parse(answer.selected_option_ids_json || '[]') : []
    const textAnswers = answer ? normalizeTextAnswers(question, JSON.parse(answer.text_answers_json || '[]')) : normalizeTextAnswers(question, [])
    const canReveal = Boolean(answer?.is_submitted && reveal)
    return {
      id: question.id,
      local_question_id: question.id,
      remote_question_id: question.remote_question_id,
      type: question.type,
      stem: question.stem,
      options: question.options.map((option) => ({ id: option.remote_option_id, label: option.label, content: option.content })),
      blanks: question.blanks.map((blank) => ({ id: blank.remote_blank_id, label: blank.label, sort_order: blank.sort_order })),
      answer_state: {
        is_answered: Boolean(answer?.is_submitted || (session.mode === 'exam' && answer)),
        selected_option_ids: selectedIds,
        text_answers: textAnswers,
        reveal: canReveal,
        is_correct: canReveal ? Boolean(answer?.is_correct) : null,
        correct_labels: canReveal ? correctLabels(question.options) : [],
        correct_text_answers: canReveal ? correctTextAnswers(question.blanks) : [],
        explanation: canReveal ? question.explanation : null,
      },
    }
  })
}

async function getQuestionInSession(sessionId: number, localQuestionId: number) {
  const questions = await orderedQuestionsForSession(sessionId)
  const question = questions.find((item) => item.id === localQuestionId)
  if (!question) throw new Error('题目不属于当前本地练习')
  return question
}

export async function saveLocalAnswer(sessionId: number, localQuestionId: number, selectedOptionIds: number[], textAnswers: string[], submit = true): Promise<LocalPracticeAnswerResult> {
  const session = await getLocalSession(sessionId)
  if (!session) throw new Error('本地练习不存在')
  if (session.status === 'submitted') throw new Error('本地练习已提交')
  const question = await getQuestionInSession(sessionId, localQuestionId)
  const db = await getLocalDb()
  const normalizedText = normalizeTextAnswers(question, textAnswers)
  const actualSelected = question.type === 'single' || question.type === 'multiple' ? selectedOptionIds : []
  const isCorrect = question.type === 'single' || question.type === 'multiple'
    ? isChoiceCorrect(question, actualSelected)
    : isTextCorrect(question, normalizedText)
  const isSubmitted = session.mode === 'exam' ? false : submit
  await db.execute(
    `INSERT INTO local_answers (session_id, local_question_id, selected_option_ids_json, text_answers_json, is_correct, is_submitted, answered_at)
     VALUES ($1, $2, $3, $4, $5, $6, $7)
     ON CONFLICT(session_id, local_question_id) DO UPDATE SET
       selected_option_ids_json = excluded.selected_option_ids_json,
       text_answers_json = excluded.text_answers_json,
       is_correct = excluded.is_correct,
       is_submitted = excluded.is_submitted,
       answered_at = excluded.answered_at`,
    [sessionId, localQuestionId, JSON.stringify(actualSelected), JSON.stringify(normalizedText), isCorrect ? 1 : 0, isSubmitted ? 1 : 0, nowIso()],
  )
  await db.execute("UPDATE local_practice_sessions SET sync_status = 'pending', sync_error = NULL WHERE id = $1", [sessionId])
  if (isSubmitted && !isCorrect) await createLocalMistakeAttempt(session, question, actualSelected, normalizedText)
  return {
    is_submitted: isSubmitted,
    reveal: session.mode !== 'exam',
    is_correct: session.mode !== 'exam' ? isCorrect : null,
    correct_option_ids: question.options.filter((option) => option.is_correct).map((option) => option.remote_option_id),
    correct_labels: correctLabels(question.options),
    correct_text_answers: correctTextAnswers(question.blanks),
    explanation: question.explanation,
  }
}

async function createLocalMistakeAttempt(session: LocalPracticeSession, question: LocalQuestion, selectedOptionIds: number[], textAnswers: string[]) {
  const db = await getLocalDb()
  await db.execute(
    `INSERT INTO local_mistake_attempts (session_id, local_bank_id, local_question_id, question_snapshot_json, user_answer_json, is_resolved, wrong_at)
     VALUES ($1, $2, $3, $4, $5, 0, $6)`,
    [
      session.id,
      session.local_bank_id,
      question.id,
      JSON.stringify(questionSnapshot(question)),
      JSON.stringify(answerSnapshot(question, selectedOptionIds, textAnswers)),
      nowIso(),
    ],
  )
}

export async function submitLocalSession(sessionId: number, commitDrafts = true) {
  const session = await getLocalSession(sessionId)
  if (!session) throw new Error('本地练习不存在')
  if (session.status === 'submitted') return session
  const db = await getLocalDb()
  if (session.mode === 'exam' && commitDrafts) {
    await db.execute('UPDATE local_answers SET is_submitted = 1 WHERE session_id = $1', [sessionId])
  }
  const answers = await db.select<AnswerRow[]>('SELECT * FROM local_answers WHERE session_id = $1 AND is_submitted = 1', [sessionId])
  const correctCount = answers.filter((answer) => Boolean(answer.is_correct)).length
  const score = session.total_questions ? Math.round((correctCount / session.total_questions) * 10000) / 100 : 0
  if (session.mode === 'exam') {
    const questions = await orderedQuestionsForSession(sessionId)
    const byId = new Map(questions.map((question) => [question.id, question]))
    for (const answer of answers) {
      if (answer.is_correct) continue
      const question = byId.get(answer.local_question_id)
      if (!question) continue
      await createLocalMistakeAttempt(session, question, JSON.parse(answer.selected_option_ids_json || '[]'), normalizeTextAnswers(question, JSON.parse(answer.text_answers_json || '[]')))
    }
  }
  await db.execute(
    "UPDATE local_practice_sessions SET status = 'submitted', correct_count = $1, score = $2, submitted_at = $3, sync_status = 'pending', sync_error = NULL WHERE id = $4",
    [correctCount, score, nowIso(), sessionId],
  )
  const updated = await getLocalSession(sessionId)
  if (!updated) throw new Error('本地练习提交失败')
  return updated
}

export async function getLocalResult(sessionId: number): Promise<LocalPracticeResult[]> {
  const questions = await orderedQuestionsForSession(sessionId)
  const db = await getLocalDb()
  const answers = await db.select<AnswerRow[]>('SELECT * FROM local_answers WHERE session_id = $1', [sessionId])
  const answerByQuestion = new Map(answers.map((answer) => [answer.local_question_id, answer]))
  return questions.map((question) => {
    const answer = answerByQuestion.get(question.id)
    const selectedOptionIds = answer?.is_submitted ? JSON.parse(answer.selected_option_ids_json || '[]') : []
    const textAnswers = answer?.is_submitted ? normalizeTextAnswers(question, JSON.parse(answer.text_answers_json || '[]')) : []
    const optionById = new Map(question.options.map((option) => [option.remote_option_id, option]))
    return {
      question_id: question.id,
      type: question.type,
      stem: question.stem,
      options: question.options.map((option) => ({ id: option.remote_option_id, label: option.label, content: option.content })),
      blanks: question.blanks.map((blank) => ({ id: blank.remote_blank_id, label: blank.label, sort_order: blank.sort_order })),
      selected_option_ids: selectedOptionIds,
      selected_labels: selectedOptionIds.map((id: number) => optionById.get(id)?.label).filter(Boolean) as string[],
      text_answers: textAnswers,
      correct_option_ids: question.options.filter((option) => option.is_correct).map((option) => option.remote_option_id),
      correct_labels: correctLabels(question.options),
      correct_text_answers: correctTextAnswers(question.blanks),
      is_correct: Boolean(answer?.is_submitted && answer.is_correct),
      is_unanswered: !answer?.is_submitted,
      explanation: question.explanation,
    }
  })
}

export async function listLocalHistory() {
  const db = await getLocalDb()
  const rows = await db.select<SessionRow[]>('SELECT * FROM local_practice_sessions ORDER BY started_at DESC, id DESC')
  return rows.map(rowToSession)
}

type LocalSyncResult = OfflinePracticeSyncResult & {
  downloaded: number
  skipped: number
}

export async function syncPendingLocalSessions(): Promise<LocalSyncResult> {
  const db = await getLocalDb()
  const sessions = await db.select<SessionRow[]>("SELECT * FROM local_practice_sessions WHERE sync_status != 'synced' ORDER BY started_at ASC")
  let uploadResult: OfflinePracticeSyncResult = { synced: [], failed: [] }
  const payloadSessions = []
  for (const session of sessions) {
    const orderRows = await db.select<SessionQuestionRow[]>('SELECT local_question_id, sort_order FROM local_session_questions WHERE session_id = $1 ORDER BY sort_order ASC', [session.id])
    const questions = await orderedQuestionsForSession(session.id)
    const byLocalId = new Map(questions.map((question) => [question.id, question]))
    const answerRows = await db.select<AnswerRow[]>('SELECT * FROM local_answers WHERE session_id = $1', [session.id])
    payloadSessions.push({
      client_session_id: session.client_session_id,
      remote_bank_id: session.remote_bank_id,
      mode: session.mode,
      status: session.status,
      question_order: orderRows.map((row) => byLocalId.get(row.local_question_id)?.remote_question_id).filter(Boolean),
      answers: answerRows.map((answer) => {
        const question = byLocalId.get(answer.local_question_id)
        return {
          question_id: question?.remote_question_id,
          selected_option_ids: JSON.parse(answer.selected_option_ids_json || '[]'),
          text_answers: JSON.parse(answer.text_answers_json || '[]'),
          is_submitted: Boolean(answer.is_submitted),
          answered_at: answer.answered_at,
        }
      }).filter((answer) => answer.question_id),
      started_at: session.started_at,
      submitted_at: session.submitted_at,
    })
  }
  if (payloadSessions.length) {
    const deviceId = await getDeviceId()
    uploadResult = await api<OfflinePracticeSyncResult>('/api/v2/offline/practice-sync', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId, sessions: payloadSessions }),
    })
    const syncedByClient = new Map(uploadResult.synced.map((item) => [item.client_session_id, item.remote_session_id]))
    const failedByClient = new Map(uploadResult.failed.map((item) => [item.client_session_id, item.message]))
    for (const session of sessions) {
      const remoteId = syncedByClient.get(session.client_session_id)
      if (remoteId) {
        await db.execute("UPDATE local_practice_sessions SET sync_status = 'synced', sync_error = NULL, remote_session_id = $1, synced_at = $2 WHERE id = $3", [remoteId, nowIso(), session.id])
      } else if (failedByClient.has(session.client_session_id)) {
        await db.execute("UPDATE local_practice_sessions SET sync_status = 'failed', sync_error = $1 WHERE id = $2", [failedByClient.get(session.client_session_id), session.id])
      }
    }
  }
  const pullResult = await pullRemotePracticeSessions()
  return { ...uploadResult, downloaded: pullResult.downloaded, skipped: pullResult.skipped }
}

async function pullRemotePracticeSessions() {
  const db = await getLocalDb()
  const banks = await listLocalBanks()
  let downloaded = 0
  let skipped = 0
  for (const bank of banks) {
    const localQuestions = await getLocalQuestions(bank.id, { includeInactive: true })
    const byRemoteQuestionId = new Map(localQuestions.map((question) => [question.remote_question_id, question]))
    let page = 1
    while (true) {
      const remotePage = await listHistory({ page, page_size: 100, bank_id: bank.remote_bank_id })
      for (const remoteSession of remotePage.items) {
        const exists = await db.select<SessionRow[]>('SELECT * FROM local_practice_sessions WHERE remote_session_id = $1 LIMIT 1', [remoteSession.id])
        if (exists.length) {
          skipped += 1
          continue
        }
        const imported = await importRemoteSession(bank.id, remoteSession, byRemoteQuestionId)
        if (imported) downloaded += 1
        else skipped += 1
      }
      if (page >= remotePage.total_pages) break
      page += 1
    }
  }
  return { downloaded, skipped }
}

async function importRemoteSession(localBankId: number, remoteSession: Awaited<ReturnType<typeof listHistory>>['items'][number], byRemoteQuestionId: Map<number, LocalQuestion>) {
  const db = await getLocalDb()
  const remoteRows = remoteSession.status === 'submitted'
    ? await getResult(remoteSession.id)
    : await getSessionQuestions(remoteSession.id)
  const ordered = remoteRows
    .map((row) => {
      const remoteQuestionId = 'question_id' in row ? Number(row.question_id) : Number(row.id)
      const question = byRemoteQuestionId.get(remoteQuestionId)
      return question ? { row, question } : null
    })
    .filter(Boolean) as Array<{ row: any; question: LocalQuestion }>
  if (!ordered.length || ordered.length !== remoteRows.length) return false

  await db.execute('BEGIN')
  try {
    await db.execute(
      `INSERT INTO local_practice_sessions (client_session_id, local_bank_id, remote_bank_id, mode, status, total_questions, correct_count, score, started_at, submitted_at, sync_status, sync_error, remote_session_id, synced_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'synced', NULL, $11, $12)`,
      [
        `remote-${remoteSession.id}`,
        localBankId,
        remoteSession.bank_id,
        remoteSession.mode,
        remoteSession.status,
        remoteSession.total_questions,
        remoteSession.correct_count,
        remoteSession.score,
        remoteSession.started_at,
        remoteSession.submitted_at,
        remoteSession.id,
        nowIso(),
      ],
    )
    const sessionRows = await db.select<Array<{ id: number }>>('SELECT id FROM local_practice_sessions WHERE remote_session_id = $1 ORDER BY id DESC LIMIT 1', [remoteSession.id])
    const localSessionId = sessionRows[0]?.id
    if (!localSessionId) throw new Error('远端练习记录导入失败')
    for (const [index, item] of ordered.entries()) {
      await db.execute('INSERT INTO local_session_questions (session_id, local_question_id, sort_order) VALUES ($1, $2, $3)', [localSessionId, item.question.id, index])
      const answerState = 'answer_state' in item.row ? item.row.answer_state : item.row
      const isSubmitted = remoteSession.status === 'submitted'
        ? !Boolean(item.row.is_unanswered)
        : Boolean(answerState?.is_answered)
      if (!isSubmitted) continue
      await db.execute(
        `INSERT INTO local_answers (session_id, local_question_id, selected_option_ids_json, text_answers_json, is_correct, is_submitted, answered_at)
         VALUES ($1, $2, $3, $4, $5, 1, $6)`,
        [
          localSessionId,
          item.question.id,
          JSON.stringify(answerState?.selected_option_ids || []),
          JSON.stringify(answerState?.text_answers || []),
          answerState?.is_correct ? 1 : 0,
          remoteSession.last_answered_at || remoteSession.submitted_at || remoteSession.started_at,
        ],
      )
    }
    await db.execute('COMMIT')
    return true
  } catch (error) {
    await db.execute('ROLLBACK')
    throw error
  }
}

async function getDeviceId() {
  const db = await getLocalDb()
  const rows = await db.select<Array<{ value: string }>>("SELECT value FROM client_meta WHERE key = 'device_id'")
  if (rows[0]?.value) return rows[0].value
  const id = uuid()
  await db.execute("INSERT INTO client_meta (key, value) VALUES ('device_id', $1)", [id])
  return id
}

export function typeLabel(type: QuestionType) {
  return ({ single: '单选题', multiple: '多选题', blank: '填空题', short_answer: '简答题' })[type]
}
