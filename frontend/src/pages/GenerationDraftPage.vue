<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { AIGenerationDraft } from '../api/types'
import {
  confirmDraft as confirmWorkflowDraft,
  getDraft as getWorkflowDraft,
  updateDraft as updateWorkflowDraft,
} from '../api/v2/aiGeneration'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const draft = ref<AIGenerationDraft | null>(null)
const loading = ref(true)
const saving = ref(false)
const confirming = ref(false)
const workflowId = computed(() => Number(route.params.workflowId))

async function load() {
  loading.value = true
  try {
    draft.value = await getWorkflowDraft(workflowId.value)
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
  draft.value = await updateWorkflowDraft(workflowId.value, draft.value as unknown as Record<string, unknown>)
}

async function confirm() {
  if (!draft.value) return
  confirming.value = true
  try {
    await persistDraft()
    const data = await confirmWorkflowDraft(workflowId.value)
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
  <section v-loading="loading" class="qp-page" element-loading-text="加载中...">
    <template v-if="draft">
      <div class="qp-section">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 class="qp-title">确认 AI 草稿</h1>
            <p class="qp-subtitle">{{ draft.validation_summary || '请检查题目后确认入库。' }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <el-button :loading="saving" @click="save">保存草稿</el-button>
            <el-button type="primary" :loading="confirming" @click="confirm">确认入库</el-button>
          </div>
        </div>
        <el-form-item class="mt-4" label="题库描述">
          <el-input v-model="draft.bank_description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </div>

      <div class="grid gap-3">
        <el-form v-for="(question, qIndex) in draft.questions" :key="question.id || qIndex" class="qp-section grid gap-3" label-position="top">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <el-tag size="small" type="info">#{{ qIndex + 1 }}</el-tag>
              <el-select v-model="question.type" size="small" style="width: 90px">
                <el-option value="single" label="单选" />
                <el-option value="multiple" label="多选" />
              </el-select>
            </div>
            <el-button text @click="removeQuestion(qIndex)">删除题目</el-button>
          </div>

          <el-form-item label="题干">
            <el-input v-model="question.stem" type="textarea" :rows="4" />
          </el-form-item>

          <div class="grid gap-2">
            <div v-for="(option, oIndex) in question.options" :key="oIndex" class="flex flex-wrap items-center gap-2 border border-slate-200 bg-slate-50 p-2">
              <el-checkbox v-model="option.is_correct" />
              <el-input v-model="option.label" size="small" style="width: 60px" />
              <el-input v-model="option.content" size="small" placeholder="选项内容" class="flex-1" />
              <el-button text size="small" @click="removeOption(qIndex, oIndex)">移除</el-button>
            </div>
            <el-button @click="addOption(qIndex)">添加选项</el-button>
          </div>

          <el-form-item label="解析">
            <el-input v-model="question.explanation" type="textarea" :rows="3" />
          </el-form-item>
        </el-form>
      </div>

      <div class="qp-section flex flex-wrap gap-2">
        <el-button @click="addQuestion">添加题目</el-button>
        <el-button :loading="saving" @click="save">保存草稿</el-button>
        <el-button type="primary" :loading="confirming" @click="confirm">确认入库</el-button>
      </div>
    </template>

    <el-empty v-if="!draft && !loading" description="草稿不存在" />
  </section>
</template>
