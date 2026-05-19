import { ref, computed } from 'vue'
import { getSession, getSessionQuestions, answerQuestion, submitSession } from '../api/v2/practice'
import type { PracticeSession } from '../api/types'

type PracticeQuestion = {
  id: number
  type: 'single' | 'multiple'
  stem: string
  options: { id: number; label: string; content: string }[]
  answer_state: {
    is_answered: boolean
    selected_option_ids: number[]
    reveal: boolean
    is_correct: boolean | null
    correct_labels: string[]
    explanation: string | null
  }
}

type AnswerResult = {
  is_submitted: boolean
  reveal: boolean
  is_correct: boolean | null
  correct_option_ids: number[]
  correct_labels: string[]
  explanation: string | null
}

export function usePracticeSession(sessionId: number) {
  const session = ref<PracticeSession | null>(null)
  const questions = ref<PracticeQuestion[]>([])
  const currentIndex = ref(0)
  const selected = ref<Record<number, number[]>>({})
  const answerStatus = ref<Record<number, 'correct' | 'wrong'>>({})
  const answerResults = ref<Record<number, AnswerResult>>({})
  const answered = ref<Record<number, boolean>>({})
  const loading = ref(true)

  const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
  const totalQuestions = computed(() => questions.value.length)

  function isLocked(questionId: number) {
    return Boolean(answered.value[questionId])
  }

  function shouldReveal(questionId: number) {
    return Boolean(answerResults.value[questionId]?.reveal)
  }

  function hasSelection(questionId: number) {
    return Boolean(selected.value[questionId]?.length)
  }

  function questionStatus(questionId: number): 'correct' | 'wrong' | 'answered' | 'selected' | 'none' {
    if (answerStatus.value[questionId] === 'correct') return 'correct'
    if (answerStatus.value[questionId] === 'wrong') return 'wrong'
    if (answered.value[questionId]) return 'answered'
    if (selected.value[questionId]?.length) return 'selected'
    return 'none'
  }

  async function load() {
    loading.value = true
    try {
      const [sessionData, questionsData] = await Promise.all([getSession(sessionId), getSessionQuestions(sessionId)])
      session.value = sessionData
      questions.value = questionsData

      const restored: Record<number, number[]> = {}
      const restoredAnswered: Record<number, boolean> = {}
      const restoredStatus: Record<number, 'correct' | 'wrong'> = {}
      const restoredResults: Record<number, AnswerResult> = {}

      questions.value.forEach((q) => {
        const state = q.answer_state
        if (state?.selected_option_ids?.length) restored[q.id] = state.selected_option_ids
        if (state?.is_answered) restoredAnswered[q.id] = true
        if (state?.reveal) {
          if (state.is_correct !== null) restoredStatus[q.id] = state.is_correct ? 'correct' : 'wrong'
          restoredResults[q.id] = {
            is_submitted: true, reveal: true, is_correct: state.is_correct,
            correct_option_ids: [], correct_labels: state.correct_labels, explanation: state.explanation,
          }
        }
      })

      const firstUnanswered = questions.value.findIndex((q) => !q.answer_state?.is_answered)
      currentIndex.value = firstUnanswered >= 0 ? firstUnanswered : 0
      selected.value = restored
      answered.value = restoredAnswered
      answerStatus.value = restoredStatus
      answerResults.value = restoredResults
    } finally {
      loading.value = false
    }
  }

  async function toggle(question: PracticeQuestion, optionId: number) {
    if (isLocked(question.id)) return
    const values = selected.value[question.id] ?? []
    if (question.type === 'single') {
      selected.value[question.id] = [optionId]
      if (session.value?.mode !== 'exam') await submitAnswer()
    } else {
      selected.value[question.id] = values.includes(optionId)
        ? values.filter(id => id !== optionId)
        : [...values, optionId]
    }
  }

  async function submitAnswer() {
    const q = currentQuestion.value
    if (!q || isLocked(q.id)) return
    const result = await answerQuestion(sessionId, q.id, selected.value[q.id] ?? [])
    answered.value[q.id] = true
    if (result.reveal && result.is_correct !== null) answerStatus.value[q.id] = result.is_correct ? 'correct' : 'wrong'
    answerResults.value[q.id] = result
  }

  async function submitAll() {
    await submitSession(sessionId)
  }

  function previousQuestion() {
    if (currentIndex.value > 0) currentIndex.value -= 1
  }

  function nextQuestion() {
    if (currentIndex.value < questions.value.length - 1) currentIndex.value += 1
  }

  function goToQuestion(index: number) {
    currentIndex.value = index
  }

  return {
    session, questions, currentIndex, selected, answerStatus, answerResults, answered,
    loading, currentQuestion, totalQuestions,
    load, toggle, submitAnswer, submitAll, previousQuestion, nextQuestion, goToQuestion,
    isLocked, shouldReveal, hasSelection, questionStatus,
  }
}
