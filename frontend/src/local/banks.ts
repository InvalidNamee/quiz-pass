import { downloadBankPackage } from '../api/v2/banks'
import type { BankDownloadPackage } from '../api/types'
import { getLocalDb } from './db'
import type { LocalBank, LocalBlank, LocalOption, LocalQuestion } from './types'

type LocalBankRow = {
  id: number
  remote_bank_id: number
  title: string
  description: string | null
  owner_json: string
  tags_json: string
  content_hash: string
  question_count: number
  downloaded_at: string
  remote_updated_at: string
}

type LocalQuestionRow = {
  id: number
  local_bank_id: number
  remote_question_id: number
  type: LocalQuestion['type']
  stem: string
  explanation: string | null
  difficulty: string | null
  sort_order: number
  is_active: number
}

type LocalOptionRow = {
  id: number
  remote_option_id: number
  label: string
  content: string
  is_correct: number
  sort_order: number
}

type LocalBlankRow = {
  id: number
  remote_blank_id: number
  label: string
  answers_json: string
  sort_order: number
}

function nowIso() {
  return new Date().toISOString()
}

function rowToBank(row: LocalBankRow): LocalBank {
  return {
    id: row.id,
    remote_bank_id: row.remote_bank_id,
    title: row.title,
    description: row.description,
    owner: JSON.parse(row.owner_json),
    tags: JSON.parse(row.tags_json),
    content_hash: row.content_hash,
    question_count: row.question_count,
    downloaded_at: row.downloaded_at,
    remote_updated_at: row.remote_updated_at,
  }
}

export async function downloadBankToLocal(remoteBankId: number) {
  const pack = await downloadBankPackage(remoteBankId)
  return saveBankPackage(pack)
}

export async function saveBankPackage(pack: BankDownloadPackage) {
  const db = await getLocalDb()
  const downloadedAt = nowIso()
  await db.execute('BEGIN')
  try {
    await db.execute(
      `INSERT INTO local_banks (remote_bank_id, title, description, owner_json, tags_json, content_hash, question_count, downloaded_at, remote_updated_at)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
       ON CONFLICT(remote_bank_id) DO UPDATE SET
         title = excluded.title,
         description = excluded.description,
         owner_json = excluded.owner_json,
         tags_json = excluded.tags_json,
         content_hash = excluded.content_hash,
         question_count = excluded.question_count,
         downloaded_at = excluded.downloaded_at,
         remote_updated_at = excluded.remote_updated_at`,
      [
        pack.bank.id,
        pack.bank.title,
        pack.bank.description,
        JSON.stringify(pack.bank.owner),
        JSON.stringify(pack.tags),
        pack.content_hash,
        pack.questions.length,
        downloadedAt,
        pack.bank.updated_at,
      ],
    )
    const rows = await db.select<LocalBankRow[]>('SELECT * FROM local_banks WHERE remote_bank_id = $1', [pack.bank.id])
    const bank = rows[0]
    if (!bank) throw new Error('本地题库保存失败')

    await db.execute('UPDATE local_questions SET is_active = 0 WHERE local_bank_id = $1', [bank.id])
    for (const [index, question] of pack.questions.entries()) {
      await db.execute(
        `INSERT INTO local_questions (local_bank_id, remote_question_id, type, stem, explanation, difficulty, source, generated_model, sort_order, is_active)
         VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 1)
         ON CONFLICT(local_bank_id, remote_question_id) DO UPDATE SET
           type = excluded.type,
           stem = excluded.stem,
           explanation = excluded.explanation,
           difficulty = excluded.difficulty,
           source = excluded.source,
           generated_model = excluded.generated_model,
           sort_order = excluded.sort_order,
           is_active = 1`,
        [bank.id, question.id, question.type, question.stem, question.explanation, question.difficulty, question.source, question.generated_model, index],
      )
      const questionRows = await db.select<Array<{ id: number }>>(
        'SELECT id FROM local_questions WHERE local_bank_id = $1 AND remote_question_id = $2',
        [bank.id, question.id],
      )
      const localQuestionId = questionRows[0]?.id
      if (!localQuestionId) throw new Error('本地题目保存失败')
      await db.execute('DELETE FROM local_options WHERE local_question_id = $1', [localQuestionId])
      await db.execute('DELETE FROM local_blanks WHERE local_question_id = $1', [localQuestionId])
      for (const option of question.options) {
        await db.execute(
          `INSERT INTO local_options (local_question_id, remote_option_id, label, content, is_correct, sort_order)
           VALUES ($1, $2, $3, $4, $5, $6)`,
          [localQuestionId, option.id, option.label, option.content, option.is_correct ? 1 : 0, option.sort_order ?? 0],
        )
      }
      for (const blank of question.blanks) {
        await db.execute(
          `INSERT INTO local_blanks (local_question_id, remote_blank_id, label, answers_json, sort_order)
           VALUES ($1, $2, $3, $4, $5)`,
          [localQuestionId, blank.id, blank.label, JSON.stringify(blank.answers || []), blank.sort_order ?? 0],
        )
      }
    }

    await db.execute('COMMIT')
    return rowToBank(bank)
  } catch (error) {
    await db.execute('ROLLBACK')
    throw error
  }
}

export async function listLocalBanks() {
  const db = await getLocalDb()
  const rows = await db.select<LocalBankRow[]>('SELECT * FROM local_banks ORDER BY downloaded_at DESC, id DESC')
  return rows.map(rowToBank)
}

export async function getLocalBank(localBankId: number) {
  const db = await getLocalDb()
  const rows = await db.select<LocalBankRow[]>('SELECT * FROM local_banks WHERE id = $1', [localBankId])
  return rows[0] ? rowToBank(rows[0]) : null
}

export async function getLocalBankByRemoteId(remoteBankId: number) {
  const db = await getLocalDb()
  const rows = await db.select<LocalBankRow[]>('SELECT * FROM local_banks WHERE remote_bank_id = $1', [remoteBankId])
  return rows[0] ? rowToBank(rows[0]) : null
}

export async function getLocalQuestions(localBankId: number, options: { includeInactive?: boolean } = {}) {
  const db = await getLocalDb()
  const rows = await db.select<LocalQuestionRow[]>(
    `SELECT * FROM local_questions WHERE local_bank_id = $1${options.includeInactive ? '' : ' AND is_active = 1'} ORDER BY sort_order ASC, id ASC`,
    [localBankId],
  )
  const result: LocalQuestion[] = []
  for (const row of rows) {
    const options = await db.select<LocalOptionRow[]>('SELECT * FROM local_options WHERE local_question_id = $1 ORDER BY sort_order ASC, id ASC', [row.id])
    const blanks = await db.select<LocalBlankRow[]>('SELECT * FROM local_blanks WHERE local_question_id = $1 ORDER BY sort_order ASC, id ASC', [row.id])
    result.push({
      id: row.id,
      local_bank_id: row.local_bank_id,
      remote_question_id: row.remote_question_id,
      type: row.type,
      stem: row.stem,
      explanation: row.explanation,
      difficulty: row.difficulty,
      sort_order: row.sort_order,
      options: options.map((option): LocalOption => ({
        id: option.id,
        remote_option_id: option.remote_option_id,
        label: option.label,
        content: option.content,
        is_correct: Boolean(option.is_correct),
        sort_order: option.sort_order,
      })),
      blanks: blanks.map((blank): LocalBlank => ({
        id: blank.id,
        remote_blank_id: blank.remote_blank_id,
        label: blank.label,
        answers: JSON.parse(blank.answers_json || '[]'),
        sort_order: blank.sort_order,
      })),
    })
  }
  return result
}
