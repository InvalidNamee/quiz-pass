<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import type { AIGenerationDraft } from '../api/types'
import {
  cancelWorkflow,
  confirmDraft as confirmWorkflowDraft,
  getDraft as getWorkflowDraft,
  updateDraft as updateWorkflowDraft,
} from '../api/v2/aiGeneration'
import { useToast } from '../composables/useToast'
import QuestionEditorDrawer from '../features/questions/QuestionEditorDrawer.vue'
import QuestionTable from '../features/questions/QuestionTable.vue'
import { emptyQuestionForm, formToDraftQuestion, questionToForm, type QuestionForm } from '../features/questions/questionForm'
import { Pencil, Trash2 } from '@lucide/vue'

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
const editorInitialQuestion = ref<QuestionForm>(emptyQuestionForm())
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

function removeQuestion(index: number) {
  draft.value?.questions.splice(index, 1)
  if (editingIndex.value === index) closeEditor()
  toast.show('已移除题目', 'info')
}

function addQuestion() {
  editingIndex.value = null
  editorInitialQuestion.value = emptyQuestionForm()
  drawerOpen.value = true
}

function openEditor(index: number) {
  const question = draft.value?.questions[index]
  if (!question) return
  editingIndex.value = index
  editorInitialQuestion.value = questionToForm(question)
  drawerOpen.value = true
}

function closeEditor() {
  drawerOpen.value = false
  editingIndex.value = null
  editorInitialQuestion.value = emptyQuestionForm()
}

function commitEditor(form: QuestionForm) {
  if (!draft.value) return
  const base = editingIndex.value === null ? null : draft.value.questions[editingIndex.value]
  const committed = formToDraftQuestion(form, base)
  if (editingIndex.value === null) {
    draft.value.questions.push(committed)
  } else {
    draft.value.questions.splice(editingIndex.value, 1, committed)
  }
  closeEditor()
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
      '导入题库后，题目将可用于刷题，草稿将不能再编辑。确认继续吗？',
      '导入题库',
      { type: 'warning', confirmButtonText: '导入题库', cancelButtonText: '取消' },
    )
    const data = await confirmWorkflowDraft(workflowId.value)
    toast.show('已导入题库', 'success')
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
            <p class="qp-subtitle">{{ draft.validation_summary || '请检查题目后确认导入。' }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <el-button type="danger" plain :loading="cancelling" @click="cancelDraft">撤销草稿</el-button>
            <el-button :loading="saving" @click="save">保存草稿</el-button>
            <el-button type="primary" :loading="confirming" @click="confirm">导入题库</el-button>
          </div>
        </div>
        <el-descriptions class="mt-3" :column="4" size="small" border>
          <el-descriptions-item label="任务">#{{ draft.workflow_id }}</el-descriptions-item>
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
        <QuestionTable :questions="draft.questions" show-validation empty-text="暂无题目">
          <template #actions="{ index }">
            <div class="qp-icon-actions">
              <el-tooltip content="编辑" placement="top">
                <el-button size="small" class="qp-icon-button is-blue" @click="openEditor(index)">
                  <Pencil :size="16" />
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button size="small" class="qp-icon-button is-red" @click="removeQuestion(index)">
                  <Trash2 :size="16" />
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </QuestionTable>
      </div>

      <div class="qp-section flex flex-wrap justify-end gap-2">
        <el-button type="danger" plain :loading="cancelling" @click="cancelDraft">撤销草稿</el-button>
        <el-button @click="addQuestion">添加题目</el-button>
        <el-button :loading="saving" @click="save">保存草稿</el-button>
        <el-button type="primary" :loading="confirming" @click="confirm">导入题库</el-button>
      </div>

      <QuestionEditorDrawer
        v-model="drawerOpen"
        :title="editorTitle"
        :initial-question="editorInitialQuestion"
        :confirm-text="editingIndex === null ? '添加到草稿' : '更新草稿题目'"
        @confirm="commitEditor"
      />
    </template>

    <el-empty v-if="!draft && !loading" description="草稿不存在" />
  </section>
</template>
