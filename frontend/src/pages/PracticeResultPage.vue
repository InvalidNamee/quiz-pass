<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import type { PracticeSession } from '../api/types'
import { getResult, getSession } from '../api/v2/practice'
import AppBadge from '../components/AppBadge.vue'
import AppLoading from '../components/AppLoading.vue'
import MathText from '../components/MathText.vue'

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
const loading = ref(true)

onMounted(async () => {
  try {
    session.value = await getSession(sessionId)
    results.value = await getResult(sessionId)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="grid gap-5">
    <div>
      <h1 class="text-lg font-bold">练习结果</h1>
      <p v-if="session" class="mt-2 text-slate-600">
        得分 <strong class="text-slate-900">{{ session.score }}</strong>，正确 {{ session.correct_count }} / {{ session.total_questions }}
      </p>
    </div>

    <AppLoading v-if="loading" />

    <div v-else class="grid gap-2">
      <article
        v-for="(item, index) in results"
        :key="item.question_id"
        class="border-y border-slate-100 py-4"
        :class="{
          'border-l-4 border-l-green-500 pl-4': item.is_correct,
          'border-l-4 border-l-red-500 pl-4': !item.is_correct && !item.is_unanswered,
          'border-l-4 border-l-yellow-500 pl-4': item.is_unanswered,
        }"
      >
        <div class="flex items-start justify-between gap-2">
          <strong class="text-slate-900">
            {{ index + 1 }}. [{{ item.type === 'single' ? '单选' : '多选' }}]
            <MathText class="inline" :text="item.stem" />
          </strong>
          <AppBadge :variant="item.is_unanswered ? 'warning' : item.is_correct ? 'success' : 'danger'">
            {{ item.is_unanswered ? '未作答' : item.is_correct ? '正确' : '错误' }}
          </AppBadge>
        </div>
        <div class="mt-2 grid gap-1 text-sm text-slate-700">
          <p v-for="option in item.options" :key="option.id" class="m-0">
            <span class="font-medium">{{ option.label }}.</span>
            <MathText class="inline" :text="option.content" />
          </p>
        </div>
        <div class="mt-2 flex flex-wrap gap-2 text-sm">
          <span class="text-slate-500">你的选择：{{ item.is_unanswered ? '未作答' : item.selected_labels.join('、') || '无' }}</span>
          <span class="font-medium text-slate-700">正确答案：{{ item.correct_labels.join('、') }}</span>
        </div>
        <p v-if="item.explanation" class="mt-2 rounded-lg bg-blue-50 px-3 py-2 text-sm text-blue-800">
          <MathText :text="item.explanation" />
        </p>
      </article>
    </div>
  </section>
</template>
