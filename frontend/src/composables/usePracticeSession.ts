import { ref, computed } from 'vue'
import { getSession, getSessionQuestions, answerQuestion, saveAnswerDraft, submitSession } from '../api/v2/practice'
import type { PracticeSession, QuestionType } from '../api/types'
import { useToast } from './useToast'

type PracticeQuestion = {
  id: number
  type: QuestionType
  stem: string
  options: { id: number; label: string; content: string }[]
  blanks: { id: number; label: string; sort_order: number }[]
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
}

type AnswerResult = {
  is_submitted: boolean
  reveal: boolean
  is_correct: boolean | null
  correct_option_ids: number[]
  correct_labels: string[]
  correct_text_answers: string[][]
  explanation: string | null
}

export function usePracticeSession(sessionId: number) {
  const toast = useToast()
  const session = ref<PracticeSession | null>(null)
  const questions = ref<PracticeQuestion[]>([])
  const currentIndex = ref(0)
  const selected = ref<Record<number, number[]>>({})
  const textAnswers = ref<Record<number, string[]>>({})
  const answerStatus = ref<Record<number, 'correct' | 'wrong'>>({})
  const answerResults = ref<Record<number, AnswerResult>>({})
  const answered = ref<Record<number, boolean>>({})
  const lastSyncedSelections = ref<Record<number, string>>({})
  const draftSaving = ref<Record<number, boolean>>({})
  const loading = ref(true)

  const currentQuestion = computed(() => questions.value[currentIndex.value] || null)
  const totalQuestions = computed(() => questions.value.length)

  function isLocked(questionId: number) {
    return session.value?.mode !== 'exam' && Boolean(answered.value[questionId])
  }

  function shouldReveal(questionId: number) {
    return Boolean(answerResults.value[questionId]?.reveal)
  }

  function hasSelection(questionId: number) {
    return Boolean(selected.value[questionId]?.length || textAnswers.value[questionId]?.some((answer) => answer.trim()))
  }

  function questionStatus(questionId: number): 'correct' | 'wrong' | 'answered' | 'selected' | 'none' {
    if (answerStatus.value[questionId] === 'correct') return 'correct'
    if (answerStatus.value[questionId] === 'wrong') return 'wrong'
    if (answered.value[questionId]) return 'answered'
    if (selected.value[questionId]?.length || textAnswers.value[questionId]?.some((answer) => answer.trim())) return 'selected'
    return 'none'
  }

  function selectionKey(optionIds: number[] = []) {
    return [...optionIds].sort((a, b) => a - b).join(',')
  }

  function textKey(values: string[] = []) {
    return values.join('\u0000')
  }

  function answerKey(question: PracticeQuestion) {
    return question.type === 'single' || question.type === 'multiple'
      ? `choice:${selectionKey(selected.value[question.id] ?? [])}`
      : `text:${textKey(textAnswers.value[question.id] ?? [])}`
  }

  async function load() {
    loading.value = true
    try {
      const [sessionData, questionsData] = await Promise.all([getSession(sessionId), getSessionQuestions(sessionId)])
      session.value = sessionData
      questions.value = questionsData

      const restored: Record<number, number[]> = {}
      const restoredText: Record<number, string[]> = {}
      const restoredAnswered: Record<number, boolean> = {}
      const restoredStatus: Record<number, 'correct' | 'wrong'> = {}
      const restoredResults: Record<number, AnswerResult> = {}
      lastSyncedSelections.value = {}

      questions.value.forEach((q) => {
        const state = q.answer_state
        if (state?.selected_option_ids?.length) {
          restored[q.id] = state.selected_option_ids
          lastSyncedSelections.value[q.id] = `choice:${selectionKey(state.selected_option_ids)}`
        }
        if (state?.text_answers?.length) {
          restoredText[q.id] = state.text_answers
          lastSyncedSelections.value[q.id] = `text:${textKey(state.text_answers)}`
        }
        if (state?.is_answered) restoredAnswered[q.id] = true
        if (state?.reveal) {
          if (state.is_correct !== null) restoredStatus[q.id] = state.is_correct ? 'correct' : 'wrong'
          restoredResults[q.id] = {
            is_submitted: true, reveal: true, is_correct: state.is_correct,
            correct_option_ids: [], correct_labels: state.correct_labels, correct_text_answers: state.correct_text_answers, explanation: state.explanation,
          }
        }
      })

      const firstUnanswered = questions.value.findIndex((q) => !q.answer_state?.is_answered)
      currentIndex.value = firstUnanswered >= 0 ? firstUnanswered : 0
      selected.value = restored
      textAnswers.value = restoredText
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

  async function setSelection(question: PracticeQuestion, optionIds: number[]) {
    if (isLocked(question.id)) return
    selected.value[question.id] = optionIds
    if (question.type === 'single' && session.value?.mode !== 'exam' && optionIds.length) await submitAnswer()
  }

  function setTextAnswers(question: PracticeQuestion, values: string[]) {
    if (isLocked(question.id)) return
    textAnswers.value[question.id] = values
  }

  async function submitAnswer() {
    const q = currentQuestion.value
    if (!q || isLocked(q.id)) return
    try {
      const result = await answerQuestion(sessionId, q.id, selected.value[q.id] ?? [], textAnswers.value[q.id] ?? [])
      answered.value[q.id] = true
      if (result.reveal && result.is_correct !== null) answerStatus.value[q.id] = result.is_correct ? 'correct' : 'wrong'
      answerResults.value[q.id] = result
      lastSyncedSelections.value[q.id] = answerKey(q)
      toast.show(session.value?.mode === 'exam' ? '答案已保存' : '答案已同步', 'success')
    } catch (error) {
      toast.show(error instanceof Error ? error.message : '答案同步失败', 'error')
      throw error
    }
  }

  async function submitAll() {
    await saveDraftIfChanged(currentQuestion.value)
    await submitSession(sessionId)
  }

  async function saveDraftIfChanged(question = currentQuestion.value) {
    if (!question || session.value?.status === 'submitted' || isLocked(question.id)) return
    const values = selected.value[question.id] ?? []
    const key = answerKey(question)
    if (key === 'choice:' && !lastSyncedSelections.value[question.id]) return
    if (key === 'text:' && !lastSyncedSelections.value[question.id]) return
    if (lastSyncedSelections.value[question.id] === key || draftSaving.value[question.id]) return
    try {
      draftSaving.value[question.id] = true
      await saveAnswerDraft(sessionId, question.id, values, textAnswers.value[question.id] ?? [])
      lastSyncedSelections.value[question.id] = key
    } catch (error) {
      toast.show(error instanceof Error ? error.message : '答案草稿保存失败', 'error')
      throw error
    } finally {
      draftSaving.value[question.id] = false
    }
  }

  async function previousQuestion() {
    await saveDraftIfChanged()
    if (currentIndex.value > 0) currentIndex.value -= 1
  }

  async function nextQuestion() {
    await saveDraftIfChanged()
    if (currentIndex.value < questions.value.length - 1) currentIndex.value += 1
  }

  async function goToQuestion(index: number) {
    if (index === currentIndex.value) return
    await saveDraftIfChanged()
    currentIndex.value = index
  }

  return {
    session, questions, currentIndex, selected, textAnswers, answerStatus, answerResults, answered,
    loading, currentQuestion, totalQuestions,
    load, toggle, setSelection, setTextAnswers, submitAnswer, submitAll, saveDraftIfChanged, previousQuestion, nextQuestion, goToQuestion,
    isLocked, shouldReveal, hasSelection, questionStatus,
  }
}
