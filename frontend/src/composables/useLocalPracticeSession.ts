import { computed, ref } from 'vue'
import { getLocalSession, getLocalSessionQuestions, saveLocalAnswer, submitLocalSession } from '../local/practice'
import type { LocalPracticeAnswerResult, LocalPracticeQuestion, LocalPracticeSession } from '../local/types'
import { useToast } from './useToast'

export function useLocalPracticeSession(sessionId: number) {
  const toast = useToast()
  const session = ref<LocalPracticeSession | null>(null)
  const questions = ref<LocalPracticeQuestion[]>([])
  const currentIndex = ref(0)
  const selected = ref<Record<number, number[]>>({})
  const textAnswers = ref<Record<number, string[]>>({})
  const answerStatus = ref<Record<number, 'correct' | 'wrong'>>({})
  const answerResults = ref<Record<number, LocalPracticeAnswerResult>>({})
  const answered = ref<Record<number, boolean>>({})
  const loading = ref(true)

  const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
  const totalQuestions = computed(() => questions.value.length)

  function normalizeTextAnswers(question: LocalPracticeQuestion, values: string[] = []) {
    if (question.type === 'blank') return Array.from({ length: question.blanks.length }, (_, index) => String(values[index] ?? ''))
    if (question.type === 'short_answer') return [String(values[0] ?? '')]
    return values.map((value) => String(value ?? ''))
  }

  function isLocked(questionId: number) {
    return session.value?.mode !== 'exam' && Boolean(answered.value[questionId])
  }

  function shouldReveal(questionId: number) {
    return Boolean(answerResults.value[questionId]?.reveal)
  }

  function questionStatus(questionId: number): 'correct' | 'wrong' | 'answered' | 'selected' | 'none' {
    if (answerStatus.value[questionId] === 'correct') return 'correct'
    if (answerStatus.value[questionId] === 'wrong') return 'wrong'
    if (answered.value[questionId]) return 'answered'
    if (selected.value[questionId]?.length || textAnswers.value[questionId]?.some((answer) => answer.trim())) return 'selected'
    return 'none'
  }

  async function load() {
    loading.value = true
    try {
      const [sessionData, questionData] = await Promise.all([getLocalSession(sessionId), getLocalSessionQuestions(sessionId)])
      if (!sessionData) throw new Error('本地练习不存在')
      session.value = sessionData
      questions.value = questionData
      const restoredSelected: Record<number, number[]> = {}
      const restoredText: Record<number, string[]> = {}
      const restoredAnswered: Record<number, boolean> = {}
      const restoredStatus: Record<number, 'correct' | 'wrong'> = {}
      const restoredResults: Record<number, LocalPracticeAnswerResult> = {}
      for (const question of questionData) {
        const state = question.answer_state
        restoredSelected[question.id] = state.selected_option_ids || []
        restoredText[question.id] = normalizeTextAnswers(question, state.text_answers || [])
        if (state.is_answered) restoredAnswered[question.id] = true
        if (state.reveal) {
          if (state.is_correct !== null) restoredStatus[question.id] = state.is_correct ? 'correct' : 'wrong'
          restoredResults[question.id] = {
            is_submitted: true,
            reveal: true,
            is_correct: state.is_correct,
            correct_option_ids: [],
            correct_labels: state.correct_labels,
            correct_text_answers: state.correct_text_answers,
            explanation: state.explanation,
          }
        }
      }
      selected.value = restoredSelected
      textAnswers.value = restoredText
      answered.value = restoredAnswered
      answerStatus.value = restoredStatus
      answerResults.value = restoredResults
    } finally {
      loading.value = false
    }
  }

  async function toggle(question: LocalPracticeQuestion, optionId: number) {
    if (isLocked(question.id)) return
    const values = selected.value[question.id] ?? []
    if (question.type === 'single') {
      selected.value[question.id] = [optionId]
      if (session.value?.mode !== 'exam') await submitAnswer()
    } else {
      selected.value[question.id] = values.includes(optionId) ? values.filter((id) => id !== optionId) : [...values, optionId]
    }
  }

  async function setSelection(question: LocalPracticeQuestion, optionIds: number[]) {
    if (isLocked(question.id)) return
    selected.value[question.id] = optionIds
    if (question.type === 'single' && session.value?.mode !== 'exam' && optionIds.length) await submitAnswer()
  }

  function setTextAnswers(question: LocalPracticeQuestion, values: string[]) {
    if (isLocked(question.id)) return
    textAnswers.value[question.id] = normalizeTextAnswers(question, values)
  }

  async function submitAnswer() {
    const question = currentQuestion.value
    if (!question || isLocked(question.id)) return
    const normalizedText = normalizeTextAnswers(question, textAnswers.value[question.id] ?? [])
    textAnswers.value[question.id] = normalizedText
    const result = await saveLocalAnswer(sessionId, question.id, selected.value[question.id] ?? [], normalizedText, true)
    answered.value[question.id] = true
    if (result.reveal && result.is_correct !== null) answerStatus.value[question.id] = result.is_correct ? 'correct' : 'wrong'
    answerResults.value[question.id] = result
    toast.show(session.value?.mode === 'exam' ? '答案已缓存到本机' : '答案已保存到本机', 'success')
  }

  async function saveDraftIfChanged(question = currentQuestion.value) {
    if (!question || session.value?.status === 'submitted' || isLocked(question.id)) return
    const normalizedText = normalizeTextAnswers(question, textAnswers.value[question.id] ?? [])
    await saveLocalAnswer(sessionId, question.id, selected.value[question.id] ?? [], normalizedText, false)
  }

  async function submitAll(options: { commit_drafts?: boolean } = {}) {
    if (options.commit_drafts ?? true) await saveDraftIfChanged(currentQuestion.value)
    session.value = await submitLocalSession(sessionId, options.commit_drafts ?? true)
  }

  async function goToQuestion(index: number) {
    if (index === currentIndex.value) return
    await saveDraftIfChanged()
    currentIndex.value = index
  }

  function setCurrentIndex(index: number) {
    currentIndex.value = Math.min(Math.max(index, 0), Math.max(questions.value.length - 1, 0))
  }

  return {
    session,
    questions,
    currentIndex,
    selected,
    textAnswers,
    answerStatus,
    answerResults,
    answered,
    loading,
    currentQuestion,
    totalQuestions,
    load,
    toggle,
    setSelection,
    setTextAnswers,
    submitAnswer,
    submitAll,
    saveDraftIfChanged,
    goToQuestion,
    setCurrentIndex,
    isLocked,
    shouldReveal,
    questionStatus,
  }
}
