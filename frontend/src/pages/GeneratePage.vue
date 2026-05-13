<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AIProviderConfig } from '../api/client'

const title = ref('')
const description = ref('')
const generationMode = ref<'knowledge_generate' | 'bank_parse'>('knowledge_generate')
const desiredVisibility = ref('private')
const aiProviderConfigId = ref('')
const questionCountMode = ref('fixed')
const questionCount = ref(10)
const generateDescription = ref(false)
const file = ref<File | null>(null)
const result = ref('')
const configs = ref<AIProviderConfig[]>([])

async function load() {
  configs.value = await api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
  const preferred = configs.value.find((item) => item.is_default) ?? configs.value[0]
  if (preferred && !aiProviderConfigId.value) aiProviderConfigId.value = String(preferred.id)
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function submit() {
  if (!file.value) return
  const form = new FormData()
  form.set('title', title.value)
  if (description.value.trim()) form.set('description', description.value.trim())
  form.set('generation_mode', generationMode.value)
  form.set('desired_visibility', desiredVisibility.value)
  if (aiProviderConfigId.value) form.set('ai_provider_config_id', aiProviderConfigId.value)
  if (generationMode.value === 'knowledge_generate') {
    form.set('question_count_mode', questionCountMode.value)
    if (questionCountMode.value === 'fixed') form.set('question_count', String(questionCount.value))
  }
  form.set('generate_description', String(generateDescription.value))
  form.set('file', file.value)
  const data = await api<{ bank_id: number; job_id: number }>('/api/v1/ai-generation/question-bank-jobs', { method: 'POST', body: form })
  result.value = `已创建生成任务 #${data.job_id}，题库 #${data.bank_id}`
  await load()
}

onMounted(load)
</script>

<template>
  <section class="mx-auto grid max-w-3xl gap-5">
    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <h1 class="text-2xl font-bold">新建题库</h1>
      <p class="mt-2 text-slate-600">从知识库文件生成新题，或从已有题库文档解析为系统题库。</p>
    </div>
    <div class="grid gap-3 rounded-xl border border-slate-200 bg-white p-6">
      <div class="grid gap-3 sm:grid-cols-2">
        <button
          class="rounded-xl border p-4 text-left"
          :class="generationMode === 'knowledge_generate' ? 'border-blue-300 bg-blue-50 text-blue-900' : 'border-slate-200 bg-white text-slate-700'"
          type="button"
          @click="generationMode = 'knowledge_generate'"
        >
          <strong class="block">从知识库生成</strong>
          <span class="mt-1 block text-sm">根据资料内容生成一批新题。</span>
        </button>
        <button
          class="rounded-xl border p-4 text-left"
          :class="generationMode === 'bank_parse' ? 'border-blue-300 bg-blue-50 text-blue-900' : 'border-slate-200 bg-white text-slate-700'"
          type="button"
          @click="generationMode = 'bank_parse'"
        >
          <strong class="block">从题库解析</strong>
          <span class="mt-1 block text-sm">解析已有题库文档，AI 会修复坏题格式。</span>
        </button>
      </div>
      <input v-model="title" class="rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库名称" />
      <textarea v-model="description" class="min-h-24 rounded-md border border-slate-300 bg-white px-3 py-2" placeholder="题库描述（可选）" />
      <select v-model="desiredVisibility" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="private">生成后私有</option>
        <option value="public">生成成功后公开</option>
      </select>
      <select v-model="aiProviderConfigId" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option v-for="config in configs" :key="config.id" :value="config.id">{{ config.name ? `${config.name} · ${config.model}` : config.model }}</option>
      </select>
      <select v-if="generationMode === 'knowledge_generate'" v-model="questionCountMode" class="rounded-md border border-slate-300 bg-white px-3 py-2">
        <option value="fixed">指定题数</option>
        <option value="adaptive">大模型自适应题数</option>
      </select>
      <input v-if="generationMode === 'knowledge_generate' && questionCountMode === 'fixed'" v-model.number="questionCount" class="rounded-md border border-slate-300 bg-white px-3 py-2" type="number" min="1" max="100" />
      <label class="flex items-center gap-2 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700">
        <input v-model="generateDescription" type="checkbox" />
        <span>让 AI 顺便生成一份题库描述</span>
      </label>
      <input class="rounded-md border border-slate-300 bg-white px-3 py-2" type="file" accept=".txt,.docx,.pdf" @change="onFile" />
      <RouterLink v-if="!configs.length" class="w-fit rounded-md bg-slate-200 px-4 py-2 text-slate-900" to="/settings/ai-providers">先创建 AI 配置</RouterLink>
      <button v-else class="w-fit rounded-md bg-blue-600 px-4 py-2 text-white" @click="submit">开始生成</button>
      <p v-if="result" class="rounded-md bg-green-50 px-3 py-2 text-sm font-medium text-green-800">{{ result }}，可前往生成队列查看进度。</p>
      <RouterLink v-if="result" class="w-fit rounded-md bg-slate-100 px-4 py-2 text-slate-700" to="/banks/generation-jobs">查看生成队列</RouterLink>
    </div>
  </section>
</template>
