<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import type { AIProviderConfig, Page } from '../api/types'
import { cancelWorkflow, listWorkflows, retryWorkflow, type WorkflowListItem } from '../api/v2/aiGeneration'
import { listAIConfigs } from '../api/v2/users'
import WorkflowTable from '../components/WorkflowTable.vue'
import WorkflowDetailDrawer from '../components/WorkflowDetailDrawer.vue'
import { Ban, Eye, FileCheck2, ExternalLink, RotateCcw } from '@lucide/vue'
import { useToast } from '../composables/useToast'
import { isUnstableWorkflowStatus } from '../utils/generationStatus'

const route = useRoute()
const router = useRouter()
const toast = useToast()
const jobs = ref<WorkflowListItem[]>([])
const status = ref('')
const pageInfo = ref<Page<WorkflowListItem> | null>(null)
const loading = ref(true)
const configs = ref<AIProviderConfig[]>([])
const retryDialogVisible = ref(false)
const retrying = ref(false)
const retryTarget = ref<WorkflowListItem | null>(null)
const detailDrawerVisible = ref(false)
const detailTarget = ref<WorkflowListItem | null>(null)
const retryFiles = ref<File[]>([])
const retryForm = ref({
  aiProviderConfigId: '',
  generationMode: 'knowledge_generate',
  useQuestionCount: false,
  questionCount: 10,
  generateDescription: false,
  extraInstruction: '',
  inheritContext: true,
  includeExistingQuestions: false,
  sourceText: '',
  title: '',
})
let pollingTimer: number | null = null

function hasUnstableJobs() {
  return jobs.value.some((job) => isUnstableWorkflowStatus(job.status))
}

function stopPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function syncPolling() {
  if (!hasUnstableJobs()) {
    stopPolling()
    return
  }
  if (pollingTimer === null) {
    pollingTimer = window.setInterval(() => {
      if (hasUnstableJobs()) void load(true)
      else stopPolling()
    }, 3000)
  }
}

async function load(silent = false) {
  status.value = String(route.query.status || '')
  if (!silent) loading.value = true
  try {
    const data = await listWorkflows({ page: Number(route.query.page || 1), status: status.value || undefined })
    pageInfo.value = data
    jobs.value = data.items
  } finally {
    if (!silent) loading.value = false
  }
}

function applyFilters(page = 1) {
  const query: Record<string, string> = {}
  if (page > 1) query.page = String(page)
  if (status.value) query.status = status.value
  router.push({ query })
}

function configLabel(config: AIProviderConfig) {
  return config.name ? `${config.name} · ${config.model}` : config.model
}

async function openRetry(row: WorkflowListItem) {
  retryTarget.value = row
  if (!configs.value.length) configs.value = await listAIConfigs()
  retryForm.value = {
    aiProviderConfigId: row.ai_provider_config_id ? String(row.ai_provider_config_id) : String(configs.value.find((item) => item.is_default)?.id || configs.value[0]?.id || ''),
    generationMode: row.generation_mode,
    useQuestionCount: Boolean(row.requested_count),
    questionCount: row.requested_count || 10,
    generateDescription: row.generate_description === 'true',
    extraInstruction: row.extra_instruction || '',
    inheritContext: row.inherit_context,
    includeExistingQuestions: row.include_existing_questions,
    sourceText: row.source_text_snapshot || '',
    title: row.bank_title_snapshot || '重新生成题库',
  }
  retryFiles.value = []
  retryDialogVisible.value = true
}

function openDetail(row: WorkflowListItem) {
  detailTarget.value = row
  detailDrawerVisible.value = true
}

function onRetryUploadChange(_uploadFile: { raw?: File }, uploadFiles: Array<{ raw?: File }>) {
  retryFiles.value = uploadFiles.map(item => item.raw).filter((item): item is File => Boolean(item))
}

function onRetryUploadRemove(_uploadFile: unknown, uploadFiles: Array<{ raw?: File }>) {
  retryFiles.value = uploadFiles.map(item => item.raw).filter((item): item is File => Boolean(item))
}

async function submitRetry() {
  if (!retryTarget.value) return
  if (!retryFiles.value.length && !retryForm.value.sourceText.trim()) {
    toast.show('请填写源文本或重新上传文件', 'error')
    return
  }
  retrying.value = true
  try {
    const form = new FormData()
    if (retryForm.value.aiProviderConfigId) form.set('ai_provider_config_id', retryForm.value.aiProviderConfigId)
    form.set('generation_mode', retryForm.value.generationMode)
    form.set('question_count_mode', retryForm.value.useQuestionCount && retryForm.value.generationMode === 'knowledge_generate' ? 'fixed' : 'adaptive')
    if (retryForm.value.useQuestionCount && retryForm.value.generationMode === 'knowledge_generate') form.set('question_count', String(retryForm.value.questionCount))
    form.set('generate_description', String(retryForm.value.generateDescription))
    form.set('extra_instruction', retryForm.value.extraInstruction)
    form.set('inherit_context', String(retryTarget.value.purpose === 'extend_bank' ? retryForm.value.inheritContext : false))
    form.set('include_existing_questions', String(retryTarget.value.purpose === 'extend_bank' ? retryForm.value.includeExistingQuestions : false))
    if (retryTarget.value.purpose === 'create_bank') {
      form.set('title', retryForm.value.title || '重新生成题库')
    }
    if (retryFiles.value.length) retryFiles.value.forEach(item => form.append('files', item))
    else form.set('source_text', retryForm.value.sourceText.trim())
    const data = await retryWorkflow(retryTarget.value.id, form)
    toast.show(`已创建重新生成 workflow #${data.workflow_id}`, 'success')
    retryDialogVisible.value = false
    await load()
  } catch (err) {
    toast.show(err instanceof Error ? err.message : '重新生成失败', 'error')
  } finally {
    retrying.value = false
  }
}

async function cancelRow(row: WorkflowListItem) {
  try {
    await ElMessageBox.confirm('撤销后该生成任务会变为已取消；如果是未入库的新建题库，空题库壳也会被删除。确定继续吗？', '撤销生成任务', {
      confirmButtonText: '撤销',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await cancelWorkflow(row.id, '用户在生成任务撤销')
    toast.show('任务已撤销', 'success')
    await load()
  } catch (err) {
    if (err instanceof Error) toast.show(err.message, 'error')
  }
}

onMounted(load)
watch(() => route.fullPath, () => { void load() })
watch(jobs, syncPolling, { deep: true })
onBeforeUnmount(stopPolling)
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title">生成任务</h1>
        <p class="qp-subtitle">跟踪 AI 生成、重试、撤销和草稿确认状态。</p>
      </div>
    </div>

    <div class="qp-toolbar rounded-2xl border border-slate-100 bg-white p-3 shadow-sm">
      <el-select v-model="status" size="small" placeholder="全部状态" style="width: 160px">
        <el-option value="">全部状态</el-option>
        <el-option value="pending">等待生成</el-option>
        <el-option value="calling_model">调用模型</el-option>
        <el-option value="validating">校验中</el-option>
        <el-option value="repairing">自动修复</el-option>
        <el-option value="draft_ready">草稿待确认</el-option>
        <el-option value="imported">已入库</el-option>
        <el-option value="failed">生成失败</el-option>
        <el-option value="cancelled">已取消</el-option>
      </el-select>
      <el-button size="small" type="primary" @click="applyFilters()">筛选</el-button>
    </div>

    <WorkflowTable :workflows="jobs" :loading="loading" show-actions show-sensitive-error>
      <template #actions="{ row }">
        <div class="qp-icon-actions">
          <el-tooltip content="查看详情" placement="top">
            <el-button size="small" class="qp-icon-button is-blue" @click="openDetail(row)">
              <Eye :size="16" />
            </el-button>
          </el-tooltip>

          <el-tooltip content="确认草稿" placement="top">
            <RouterLink v-if="row.can_confirm" :to="`/ai-generation/workflows/${row.id}/draft`" class="inline-block">
              <el-button size="small" class="qp-icon-button is-green">
                <FileCheck2 :size="16" />
              </el-button>
            </RouterLink>
            <el-button v-else disabled size="small" class="qp-icon-button is-green">
              <FileCheck2 :size="16" />
            </el-button>
          </el-tooltip>

          <el-tooltip content="重新生成" placement="top">
            <el-button size="small" :disabled="!row.can_retry" class="qp-icon-button is-amber" @click="openRetry(row)">
              <RotateCcw :size="16" />
            </el-button>
          </el-tooltip>

          <el-tooltip content="撤销" placement="top">
            <el-button size="small" :disabled="!row.can_cancel" class="qp-icon-button is-red" @click="cancelRow(row)">
              <Ban :size="16" />
            </el-button>
          </el-tooltip>

          <el-tooltip content="查看题库" placement="top">
            <RouterLink v-if="row.bank_id" :to="`/banks/${row.bank_id}`" class="inline-block">
              <el-button size="small" class="qp-icon-button">
                <ExternalLink :size="16" />
              </el-button>
            </RouterLink>
            <el-button v-else disabled size="small" class="qp-icon-button">
              <ExternalLink :size="16" />
            </el-button>
          </el-tooltip>
        </div>
      </template>
    </WorkflowTable>

    <el-pagination
      v-if="pageInfo"
      background
      size="small"
      :current-page="pageInfo.page"
      :page-count="pageInfo.total_pages || 1"
      :total="pageInfo.total"
      layout="prev, pager, next, total"
      @current-change="applyFilters"
    />

    <el-dialog v-model="retryDialogVisible" title="重新生成" width="760px" top="5vh">
      <el-form label-position="top">
        <el-form-item label="生成模式">
          <el-radio-group v-model="retryForm.generationMode">
            <el-radio-button value="knowledge_generate">从知识库生成</el-radio-button>
            <el-radio-button value="bank_parse">从题库解析</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="retryTarget?.purpose === 'create_bank'" label="题库名称">
          <el-input v-model="retryForm.title" placeholder="重新生成题库" />
        </el-form-item>

        <div class="grid gap-3 sm:grid-cols-2">
          <el-form-item label="AI 模型">
            <el-select v-model="retryForm.aiProviderConfigId" class="w-full">
              <el-option v-for="config in configs" :key="config.id" :value="String(config.id)" :label="configLabel(config)" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="retryForm.generationMode === 'knowledge_generate'" label="题数">
            <el-checkbox v-model="retryForm.useQuestionCount">指定题数</el-checkbox>
          </el-form-item>
          <el-form-item v-if="retryForm.generationMode === 'knowledge_generate' && retryForm.useQuestionCount" label="题目数量">
            <el-input-number v-model="retryForm.questionCount" :min="1" :max="100" />
          </el-form-item>
        </div>
        <el-form-item v-if="retryTarget?.purpose === 'extend_bank'">
          <el-checkbox v-model="retryForm.inheritContext">使用题库 AI 描述</el-checkbox>
        </el-form-item>
        <el-form-item v-if="retryTarget?.purpose === 'extend_bank'">
          <el-checkbox v-model="retryForm.includeExistingQuestions">附带已有题目题干给 AI</el-checkbox>
        </el-form-item>
        <el-form-item v-if="retryForm.generationMode === 'knowledge_generate'">
          <el-checkbox v-model="retryForm.generateDescription">让 AI 生成题库描述</el-checkbox>
        </el-form-item>
        <el-form-item label="额外指令">
          <el-input v-model="retryForm.extraInstruction" type="textarea" :rows="3" maxlength="2000" show-word-limit />
        </el-form-item>
        <el-form-item label="源文本">
          <el-input v-model="retryForm.sourceText" type="textarea" :rows="8" placeholder="可直接编辑上次提取文本；也可以上传新文件替换" />
        </el-form-item>
        <el-form-item label="替换文件（可选）">
          <el-upload
            :auto-upload="false"
            :limit="20"
            multiple
            accept=".txt,.docx,.pdf"
            :on-change="onRetryUploadChange"
            :on-remove="onRetryUploadRemove"
          >
            <el-button>选择文件</el-button>
            <template #tip><span class="ml-2 text-sm text-slate-500">支持 .txt / .docx / .pdf，可上传多个文件；上传后将替换上方源文本。</span></template>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="retryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="retrying" @click="submitRetry">重新生成</el-button>
      </template>
    </el-dialog>

    <WorkflowDetailDrawer
      v-model="detailDrawerVisible"
      :workflow="detailTarget"
      @retry="openRetry"
      @cancel="cancelRow"
    />
  </section>
</template>
