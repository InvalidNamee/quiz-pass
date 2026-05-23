import type { AIGenerationDraftQuestion, Question, QuestionOption } from '../../api/types'

export type QuestionForm = {
  type: 'single' | 'multiple'
  stem: string
  explanation: string
  difficulty: string | null
  options: Array<{ label: string; content: string; is_correct: boolean }>
  validation_status?: string
  validation_message?: string | null
}

export type EditableQuestion = Question | AIGenerationDraftQuestion

export function emptyQuestionForm(): QuestionForm {
  return {
    type: 'single',
    stem: '',
    explanation: '',
    difficulty: null,
    options: [
      { label: 'A', content: '', is_correct: true },
      { label: 'B', content: '', is_correct: false },
    ],
    validation_status: 'valid',
    validation_message: null,
  }
}

export function cloneQuestionForm(form: QuestionForm): QuestionForm {
  return {
    ...form,
    options: form.options.map((option) => ({ ...option })),
  }
}

export function relabelOptions(options: QuestionForm['options']) {
  options.forEach((option, index) => { option.label = String.fromCharCode(65 + index) })
}

export function normalizeQuestionForm(form: QuestionForm): QuestionForm {
  const next = cloneQuestionForm(form)
  relabelOptions(next.options)
  if (next.type === 'single') {
    const correctIndex = Math.max(0, next.options.findIndex((option) => option.is_correct))
    next.options.forEach((option, index) => { option.is_correct = index === correctIndex })
  }
  return next
}

export function questionToForm(question: EditableQuestion): QuestionForm {
  return normalizeQuestionForm({
    type: question.type,
    stem: question.stem || '',
    explanation: question.explanation || '',
    difficulty: question.difficulty || null,
    options: question.options.map((option: QuestionOption | AIGenerationDraftQuestion['options'][number]) => ({
      label: option.label,
      content: option.content,
      is_correct: Boolean(option.is_correct),
    })),
    validation_status: 'validation_status' in question ? question.validation_status : 'valid',
    validation_message: 'validation_message' in question ? question.validation_message : null,
  })
}

export function formToQuestionPayload(form: QuestionForm) {
  const normalized = normalizeQuestionForm(form)
  return {
    type: normalized.type,
    stem: normalized.stem.trim(),
    explanation: normalized.explanation.trim() || null,
    difficulty: normalized.difficulty || null,
    options: normalized.options.map((option) => ({
      label: option.label,
      content: option.content.trim(),
      is_correct: option.is_correct,
    })),
  }
}

export function formToDraftQuestion(form: QuestionForm, base?: AIGenerationDraftQuestion | null): AIGenerationDraftQuestion {
  const payload = formToQuestionPayload(form)
  return {
    id: base?.id ?? 0,
    type: payload.type,
    stem: payload.stem,
    explanation: payload.explanation,
    difficulty: payload.difficulty,
    options: payload.options,
    validation_status: base?.validation_status ?? form.validation_status ?? 'valid',
    validation_message: base?.validation_message ?? form.validation_message ?? null,
  }
}

export function validateQuestionForm(form: QuestionForm) {
  const stem = form.stem.trim()
  if (!stem) return '请输入题干'
  const filledOptions = form.options.filter((option) => option.content.trim())
  if (filledOptions.length < 2) return '至少需要两个有效选项'
  const correctCount = form.options.filter((option) => option.is_correct).length
  if (form.type === 'single' && correctCount !== 1) return '单选题必须且只能有一个正确答案'
  if (form.type === 'multiple' && correctCount < 2) return '多选题至少需要两个正确答案'
  return null
}

export function optionCountLabel(question: EditableQuestion) {
  return `${question.options.length} 个选项`
}

export function sourceLabel(source: string | undefined) {
  const map: Record<string, string> = { manual: '手动', json_import: 'JSON', ai_generated: 'AI' }
  return source ? map[source] || source : ''
}
