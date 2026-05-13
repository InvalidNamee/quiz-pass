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
  <section>
    <h1 class="text-2xl font-bold">开始刷题</h1>
    <p v-if="bank" class="mt-2 text-slate-600">题库：{{ bank.title }}，默认练习全部题目</p>
    <div class="my-4 grid max-w-xl gap-3">
      <select v-model="mode" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="practice">普通练习</option>
        <option value="exam">模拟考试</option>
        <option value="mistake_review">错题练习</option>
      </select>
      <label class="flex items-center gap-2"><input v-model="useLimit" type="checkbox" /> 指定题数</label>
      <input v-if="useLimit" v-model.number="limit" class="rounded-md border border-slate-300 bg-white px-3 py-2" type="number" min="1" max="200" />
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="start">开始</button>
    </div>
  </section>
</template>
