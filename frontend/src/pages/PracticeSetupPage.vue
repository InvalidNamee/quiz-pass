<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type PracticeSession, type QuestionBank } from '../api/client'
import AppButton from '../components/AppButton.vue'
import AppLoading from '../components/AppLoading.vue'

const route = useRoute()
const router = useRouter()
const bank = ref<QuestionBank | null>(null)
const mode = ref('practice')
const useLimit = ref(false)
const limit = ref(20)
const loading = ref(true)
const starting = ref(false)

const modeDescriptions: Record<string, string> = {
  practice: '每题作答后立即显示对错和解析，适合日常练习。',
  exam: '模拟考试环境，提交前不显示答案，交卷后统一出分。',
  mistake_review: '只练习当前题库中做错的题目，查漏补缺。',
}

async function load() {
  loading.value = true
  try {
    bank.value = await api<QuestionBank>(`/api/v1/question-banks/${route.params.bankId}`)
  } finally {
    loading.value = false
  }
}

async function start() {
  starting.value = true
  try {
    const body: Record<string, unknown> = { bank_id: Number(route.params.bankId), mode: mode.value }
    if (useLimit.value) body.question_limit = limit.value
    const session = await api<PracticeSession>('/api/v1/practice/sessions', { method: 'POST', body: JSON.stringify(body) })
    router.push(`/practice/session/${session.id}`)
  } catch {
    starting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">开始刷题</h1>
      <p v-if="bank" class="mt-2 text-slate-600">{{ bank.title }} · {{ bank.question_count }} 题</p>
    </div>

    <AppLoading v-if="loading" />

    <div v-else class="grid max-w-2xl gap-5 page-card p-6">
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">练习模式</span>
        <select v-model="mode" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option value="practice">普通练习</option>
          <option value="exam">模拟考试</option>
          <option value="mistake_review">错题复习</option>
        </select>
        <span class="text-xs text-slate-500">{{ modeDescriptions[mode] }}</span>
      </label>

      <label class="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
        <input v-model="useLimit" type="checkbox" class="rounded" /> 指定题数
      </label>
      <input v-if="useLimit" v-model.number="limit" class="rounded-input border border-slate-300 bg-white px-3 py-2" type="number" min="1" max="200" />

      <div class="flex flex-wrap gap-2">
        <AppButton :loading="starting" @click="start">开始</AppButton>
        <RouterLink v-if="bank" :to="`/banks/${bank.id}`" class="inline-flex items-center rounded-btn px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">返回题库</RouterLink>
      </div>
    </div>
  </section>
</template>
