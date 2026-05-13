<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type MistakeRecord, type Page, type PracticeSession } from '../api/client'

const route = useRoute()
const router = useRouter()
const bankId = Number(route.params.bankId)
const mistakes = ref<MistakeRecord[]>([])

async function load() {
  const data = await api<Page<MistakeRecord>>(`/api/v1/question-banks/${bankId}/mistakes?resolved=false`)
  mistakes.value = data.items
}

async function resolve(questionId: number) {
  await api(`/api/v1/question-banks/${bankId}/mistakes/${questionId}/resolve`, { method: 'POST' })
  await load()
}

async function practice() {
  const session = await api<PracticeSession>(`/api/v1/question-banks/${bankId}/mistakes/practice-sessions`, { method: 'POST' })
  router.push(`/practice/session/${session.id}`)
}

onMounted(load)
</script>

<template>
  <section>
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-bold">错题</h1>
      <button class="rounded-md bg-blue-600 px-4 py-2 text-white disabled:opacity-50" :disabled="!mistakes.length" @click="practice">错题练习</button>
    </div>
    <div class="mt-4 grid gap-3">
      <article v-for="item in mistakes" :key="item.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
        <strong>题目 #{{ item.question_id }}</strong>
        <span class="text-sm text-slate-500">错误 {{ item.wrong_count }} 次</span>
        <button class="rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="resolve(item.question_id)">已掌握</button>
      </article>
    </div>
  </section>
</template>
