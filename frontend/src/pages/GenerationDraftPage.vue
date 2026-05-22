<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import type { AIGenerationDraft, AIGenerationDraftQuestion } from '../api/types'
import {
  cancelWorkflow,
  confirmDraft as confirmWorkflowDraft,
  getDraft as getWorkflowDraft,
  updateDraft as updateWorkflowDraft,
} from '../api/v2/aiGeneration'
import MathText from '../components/MathText.vue'
import { useToast } from '../composables/useToast'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const draft = ref<AIGenerationDraft | null>(null)
const loading = ref(true)
const saving = ref(false)
const confirming = ref(false)
const cancelling = ref(false)
const drawerOpen = ref(false)
const editingIndex = ref<number | null>(null)
const questionDraft = ref<AIGenerationDraftQuestion | null>(null)
const workflowId = computed(() => Number(route.params.workflowId))
const editorTitle = computed(() => editingIndex.value === null ? '新增草稿题目' : '编辑草稿题目')
const validCount = computed(() => draft.value?.questions.filter(question => question.validation_status === 'valid').length ?? 0)

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

function cloneQuestion(question: AIGenerationDraftQuestion): AIGenerationDraftQuestion {
  return {
    ...question,
    options: question.options.map(option => ({ ...option })),
  }
}

function emptyQuestion(): AIGenerationDraftQuestion {
  return {
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
  }
}

function addOption() {
  const question = questionDraft.value
  if (!question) return
  const label = String.fromCharCode(65 + question.options.length)
  question.options.push({ label, content: '', is_correct: false })
}

function removeOption(optionIndex: number) {
  const question = questionDraft.value
  if (!question || question.options.length <= 2) return
  question.options.splice(optionIndex, 1)
  question.options.forEach((option, index) => { option.label = String.fromCharCode(65 + index) })
}

function setCorrect(optionIndex: number, checked = true) {
  const question = questionDraft.value
  if (!question) return
  if (question.type === 'single') {
    question.options.forEach((option, index) => { option.is_correct = index === optionIndex })
  } else {
    question.options[optionIndex].is_correct = checked
  }
}

function removeQuestion(index: number) {
  draft.value?.questions.splice(index, 1)
  if (editingIndex.value === index) closeEditor()
}

function addQuestion() {
  editingIndex.value = null
  questionDraft.value = emptyQuestion()
  drawerOpen.value = true
}

function openEditor(index: number) {
  const question = draft.value?.questions[index]
  if (!question) return
  editingIndex.value = index
  questionDraft.value = cloneQuestion(question)
  drawerOpen.value = true
}

function closeEditor() {
  drawerOpen.value = false
  editingIndex.value = null
  questionDraft.value = null
}

function commitEditor() {
  if (!draft.value || !questionDraft.value) return
  const committed = cloneQuestion(questionDraft.value)
  if (editingIndex.value === null) {
    draft.value.questions.push(committed)
  } else {
    draft.value.questions.splice(editingIndex.value, 1, committed)
  }
  closeEditor()
}

function optionSummary(question: AIGenerationDraftQuestion) {
  return `${question.options.length} 个选项`
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
    await ElMessageBox.confirm(
      '入库后会写入正式题库，草稿状态会变更，题目将可用于刷题。确认继续吗？',
      '确认入库',
      { type: 'warning', confirmButtonText: '确认入库', cancelButtonText: '取消' },
    )
    const data = await confirmWorkflowDraft(workflowId.value)
    toast.show('草稿已入库', 'success')
    router.push(`/banks/${data.bank_id}`)
  } catch (err) {
    if (err === 'cancel' || err === 'close') return
    toast.show(err instanceof Error ? err.message : '确认失败', 'error')
  } finally {
    confirming.value = false
  }
}

async function cancelDraft() {
  cancelling.value = true
  try {
    await ElMessageBox.confirm(
      '撤销后该草稿会变为已取消；如果这是未入库的新建题库，空题库壳也会被删除。确定撤销吗？',
      '撤销草稿',
      { type: 'warning', confirmButtonText: '撤销草稿', cancelButtonText: '取消' },
    )
    await cancelWorkflow(workflowId.value, '用户在草稿页撤销')
    toast.show('草稿已撤销', 'success')
    router.push('/banks/generation-jobs')
  } catch (err) {
    if (err === 'cancel' || err === 'close') return
    toast.show(err instanceof Error ? err.message : '撤销失败', 'error')
  } finally {
    cancelling.value = false
  }
}

onMounted(load)
</script>

<template>
  <section v-loading="loading" class="qp-page" element-loading-text="加载中...">
    <template v-if="draft">
      <div class="qp-section">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 class="qp-title">确认 AI 草稿</h1>
            <p class="qp-subtitle">{{ draft.validation_summary || '请检查题目后确认入库。' }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <el-button type="danger" plain :loading="cancelling" @click="cancelDraft">撤销草稿</el-button>
            <el-button :loading="saving" @click="save">保存草稿</el-button>
            <el-button type="primary" :loading="confirming" @click="confirm">确认入库</el-button>
          </div>
        </div>
        <el-descriptions class="mt-3" :column="4" size="small" border>
          <el-descriptions-item label="Workflow">#{{ draft.workflow_id }}</el-descriptions-item>
          <el-descriptions-item label="状态">{{ draft.status }}</el-descriptions-item>
          <el-descriptions-item label="题目">{{ draft.questions.length }}</el-descriptions-item>
          <el-descriptions-item label="有效">{{ validCount }}</el-descriptions-item>
        </el-descriptions>
        <el-form-item class="mt-3" label="题库描述">
          <el-input v-model="draft.bank_description" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </div>

      <div class="qp-section">
        <div class="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h2 class="qp-section-title">草稿题目</h2>
          <el-button @click="addQuestion">添加题目</el-button>
        </div>
        <el-table :data="draft.questions" size="small" border empty-text="暂无题目">
          <el-table-column type="index" label="#" width="54" />
          <el-table-column label="题型" width="82">
            <template #default="{ row }: { row: AIGenerationDraftQuestion }">
              <el-tag size="small" :type="row.type === 'single' ? 'primary' : 'warning'">{{ row.type === 'single' ? '单选' : '多选' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="题干" min-width="320">
            <template #default="{ row }: { row: AIGenerationDraftQuestion }">
              <MathText as="span" class="line-clamp-2" :text="row.stem || '未填写题干'" />
            </template>
          </el-table-column>
          <el-table-column label="选项" width="90">
            <template #default="{ row }: { row: AIGenerationDraftQuestion }">{{ optionSummary(row) }}</template>
          </el-table-column>
          <el-table-column label="校验" width="120">
            <template #default="{ row }: { row: AIGenerationDraftQuestion }">
              <el-tag size="small" :type="row.validation_status === 'valid' ? 'success' : 'danger'">{{ row.validation_status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="130" align="right" fixed="right">
            <template #default="{ $index }: { $index: number }">
              <div class="flex items-center justify-end gap-1">
                <el-button text size="small" @click="openEditor($index)">编辑</el-button>
                <el-button text type="danger" size="small" @click="removeQuestion($index)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="qp-section flex flex-wrap justify-end gap-2">
        <el-button type="danger" plain :loading="cancelling" @click="cancelDraft">撤销草稿</el-button>
        <el-button @click="addQuestion">添加题目</el-button>
        <el-button :loading="saving" @click="save">保存草稿</el-button>
        <el-button type="primary" :loading="confirming" @click="confirm">确认入库</el-button>
      </div>

      <el-drawer v-model="drawerOpen" :title="editorTitle" size="680px" @closed="questionDraft = null; editingIndex = null">
        <el-form v-if="questionDraft" class="grid gap-3" label-position="top">
          <div class="flex items-center gap-2">
            <el-tag v-if="editingIndex !== null" size="small" type="info">#{{ editingIndex + 1 }}</el-tag>
            <el-tag v-else size="small" type="info">新题目</el-tag>
            <el-select v-model="questionDraft.type" size="small" style="width: 100px" @change="questionDraft.options.forEach((option, index) => { option.is_correct = index === 0 })">
              <el-option value="single" label="单选" />
              <el-option value="multiple" label="多选" />
            </el-select>
          </div>
          <el-form-item label="题干">
            <el-input v-model="questionDraft.stem" type="textarea" :rows="5" />
          </el-form-item>
          <div class="grid gap-2">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-slate-700">选项</span>
              <el-button size="small" @click="addOption">添加选项</el-button>
            </div>
            <div v-for="(option, oIndex) in questionDraft.options" :key="oIndex" class="grid grid-cols-[44px_64px_minmax(0,1fr)_56px] items-center gap-2">
              <el-radio
                v-if="questionDraft.type === 'single'"
                :model-value="questionDraft.options.findIndex(item => item.is_correct)"
                :value="oIndex"
                @change="() => setCorrect(oIndex)"
              />
              <el-checkbox v-else :model-value="option.is_correct" @change="(checked: string | number | boolean) => setCorrect(oIndex, Boolean(checked))" />
              <el-input v-model="option.label" size="small" style="width: 64px" />
              <el-input v-model="option.content" size="small" placeholder="选项内容" class="flex-1" />
              <el-button text size="small" @click="removeOption(oIndex)">移除</el-button>
            </div>
          </div>
          <el-form-item label="解析">
            <el-input v-model="questionDraft.explanation" type="textarea" :rows="4" />
          </el-form-item>
          <el-alert v-if="questionDraft.validation_message" :title="questionDraft.validation_message" type="warning" show-icon :closable="false" />
          <div class="flex justify-end gap-2">
            <el-button @click="closeEditor">关闭</el-button>
            <el-button type="primary" @click="commitEditor">确定</el-button>
          </div>
        </el-form>
      </el-drawer>
    </template>

    <el-empty v-if="!draft && !loading" description="草稿不存在" />
  </section>
</template>
