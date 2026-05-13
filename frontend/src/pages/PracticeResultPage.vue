<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { api, type PracticeSession } from '../api/client'

type ResultOption = { id: number; label: string; content: string }
type Result = {
  question_id: number
  type: 'single' | 'multiple'
  stem: string
  options: ResultOption[]
  selected_option_ids: number[]
  selected_labels: string[]
  correct_option_ids: number[]
  correct_labels: string[]
  is_correct: boolean
  is_unanswered: boolean
  explanation: string | null
}
const route = useRoute()
const sessionId = Number(route.params.sessionId)
const session = ref<PracticeSession | null>(null)
const results = ref<Result[]>([])

onMounted(async () => {
  session.value = await api<PracticeSession>(`/api/v1/practice/sessions/${sessionId}`)
  results.value = await api<Result[]>(`/api/v1/practice/sessions/${sessionId}/result`)
})
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">练习结果</h1>
    <p v-if="session" class="mt-2 text-slate-600">得分 {{ session.score }}，正确 {{ session.correct_count }} / {{ session.total_questions }}</p>
    <div class="mt-5 grid gap-3">
      <article
        v-for="(item, index) in results"
        :key="item.question_id"
        class="grid gap-3 rounded-lg border bg-white p-4 shadow-sm"
        :class="{ 'border-green-300': item.is_correct, 'border-red-300': !item.is_correct && !item.is_unanswered, 'border-yellow-500 bg-yellow-50': item.is_unanswered }"
      >
        <div class="flex items-center justify-between gap-4">
          <strong>{{ index + 1 }}. [{{ item.type === 'single' ? '单选' : '多选' }}] {{ item.stem }}</strong>
          <span class="text-sm font-bold">{{ item.is_unanswered ? '未作答' : item.is_correct ? '正确' : '错误' }}</span>
        </div>
        <div class="grid gap-1 text-sm text-slate-700">
          <p v-for="option in item.options" :key="option.id" class="m-0">{{ option.label }}. {{ option.content }}</p>
        </div>
        <div class="flex flex-wrap gap-3 text-sm text-slate-500">
          <span>当时选择：{{ item.is_unanswered ? '未作答' : item.selected_labels.join('、') }}</span>
          <span>正确答案：{{ item.correct_labels.join('、') }}</span>
        </div>
        <p v-if="item.explanation" class="m-0 text-slate-700">{{ item.explanation }}</p>
      </article>
    </div>
  </section>
</template>
