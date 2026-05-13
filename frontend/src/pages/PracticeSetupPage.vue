<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useRouter } from 'vue-router'
import { api, type PracticeSession, type QuestionBank } from '../api/client'

const route = useRoute()
const router = useRouter()
const bank = ref<QuestionBank | null>(null)
const mode = ref('practice')
const useLimit = ref(false)
const limit = ref(20)

async function load() {
  bank.value = await api<QuestionBank>(`/api/v1/question-banks/${route.params.bankId}`)
}

async function start() {
  const body: Record<string, unknown> = { bank_id: Number(route.params.bankId), mode: mode.value }
  if (useLimit.value) body.question_limit = limit.value
  const session = await api<PracticeSession>('/api/v1/practice/sessions', {
    method: 'POST',
    body: JSON.stringify(body),
  })
  router.push(`/practice/session/${session.id}`)
}

onMounted(load)
</script>

<template>
  <section class="grid gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h1 class="text-2xl font-bold">开始刷题</h1>
      <p v-if="bank" class="mt-2 text-slate-600">{{ bank.title }} · {{ bank.question_count }} 题，默认练习全部题目。</p>
    </div>
    <div class="grid max-w-3xl gap-4 rounded-xl border border-slate-200 bg-white p-6">
      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">练习模式</span>
        <select v-model="mode" class="rounded-md border border-slate-300 bg-white px-3 py-2">
          <option value="practice">普通练习</option>
          <option value="exam">模拟考试</option>
          <option value="mistake_review">错题练习</option>
        </select>
      </label>
      <label class="flex items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-sm text-slate-700"><input v-model="useLimit" type="checkbox" /> 指定题数</label>
      <input v-if="useLimit" v-model.number="limit" class="rounded-md border border-slate-300 bg-white px-3 py-2" type="number" min="1" max="200" />
      <div class="flex flex-wrap gap-2">
        <button class="rounded-md bg-blue-600 px-4 py-2 text-white" @click="start">开始</button>
        <RouterLink v-if="bank" class="rounded-md bg-slate-100 px-4 py-2 text-slate-700" :to="`/banks/${bank.id}`">返回题库</RouterLink>
      </div>
    </div>
  </section>
</template>
