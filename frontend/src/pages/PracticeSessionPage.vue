<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type PracticeSession } from '../api/client'

type PracticeQuestion = {
  id: number
  type: 'single' | 'multiple'
  stem: string
  options: { id: number; label: string; content: string }[]
}

const route = useRoute()
const router = useRouter()
const sessionId = Number(route.params.sessionId)
const session = ref<PracticeSession | null>(null)
const questions = ref<PracticeQuestion[]>([])
const currentIndex = ref(0)
const selected = ref<Record<number, number[]>>({})
const answerStatus = ref<Record<number, 'correct' | 'wrong'>>({})

async function load() {
  session.value = await api<PracticeSession>(`/api/v1/practice/sessions/${sessionId}`)
  questions.value = await api<PracticeQuestion[]>(`/api/v1/practice/sessions/${sessionId}/questions`)
}

function toggle(question: PracticeQuestion, optionId: number) {
  const values = selected.value[question.id] ?? []
  if (question.type === 'single') {
    selected.value[question.id] = [optionId]
    return
  }
  selected.value[question.id] = values.includes(optionId) ? values.filter((id) => id !== optionId) : [...values, optionId]
}

async function answer() {
  const question = questions.value[currentIndex.value]
  const result = await api<{ is_correct: boolean }>(`/api/v1/practice/sessions/${sessionId}/answers`, {
    method: 'POST',
    body: JSON.stringify({ question_id: question.id, selected_option_ids: selected.value[question.id] ?? [] }),
  })
  answerStatus.value[question.id] = result.is_correct ? 'correct' : 'wrong'
  if (question.type === 'single' && currentIndex.value < questions.value.length - 1) currentIndex.value += 1
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
      :class="{ 'border-green-600 bg-green-50': answerStatus[questions[currentIndex].id] === 'correct', 'border-red-600 bg-red-50': answerStatus[questions[currentIndex].id] === 'wrong', 'border-slate-200': !answerStatus[questions[currentIndex].id] }"
    >
      <div class="w-fit rounded-md bg-cyan-50 px-2 py-1 text-sm font-bold text-cyan-900">{{ questions[currentIndex].type === 'single' ? '单选' : '多选' }}</div>
      <h2 class="text-xl font-semibold">{{ questions[currentIndex].stem }}</h2>
      <label v-for="option in questions[currentIndex].options" :key="option.id" class="flex items-center gap-2">
        <input
          :type="questions[currentIndex].type === 'single' ? 'radio' : 'checkbox'"
          :checked="(selected[questions[currentIndex].id] ?? []).includes(option.id)"
          @change="toggle(questions[currentIndex], option.id)"
        />
        {{ option.label }}. {{ option.content }}
      </label>
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="answer">提交本题</button>
      <p v-if="answerStatus[questions[currentIndex].id]" class="font-bold text-green-700">
        {{ answerStatus[questions[currentIndex].id] === 'correct' ? '回答正确' : '回答错误' }}
      </p>
    </article>
    <aside class="sticky top-5 grid grid-cols-5 gap-2 self-start rounded-lg border border-slate-200 bg-white p-4 shadow-sm lg:grid-cols-4">
      <button
        v-for="(question, index) in questions"
        :key="question.id"
        class="min-h-10 rounded-md bg-slate-100 text-slate-900"
        :class="{ 'outline outline-2 outline-offset-2 outline-blue-600': index === currentIndex, 'bg-slate-300': selected[question.id]?.length, 'bg-green-700 text-white': answerStatus[question.id] === 'correct', 'bg-red-700 text-white': answerStatus[question.id] === 'wrong' }"
        @click="currentIndex = index"
      >
        {{ index + 1 }}
      </button>
    </aside>
    </div>
  </section>
</template>
