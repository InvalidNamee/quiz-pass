import type { AIGenerationDraftQuestion, Question, QuestionOption, QuestionType } from '../../api/types'

export type QuestionForm = {
  type: QuestionType
  stem: string
  explanation: string
  difficulty: string | null
  options: Array<{ label: string; content: string; is_correct: boolean }>
  blanks: Array<{ label: string; answers: string[] }>
  validation_status?: string
  validation_message?: string | null
}

export type EditableQuestion = Question | AIGenerationDraftQuestion
export const MAX_OPTION_COUNT = 26

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
    blanks: [{ label: '1', answers: [''] }],
    validation_status: 'valid',
    validation_message: null,
  }
}

export function cloneQuestionForm(form: QuestionForm): QuestionForm {
  return {
    ...form,
    options: form.options.map((option) => ({ ...option })),
    blanks: form.blanks.map((blank) => ({ label: blank.label, answers: [...blank.answers] })),
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
  if (next.type === 'blank') {
    next.options = []
    next.blanks.forEach((blank, index) => { blank.label = String(index + 1) })
  }
  if (next.type === 'short_answer') {
    next.options = []
    next.blanks = []
  }
  if (next.type === 'single' || next.type === 'multiple') {
    next.blanks = []
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
    blanks: (question.blanks || []).map((blank) => ({
      label: blank.label,
      answers: [...blank.answers],
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
    blanks: normalized.blanks.map((blank) => ({
      label: blank.label,
      answers: blank.answers.map((answer) => answer.trim()).filter(Boolean),
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
    blanks: payload.blanks,
    validation_status: base?.validation_status ?? form.validation_status ?? 'valid',
    validation_message: base?.validation_message ?? form.validation_message ?? null,
  }
}

export function validateQuestionForm(form: QuestionForm) {
  const stem = form.stem.trim()
  if (!stem) return '请输入题干'
  if (form.type === 'single' || form.type === 'multiple') {
    const filledOptions = form.options.filter((option) => option.content.trim())
    if (filledOptions.length < 2) return '至少需要两个有效选项'
    if (form.options.length > MAX_OPTION_COUNT) return '最多 26 个选项'
    const correctCount = form.options.filter((option) => option.is_correct).length
    if (form.type === 'single' && correctCount !== 1) return '单选题必须且只能有一个正确答案'
    if (form.type === 'multiple' && correctCount < 2) return '多选题至少需要两个正确答案'
  }
  if (form.type === 'blank') {
    if (!form.blanks.length) return '填空题至少需要一个空'
    const labels = form.blanks.map((blank) => blank.label.trim())
    for (const label of labels) {
      if (!stem.includes(`{{${label}}}`)) return `题干缺少 {{${label}}} 占位符`
    }
    const placeholders = Array.from(stem.matchAll(/\{\{([^{}]+)\}\}/g)).map((match) => match[1])
    if (placeholders.length !== labels.length || placeholders.some((label) => !labels.includes(label))) return '题干占位符必须和空位一致'
    if (form.blanks.some((blank) => !blank.answers.some((answer) => answer.trim()))) return '每个空至少需要一个答案'
  }
  if (form.type === 'short_answer' && !form.explanation.trim()) return '简答题需要在解析中填写给分点'
  return null
}

export function optionCountLabel(question: EditableQuestion) {
  if (question.type === 'blank') return `${question.blanks?.length || 0} 个空`
  if (question.type === 'short_answer') return '简答'
  return `${question.options.length} 个选项`
}

export function questionTypeLabel(type: QuestionType) {
  const map: Record<QuestionType, string> = { single: '单选', multiple: '多选', blank: '填空', short_answer: '简答' }
  return map[type]
}

export function questionTypeTag(type: QuestionType): 'primary' | 'warning' | 'success' | 'info' {
  const map: Record<QuestionType, 'primary' | 'warning' | 'success' | 'info'> = { single: 'primary', multiple: 'warning', blank: 'success', short_answer: 'info' }
  return map[type]
}

export function sourceLabel(source: string | undefined) {
  const map: Record<string, string> = { manual: '手动', json_import: 'JSON', ai_generated: 'AI' }
  return source ? map[source] || source : ''
}
