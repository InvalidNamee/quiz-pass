<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type QuestionBank } from '../api/client'

const route = useRoute()
const router = useRouter()
const bankId = Number(route.params.bankId)
const file = ref<File | null>(null)
const message = ref('')

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function submit() {
  if (!file.value) return
  const form = new FormData()
  form.set('file', file.value)
  const bank = await api<QuestionBank>(`/api/v1/question-banks/${bankId}/import-json`, { method: 'POST', body: form })
  message.value = `已导入到 ${bank.title}`
}

async function exportJson() {
  const token = localStorage.getItem('access_token')
  const response = await fetch(`/api/v1/question-banks/${bankId}/export`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `question-bank-${bankId}.json`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">导入导出</h1>
    <div class="my-4 grid max-w-xl gap-3">
      <input class="rounded-md border border-slate-300 bg-white px-3 py-2" type="file" accept=".json" @change="onFile" />
      <button class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="submit">导入 JSON</button>
      <button class="w-fit rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="exportJson">导出 JSON</button>
      <button class="w-fit rounded-md bg-slate-200 px-4 py-2 text-slate-900" @click="router.push(`/banks/${bankId}`)">返回</button>
      <p v-if="message">{{ message }}</p>
    </div>
  </section>
</template>
