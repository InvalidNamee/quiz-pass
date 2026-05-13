<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type PracticeSession } from '../api/client'

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

const route = useRoute()
const router = useRouter()
const sessionId = Number(route.params.sessionId)
const session = ref<PracticeSession | null>(null)
const questions = ref<PracticeQuestion[]>([])
const currentIndex = ref(0)
const selected = ref<Record<number, number[]>>({})
const answerStatus = ref<Record<number, 'correct' | 'wrong'>>({})
const answerResults = ref<Record<number, AnswerResult>>({})
const answered = ref<Record<number, boolean>>({})

async function load() {
  session.value = await api<PracticeSession>(`/api/v1/practice/sessions/${sessionId}`)
  questions.value = await api<PracticeQuestion[]>(`/api/v1/practice/sessions/${sessionId}/questions`)
  const restoredSelected: Record<number, number[]> = {}
  const restoredAnswered: Record<number, boolean> = {}
  const restoredStatus: Record<number, 'correct' | 'wrong'> = {}
  const restoredResults: Record<number, AnswerResult> = {}
  questions.value.forEach((question) => {
    const state = question.answer_state
    if (state?.selected_option_ids?.length) restoredSelected[question.id] = state.selected_option_ids
    if (state?.is_answered) restoredAnswered[question.id] = true
    if (state?.reveal) {
      if (state.is_correct !== null) restoredStatus[question.id] = state.is_correct ? 'correct' : 'wrong'
      restoredResults[question.id] = {
        is_submitted: true,
        reveal: true,
        is_correct: state.is_correct,
        correct_option_ids: [],
        correct_labels: state.correct_labels,
        explanation: state.explanation,
      }
    }
  })
  const firstUnanswered = questions.value.findIndex((question) => !question.answer_state?.is_answered)
  currentIndex.value = firstUnanswered >= 0 ? firstUnanswered : 0
  selected.value = restoredSelected
  answered.value = restoredAnswered
  answerStatus.value = restoredStatus
  answerResults.value = restoredResults
}

function isLocked(questionId: number) {
  return Boolean(answered.value[questionId])
}

function shouldReveal(questionId: number) {
  return Boolean(answerResults.value[questionId]?.reveal)
}

function cardClass(question: PracticeQuestion, index: number) {
  const status = answerStatus.value[question.id]
  const current = index === currentIndex.value ? ' outline outline-2 outline-offset-2 outline-blue-600' : ''
  if (status === 'correct') return `border border-green-300 bg-green-50 text-green-800${current}`
  if (status === 'wrong') return `border border-red-300 bg-red-50 text-red-800${current}`
  if (index === currentIndex.value) return 'bg-blue-50 text-blue-700 outline outline-2 outline-offset-2 outline-blue-600'
  if (answered.value[question.id]) return 'border border-slate-300 bg-slate-100 text-slate-700'
  if (selected.value[question.id]?.length) return 'bg-blue-50 text-blue-900'
  return 'bg-white text-slate-700 border border-slate-200'
}

function hasSelection(questionId: number) {
  return Boolean(selected.value[questionId]?.length)
}

async function toggle(question: PracticeQuestion, optionId: number) {
  if (isLocked(question.id)) return
  const values = selected.value[question.id] ?? []
  if (question.type === 'single') {
    selected.value[question.id] = [optionId]
    if (session.value?.mode !== 'exam') await answer()
    return
  }
  selected.value[question.id] = values.includes(optionId) ? values.filter((id) => id !== optionId) : [...values, optionId]
}

async function answer() {
  const question = questions.value[currentIndex.value]
  if (isLocked(question.id)) return
  const result = await api<AnswerResult>(`/api/v1/practice/sessions/${sessionId}/answers`, {
    method: 'POST',
    body: JSON.stringify({ question_id: question.id, selected_option_ids: selected.value[question.id] ?? [] }),
  })
  answered.value[question.id] = true
  if (result.reveal && result.is_correct !== null) answerStatus.value[question.id] = result.is_correct ? 'correct' : 'wrong'
  answerResults.value[question.id] = result
}

async function submit() {
  await api<PracticeSession>(`/api/v1/practice/sessions/${sessionId}/submit`, { method: 'POST' })
  router.push(`/practice/result/${sessionId}`)
}

onMounted(load)
</script>

<template>
  <section v-if="questions.length">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold">第 {{ currentIndex + 1 }} / {{ questions.length }} 题</h1>
      <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="submit">交卷</button>
    </div>
    <div class="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_220px]">
    <article
      class="grid gap-4 rounded-lg border bg-white p-5 shadow-sm"
      :class="{ 'border-green-300 bg-green-50': answerStatus[questions[currentIndex].id] === 'correct', 'border-red-300 bg-red-50': answerStatus[questions[currentIndex].id] === 'wrong', 'border-slate-200': !answerStatus[questions[currentIndex].id] }"
    >
      <div class="w-fit rounded-md bg-cyan-50 px-2 py-1 text-sm font-bold text-cyan-900">{{ questions[currentIndex].type === 'single' ? '单选' : '多选' }}</div>
      <h2 class="text-xl font-semibold">{{ questions[currentIndex].stem }}</h2>
      <label v-for="option in questions[currentIndex].options" :key="option.id" class="flex items-center gap-2">
        <input
          :type="questions[currentIndex].type === 'single' ? 'radio' : 'checkbox'"
          :checked="(selected[questions[currentIndex].id] ?? []).includes(option.id)"
          :disabled="isLocked(questions[currentIndex].id)"
          @change="toggle(questions[currentIndex], option.id)"
        />
        {{ option.label }}. {{ option.content }}
      </label>
      <button
        v-if="questions[currentIndex].type === 'multiple' || session?.mode === 'exam'"
        class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        :disabled="isLocked(questions[currentIndex].id) || !hasSelection(questions[currentIndex].id)"
        @click="answer"
      >
        提交本题
      </button>
      <p v-if="answerStatus[questions[currentIndex].id]" class="font-bold" :class="answerStatus[questions[currentIndex].id] === 'correct' ? 'text-green-800' : 'text-red-800'">
        {{ answerStatus[questions[currentIndex].id] === 'correct' ? '回答正确' : '回答错误' }}
      </p>
      <p v-else-if="isLocked(questions[currentIndex].id)" class="font-bold text-slate-500">已提交答案</p>
      <div v-if="shouldReveal(questions[currentIndex].id)" class="grid gap-2 rounded-md bg-slate-100 p-3 text-sm text-slate-700">
        <p class="m-0 font-bold">正确答案：{{ answerResults[questions[currentIndex].id].correct_labels.join('、') }}</p>
        <p v-if="answerResults[questions[currentIndex].id].explanation" class="m-0">解析：{{ answerResults[questions[currentIndex].id].explanation }}</p>
      </div>
    </article>
    <aside class="sticky top-5 grid grid-cols-5 gap-2 self-start rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:grid-cols-4">
      <button
        v-for="(question, index) in questions"
        :key="question.id"
        class="min-h-10 rounded-md"
        :class="cardClass(question, index)"
        @click="currentIndex = index"
      >
        {{ index + 1 }}
      </button>
    </aside>
    </div>
  </section>
</template>
