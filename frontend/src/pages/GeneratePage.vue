<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AIProviderConfig, type Page } from '../api/client'

const title = ref('')
const desiredVisibility = ref('private')
const aiProviderConfigId = ref('')
const questionCountMode = ref('fixed')
const questionCount = ref(10)
const file = ref<File | null>(null)
const result = ref('')
const configs = ref<AIProviderConfig[]>([])
const jobs = ref<any[]>([])

async function load() {
  configs.value = await api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
  const preferred = configs.value.find((item) => item.is_default) ?? configs.value[0]
  if (preferred && !aiProviderConfigId.value) aiProviderConfigId.value = String(preferred.id)
  jobs.value = (await api<Page<any>>('/api/v1/ai-generation/jobs')).items
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function submit() {
  if (!file.value) return
  const form = new FormData()
  form.set('title', title.value)
  form.set('desired_visibility', desiredVisibility.value)
  if (aiProviderConfigId.value) form.set('ai_provider_config_id', aiProviderConfigId.value)
  form.set('question_count_mode', questionCountMode.value)
  if (questionCountMode.value === 'fixed') form.set('question_count', String(questionCount.value))
  form.set('file', file.value)
  const data = await api<{ bank_id: number; job_id: number }>('/api/v1/ai-generation/question-bank-jobs', { method: 'POST', body: form })
  result.value = `已创建生成任务 #${data.job_id}，题库 #${data.bank_id}`
  await load()
}

onMounted(load)
</script>

<template>
  <section>
    <h1 class="text-2xl font-bold">AI 生成题库</h1>
    <div class="my-4 grid max-w-2xl gap-3">
      <input v-model="title" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库名称" />
      <select v-model="desiredVisibility" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="private">生成后私有</option>
        <option value="public">生成成功后公开</option>
      </select>
      <select v-model="aiProviderConfigId" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option v-for="config in configs" :key="config.id" :value="config.id">{{ config.name ? `${config.name} · ${config.model}` : config.model }}</option>
      </select>
      <select v-model="questionCountMode" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="fixed">指定题数</option>
        <option value="adaptive">大模型自适应题数</option>
      </select>
      <input v-if="questionCountMode === 'fixed'" v-model.number="questionCount" class="rounded-md border border-slate-300 bg-white px-3 py-2" type="number" min="1" max="100" />
      <input class="rounded-md border border-slate-300 bg-white px-3 py-2" type="file" accept=".txt,.docx,.pdf" @change="onFile" />
      <RouterLink v-if="!configs.length" class="w-fit rounded-md bg-slate-200 px-4 py-2 text-slate-900" to="/settings/ai-providers">先创建 AI 配置</RouterLink>
      <button v-else class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="submit">开始生成</button>
      <p v-if="result">{{ result }}</p>
    </div>
    <h2 class="text-xl font-semibold">生成任务</h2>
    <div class="mt-4 grid gap-3">
      <RouterLink v-for="job in jobs" :key="job.id" class="flex items-center justify-between gap-4 rounded-lg border border-slate-200 bg-white p-4 shadow-sm" :to="`/banks/${job.bank_id}`">
        <strong>#{{ job.id }} · {{ job.status }}</strong>
        <span class="text-sm text-slate-500">{{ job.ai_model_snapshot }} · {{ job.error_message || '无错误' }}</span>
      </RouterLink>
    </div>
  </section>
</template>
