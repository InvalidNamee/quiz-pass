<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, type AIProviderConfig, type QuestionBank, type QuestionBankTag } from '../api/client'
import AppButton from '../components/AppButton.vue'
import BankTagInput from '../components/BankTagInput.vue'
import { useToast } from '../composables/useToast'

type CreateMode = 'ai_knowledge' | 'ai_parse' | 'json_import'

const title = ref('')
const description = ref('')
const createMode = ref<CreateMode>('ai_knowledge')
const isPublic = ref(false)
const aiProviderConfigId = ref('')
const questionCountMode = ref('fixed')
const questionCount = ref(10)
const generateDescription = ref(false)
const extraInstruction = ref('')
const selectedTags = ref<QuestionBankTag[]>([])
const file = ref<File | null>(null)
const configs = ref<AIProviderConfig[]>([])
const bank = ref<QuestionBank | null>(null)
const submitting = ref(false)
const toast = useToast()
const route = useRoute()
const router = useRouter()
const extendBankId = computed(() => route.params.bankId ? Number(route.params.bankId) : null)
const isExtend = computed(() => Boolean(extendBankId.value))

async function load() {
  configs.value = await api<AIProviderConfig[]>('/api/v1/users/me/ai-provider-configs')
  const preferred = configs.value.find((item) => item.is_default) ?? configs.value[0]
  if (preferred && !aiProviderConfigId.value) aiProviderConfigId.value = String(preferred.id)
  if (extendBankId.value) {
    bank.value = await api<QuestionBank>(`/api/v1/question-banks/${extendBankId.value}`)
  }
}

function onFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

async function submit() {
  if (!file.value) return
  if (!isExtend.value && !title.value.trim()) {
    toast.show('请输入题库名称', 'error')
    return
  }
  submitting.value = true
  try {
    const form = new FormData()
    form.set('file', file.value)

    if (createMode.value === 'json_import') {
      form.set('visibility', isPublic.value ? 'public' : 'private')
      if (selectedTags.value.length) form.set('tag_names', JSON.stringify(selectedTags.value.map(tag => tag.name)))
      const endpoint = isExtend.value
        ? `/api/v1/question-banks/${extendBankId.value}/import-json`
        : '/api/v1/question-banks/import-json'
      const bank = await api<QuestionBank>(endpoint, { method: 'POST', body: form })
      toast.show(`题目已导入「${bank.title}」`, 'success')
    } else {
      if (!isExtend.value) {
        form.set('title', title.value)
        if (description.value.trim()) form.set('description', description.value.trim())
        form.set('desired_visibility', isPublic.value ? 'public' : 'private')
        if (selectedTags.value.length) form.set('tag_names', JSON.stringify(selectedTags.value.map(tag => tag.name)))
      }
      form.set('generation_mode', createMode.value === 'ai_parse' ? 'bank_parse' : 'knowledge_generate')
      if (aiProviderConfigId.value) form.set('ai_provider_config_id', aiProviderConfigId.value)
      if (createMode.value === 'ai_knowledge') {
        form.set('question_count_mode', questionCountMode.value)
        if (questionCountMode.value === 'fixed') form.set('question_count', String(questionCount.value))
      }
      if (extraInstruction.value.trim()) form.set('extra_instruction', extraInstruction.value.trim())
      form.set('generate_description', String(generateDescription.value))
      const endpoint = isExtend.value
        ? `/api/v1/question-banks/${extendBankId.value}/ai-generation/extend-jobs`
        : '/api/v1/ai-generation/question-bank-jobs'
      const data = await api<{ bank_id: number; job_id: number }>(endpoint, { method: 'POST', body: form })
      toast.show(`已创建${isExtend.value ? '扩展' : '生成'}任务 #${data.job_id}`, 'success')
    }

    title.value = ''
    extraInstruction.value = ''
    selectedTags.value = []
    file.value = null
    await load()
    router.push('/banks/generation-jobs')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '提交失败', 'error')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
watch(() => route.fullPath, load)
</script>

<template>
  <section class="mx-auto grid max-w-3xl gap-5">
    <div class="page-card p-6">
      <h1 class="text-2xl font-bold">{{ isExtend ? `扩展题库${bank ? '：' + bank.title : ''}` : '新建题库' }}</h1>
      <p class="mt-2 text-slate-600">
        {{ isExtend ? '为已有题库追加题目。' : '选择一种方式创建题库。' }}
      </p>
    </div>

    <div class="page-card grid gap-5 p-6">
      <!-- Mode selection -->
      <div class="grid gap-3 sm:grid-cols-3">
        <button
          v-for="mode in [
            { key: 'ai_knowledge', title: 'AI 生成', desc: '上传资料生成新题' },
            { key: 'ai_parse', title: 'AI 解析', desc: '从题库文档提取' },
            { key: 'json_import', title: '导入 JSON', desc: '导入 Quiz Pass JSON' },
          ] as { key: CreateMode; title: string; desc: string }[]"
          :key="mode.key"
          class="rounded-xl border p-4 text-left transition-colors"
          :class="createMode === mode.key ? 'border-brand-500 bg-brand-50 text-brand-900' : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300'"
          type="button"
          @click="createMode = mode.key"
        >
          <strong class="block text-sm">{{ mode.title }}</strong>
          <span class="mt-1 block text-xs text-current opacity-70">{{ mode.desc }}</span>
        </button>
      </div>

      <!-- Basic info (hide when extending via AI) -->
      <template v-if="!(isExtend && createMode !== 'json_import')">
        <div class="grid gap-3">
          <label class="grid gap-1">
            <span class="text-sm font-medium text-slate-700">题库名称</span>
            <input v-model="title" class="rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="起个名字" />
          </label>
          <textarea v-model="description" class="min-h-14 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="简短描述（可选）" />
          <BankTagInput v-model="selectedTags" allow-create placeholder="添加标签" />
        </div>
      </template>

      <!-- AI settings (only for AI modes) -->
      <template v-if="createMode !== 'json_import'">
        <div class="border-t border-slate-100 pt-5">
          <h3 class="mb-3 text-sm font-semibold text-slate-700">AI 生成设置</h3>
          <div class="grid gap-3 sm:grid-cols-2">
            <label class="grid gap-1">
              <span class="text-sm font-medium text-slate-700">AI 模型</span>
              <select v-model="aiProviderConfigId" class="rounded-input border border-slate-300 bg-white px-3 py-2">
                <option v-for="config in configs" :key="config.id" :value="config.id">{{ config.name ? `${config.name} · ${config.model}` : config.model }}</option>
              </select>
            </label>
            <template v-if="createMode === 'ai_knowledge'">
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
            </template>
          </div>
          <label class="mt-3 grid gap-1">
            <span class="text-sm font-medium text-slate-700">额外指令（可选）</span>
            <textarea v-model="extraInstruction" class="min-h-16 rounded-input border border-slate-300 bg-white px-3 py-2" maxlength="2000" placeholder="例如：题目偏实战场景；解析更详细" />
            <span class="text-xs text-slate-400">{{ extraInstruction.length }} / 2000</span>
          </label>
        </div>

        <div class="flex flex-wrap gap-4">
          <label class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="isPublic" type="checkbox" class="rounded" /> 生成成功后自动公开
          </label>
          <label v-if="createMode === 'ai_knowledge'" class="flex items-center gap-2 text-sm text-slate-700">
            <input v-model="generateDescription" type="checkbox" class="rounded" /> 让 AI 生成题库描述
          </label>
        </div>
      </template>

      <!-- Visibility for JSON import -->
      <label v-if="createMode === 'json_import'" class="flex items-center gap-2 text-sm text-slate-700">
        <input v-model="isPublic" type="checkbox" class="rounded" /> 公开题库
      </label>

      <!-- File upload -->
      <div class="border-t border-slate-100 pt-5">
        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">上传文件</span>
          <span class="text-xs text-slate-400">{{ createMode === 'json_import' ? '支持 .json' : '支持 .txt / .docx / .pdf' }}</span>
          <input class="mt-1 rounded-input border border-slate-300 bg-white px-3 py-2" type="file" :accept="createMode === 'json_import' ? '.json' : '.txt,.docx,.pdf'" @change="onFile" />
        </label>
      </div>

      <div class="flex flex-wrap gap-2 border-t border-slate-100 pt-5">
        <RouterLink v-if="createMode !== 'json_import' && !configs.length" to="/settings/ai-providers" class="inline-flex items-center rounded-btn bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700">先配置 AI</RouterLink>
        <AppButton v-else :loading="submitting" @click="submit">
          {{ createMode === 'json_import' ? '开始导入' : '开始生成' }}
        </AppButton>
        <RouterLink to="/banks/generation-jobs" class="inline-flex items-center rounded-btn px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100">查看队列</RouterLink>
      </div>
    </div>
  </section>
</template>
