import type { BankOwner, QuestionBankTag, QuestionType } from '../api/types'

export type LocalBank = {
  id: number
  remote_bank_id: number
  title: string
  description: string | null
  owner: BankOwner
  tags: QuestionBankTag[]
  content_hash: string
  question_count: number
  downloaded_at: string
  remote_updated_at: string
  sync_status?: string
}

export type LocalOption = {
  id: number
  remote_option_id: number
  label: string
  content: string
  is_correct: boolean
  sort_order: number
}

export type LocalBlank = {
  id: number
  remote_blank_id: number
  label: string
  answers: string[]
  sort_order: number
}

export type LocalQuestion = {
  id: number
  local_bank_id: number
  remote_question_id: number
  type: QuestionType
  stem: string
  explanation: string | null
  difficulty: string | null
  options: LocalOption[]
  blanks: LocalBlank[]
  sort_order: number
}

export type LocalPracticeSession = {
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

export type LocalPracticeQuestion = {
  id: number
  type: QuestionType
  stem: string
  options: Array<{ id: number; label: string; content: string }>
  blanks: Array<{ id: number; label: string; sort_order: number }>
  answer_state: {
    is_answered: boolean
    selected_option_ids: number[]
    text_answers: string[]
    reveal: boolean
    is_correct: boolean | null
    correct_labels: string[]
    correct_text_answers: string[][]
    explanation: string | null
  }
  local_question_id: number
  remote_question_id: number
}

export type LocalPracticeAnswerResult = {
  is_submitted: boolean
  reveal: boolean
  is_correct: boolean | null
  correct_option_ids: number[]
  correct_labels: string[]
  correct_text_answers: string[][]
  explanation: string | null
}

export type LocalPracticeResult = {
  question_id: number
  type: QuestionType
  stem: string
  options: Array<{ id: number; label: string; content: string }>
  blanks: Array<{ id: number; label: string; sort_order: number }>
  selected_option_ids: number[]
  selected_labels: string[]
  text_answers: string[]
  correct_option_ids: number[]
  correct_labels: string[]
  correct_text_answers: string[][]
  is_correct: boolean
  is_unanswered: boolean
  explanation: string | null
}
