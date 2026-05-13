<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AIProviderConfig } from '../api/client'
import AppButton from '../components/AppButton.vue'
import { useToast } from '../composables/useToast'

const title = ref('')
const description = ref('')
const generationMode = ref<'knowledge_generate' | 'bank_parse'>('knowledge_generate')
const isPublic = ref(false)
const aiProviderConfigId = ref('')
const questionCountMode = ref('fixed')
const questionCount = ref(10)
const generateDescription = ref(false)
const extraInstruction = ref('')
const file = ref<File | null>(null)
const configs = ref<AIProviderConfig[]>([])
const submitting = ref(false)
const toast = useToast()

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
  if (!title.value.trim()) {
    toast.show('请输入题库名称', 'error')
    return
  }
  submitting.value = true
  try {
    const form = new FormData()
    form.set('title', title.value)
    if (description.value.trim()) form.set('description', description.value.trim())
    form.set('generation_mode', generationMode.value)
    form.set('desired_visibility', isPublic.value ? 'public' : 'private')
    if (aiProviderConfigId.value) form.set('ai_provider_config_id', aiProviderConfigId.value)
    if (generationMode.value === 'knowledge_generate') {
      form.set('question_count_mode', questionCountMode.value)
      if (questionCountMode.value === 'fixed') form.set('question_count', String(questionCount.value))
    }
    if (extraInstruction.value.trim()) form.set('extra_instruction', extraInstruction.value.trim())
    form.set('generate_description', String(generateDescription.value))
    form.set('file', file.value)
    const data = await api<{ bank_id: number; job_id: number }>('/api/v1/ai-generation/question-bank-jobs', { method: 'POST', body: form })
    toast.show(`已创建生成任务 #${data.job_id}`, 'success')
    title.value = ''
    extraInstruction.value = ''
    file.value = null
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '提交失败', 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="mx-auto grid max-w-3xl gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">AI 生成题库</h1>
      <p class="mt-2 text-slate-600">上传文档，AI 自动生成选择题。</p>
    </div>

    <div class="page-card grid gap-4 p-6">
      <div class="grid gap-3 sm:grid-cols-2">
        <button
          class="rounded-xl border p-4 text-left transition-colors"
          :class="generationMode === 'knowledge_generate' ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'"
          type="button"
          @click="generationMode = 'knowledge_generate'"
        >
          <strong class="block">从知识库生成</strong>
          <span class="mt-1 block text-sm">根据资料内容生成新题。</span>
        </button>
        <button
          class="rounded-xl border p-4 text-left transition-colors"
          :class="generationMode === 'bank_parse' ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'"
          type="button"
          @click="generationMode = 'bank_parse'"
        >
          <strong class="block">从题库解析</strong>
          <span class="mt-1 block text-sm">解析已有题库文档，AI 修复坏题格式。</span>
        </button>
      </div>

      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">题库名称</span>
        <input v-model="title" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="起个名字" />
      </label>

      <textarea v-model="description" class="min-h-20 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="题库描述（可选）" />

      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">AI 模型</span>
        <select v-model="aiProviderConfigId" class="rounded-input border border-slate-300 bg-white px-3 py-2">
          <option v-for="config in configs" :key="config.id" :value="config.id">{{ config.name ? `${config.name} · ${config.model}` : config.model }}</option>
        </select>
      </label>

      <template v-if="generationMode === 'knowledge_generate'">
        <div class="grid gap-3 sm:grid-cols-2">
          <label class="grid gap-1">
            <span class="text-sm font-medium text-slate-700">题数模式</span>
            <select v-model="questionCountMode" class="rounded-input border border-slate-300 bg-white px-3 py-2">
              <option value="fixed">指定题数</option>
              <option value="adaptive">AI 自适应</option>
            </select>
          </label>
          <label v-if="questionCountMode === 'fixed'" class="grid gap-1">
            <span class="text-sm font-medium text-slate-700">题目数量</span>
            <input v-model.number="questionCount" class="rounded-input border border-slate-300 bg-white px-3 py-2" type="number" min="1" max="100" />
          </label>
        </div>
      </template>

      <div class="flex flex-wrap gap-4">
        <label class="flex items-center gap-2 text-sm text-slate-700">
          <input v-model="isPublic" type="checkbox" class="rounded" /> 生成成功后自动公开
        </label>
        <label class="flex items-center gap-2 text-sm text-slate-700">
          <input v-model="generateDescription" type="checkbox" class="rounded" /> 让 AI 生成题库描述
        </label>
      </div>

      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">额外指令（可选）</span>
        <textarea
          v-model="extraInstruction"
          class="min-h-24 rounded-input border border-slate-300 bg-white px-3 py-2"
          maxlength="2000"
          placeholder="例如：题目偏实战场景；解析更详细；解析题库时保留原编号。硬性 JSON 和答案规则仍会优先。"
        />
        <span class="text-xs text-slate-500">{{ extraInstruction.length }} / 2000</span>
      </label>

      <label class="grid gap-1">
        <span class="text-sm font-medium text-slate-700">文档文件（.txt / .docx / .pdf）</span>
        <input class="rounded-input border border-slate-300 bg-white px-3 py-2" type="file" accept=".txt,.docx,.pdf" @change="onFile" />
      </label>

      <div class="flex flex-wrap gap-2">
        <RouterLink v-if="!configs.length" to="/settings/ai-providers" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">先配置 AI</RouterLink>
        <AppButton v-else :loading="submitting" @click="submit">开始生成</AppButton>
        <RouterLink to="/banks/generation-jobs" class="inline-flex items-center rounded-btn px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">查看队列</RouterLink>
      </div>
    </div>
  </section>
</template>
