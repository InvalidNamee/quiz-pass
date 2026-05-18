<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import type { AIGenerationDraft } from '../api/types'
import {
  confirmDraft as confirmWorkflowDraft,
  getDraft as getWorkflowDraft,
  updateDraft as updateWorkflowDraft,
} from '../api/v2/aiGeneration'
import AppButton from '../components/AppButton.vue'
import AppEmpty from '../components/AppEmpty.vue'
import AppLoading from '../components/AppLoading.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const draft = ref<AIGenerationDraft | null>(null)
const loading = ref(true)
const saving = ref(false)
const confirming = ref(false)
const jobId = computed(() => Number(route.params.jobId))
const workflowId = computed(() => Number(route.params.workflowId))
const isWorkflowRoute = computed(() => Number.isFinite(workflowId.value) && workflowId.value > 0)

async function load() {
  loading.value = true
  try {
    draft.value = isWorkflowRoute.value
      ? await getWorkflowDraft(workflowId.value)
      : await api<AIGenerationDraft>(`/api/v1/ai-generation/jobs/${jobId.value}/draft`)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '草稿不存在', 'error')
  } finally {
    loading.value = false
  }
}

function addOption(questionIndex: number) {
  const question = draft.value?.questions[questionIndex]
  if (!question) return
  const label = String.fromCharCode(65 + question.options.length)
  question.options.push({ label, content: '', is_correct: false })
}

function removeOption(questionIndex: number, optionIndex: number) {
  const question = draft.value?.questions[questionIndex]
  if (!question || question.options.length <= 2) return
  question.options.splice(optionIndex, 1)
  question.options.forEach((option, index) => { option.label = String.fromCharCode(65 + index) })
}

function removeQuestion(index: number) {
  draft.value?.questions.splice(index, 1)
}

function addQuestion() {
  draft.value?.questions.push({
    id: 0,
    type: 'single',
    stem: '',
    explanation: '',
    difficulty: null,
    options: [
      { label: 'A', content: '', is_correct: true },
      { label: 'B', content: '', is_correct: false },
    ],
    validation_status: 'valid',
    validation_message: null,
  })
}

async function save() {
  if (!draft.value) return
  saving.value = true
  try {
    await persistDraft()
    toast.show('草稿已保存', 'success')
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '保存失败', 'error')
  } finally {
    saving.value = false
  }
}

async function persistDraft() {
  if (!draft.value) return
  draft.value = isWorkflowRoute.value
    ? await updateWorkflowDraft(workflowId.value, draft.value as unknown as Record<string, unknown>)
    : await api<AIGenerationDraft>(`/api/v1/ai-generation/jobs/${jobId.value}/draft`, {
        method: 'PATCH',
        body: JSON.stringify(draft.value),
      })
}

async function confirm() {
  if (!draft.value) return
  confirming.value = true
  try {
    await persistDraft()
    const data = isWorkflowRoute.value
      ? await confirmWorkflowDraft(workflowId.value)
      : await api<{ ok: boolean; bank_id: number }>(`/api/v1/ai-generation/jobs/${jobId.value}/confirm`, { method: 'POST' })
    toast.show('草稿已入库', 'success')
    router.push(`/banks/${data.bank_id}`)
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '确认失败', 'error')
  } finally {
    confirming.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-if="loading">
    <AppLoading />
  </section>

  <section v-else-if="!draft">
    <AppEmpty title="草稿不存在" />
  </section>

  <section v-else class="grid gap-5">
    <div class="page-card p-6">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold">确认 AI 草稿</h1>
          <p class="mt-2 text-slate-600">{{ draft.validation_summary || '请检查题目后确认入库。' }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <AppButton variant="secondary" :loading="saving" @click="save">保存草稿</AppButton>
          <AppButton :loading="confirming" @click="confirm">确认入库</AppButton>
        </div>
      </div>
      <label class="mt-5 grid gap-1">
        <span class="text-sm font-medium text-slate-700">题库描述</span>
        <textarea v-model="draft.bank_description" class="min-h-20 rounded-input border border-slate-300 bg-white px-3 py-2" placeholder="可选" />
      </label>
    </div>

    <div class="grid gap-4">
      <div v-for="(question, qIndex) in draft.questions" :key="question.id || qIndex" class="page-card grid gap-4 p-5">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <div class="flex items-center gap-2">
            <span class="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600">#{{ qIndex + 1 }}</span>
            <select v-model="question.type" class="rounded-input border border-slate-300 bg-white px-3 py-2 text-sm">
              <option value="single">单选</option>
              <option value="multiple">多选</option>
            </select>
          </div>
          <AppButton variant="ghost" @click="removeQuestion(qIndex)">删除题目</AppButton>
        </div>

        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">题干</span>
          <textarea v-model="question.stem" class="min-h-24 rounded-input border border-slate-300 bg-white px-3 py-2" />
        </label>

        <div class="grid gap-2">
          <div v-for="(option, oIndex) in question.options" :key="oIndex" class="grid gap-2 rounded-xl border border-slate-200 bg-slate-50 p-3 sm:grid-cols-[auto_auto_1fr_auto] sm:items-center">
            <input v-model="option.is_correct" type="checkbox" class="size-4 rounded" />
            <input v-model="option.label" class="w-16 rounded-input border border-slate-300 bg-white px-2 py-1 text-sm" />
            <input v-model="option.content" class="rounded-input border border-slate-300 bg-white px-3 py-2 text-sm" placeholder="选项内容" />
            <AppButton variant="ghost" @click="removeOption(qIndex, oIndex)">移除</AppButton>
          </div>
          <AppButton variant="secondary" @click="addOption(qIndex)">添加选项</AppButton>
        </div>

        <label class="grid gap-1">
          <span class="text-sm font-medium text-slate-700">解析</span>
          <textarea v-model="question.explanation" class="min-h-20 rounded-input border border-slate-300 bg-white px-3 py-2" />
        </label>
      </div>
    </div>

    <div class="page-card flex flex-wrap gap-2 p-5">
      <AppButton variant="secondary" @click="addQuestion">添加题目</AppButton>
      <AppButton variant="secondary" :loading="saving" @click="save">保存草稿</AppButton>
      <AppButton :loading="confirming" @click="confirm">确认入库</AppButton>
    </div>
  </section>
</template>
