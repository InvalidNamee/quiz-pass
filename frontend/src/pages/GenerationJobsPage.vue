<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import type { AIProviderConfig, Page } from '../api/types'
import { cancelWorkflow, listWorkflows, retryWorkflow, type WorkflowListItem } from '../api/v2/aiGeneration'
import { listAIConfigs } from '../api/v2/users'
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
const retryFile = ref<File | null>(null)
const retryForm = ref({
  aiProviderConfigId: '',
  generationMode: 'knowledge_generate',
  useQuestionCount: false,
  questionCount: 10,
  generateDescription: false,
  extraInstruction: '',
  inheritContext: true,
  sourceText: '',
  title: '',
  desiredVisibility: 'private',
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

function statusBadge(value: string): 'default' | 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<string, 'default' | 'success' | 'warning' | 'danger' | 'info'> = {
    pending: 'default',
    processing: 'info',
    extracting_document: 'info',
    calling_model: 'info',
    validating: 'info',
    repairing: 'warning',
    draft_ready: 'warning',
    imported: 'success',
    succeeded: 'success',
    failed: 'danger',
    cancelled: 'default',
  }
  return map[value] || 'default'
}

function statusText(value: string) {
  const map: Record<string, string> = {
    pending: '等待生成',
    processing: '生成中',
    extracting_document: '提取文档',
    calling_model: '调用模型',
    validating: '校验中',
    repairing: '自动修复',
    draft_ready: '草稿待确认',
    imported: '已入库',
    succeeded: '生成成功',
    failed: '生成失败',
    cancelled: '已取消',
  }
  return map[value] || value
}

function typeText(item: WorkflowListItem) {
  const mode = item.generation_mode === 'bank_parse' ? '题库解析' : '知识库生成'
  const purpose = item.purpose === 'extend_bank' ? '扩展题库' : '新建题库'
  return `${purpose} · ${mode}`
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
    sourceText: row.source_text_snapshot || '',
    title: row.bank_title_snapshot || '重新生成题库',
    desiredVisibility: 'private',
  }
  retryFile.value = null
  retryDialogVisible.value = true
}

function onRetryUploadChange(uploadFile: { raw?: File }) {
  retryFile.value = uploadFile.raw ?? null
}

function onRetryUploadRemove() {
  retryFile.value = null
}

async function submitRetry() {
  if (!retryTarget.value) return
  if (!retryFile.value && !retryForm.value.sourceText.trim()) {
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
    if (retryTarget.value.purpose === 'create_bank') {
      form.set('title', retryForm.value.title || '重新生成题库')
      form.set('desired_visibility', retryForm.value.desiredVisibility)
    }
    if (retryFile.value) form.set('file', retryFile.value)
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
    await cancelWorkflow(row.id, '用户在生成队列撤销')
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
      <h1 class="qp-title">生成队列</h1>
      <div class="flex flex-wrap gap-2">
        <el-select v-model="status" size="small" placeholder="全部状态" style="width: 160px">
          <el-option value="">全部状态</el-option>
          <el-option value="pending">等待生成</el-option>
          <el-option value="calling_model">调用模型</el-option>
          <el-option value="validating">校验中</el-option>
          <el-option value="repairing">自动修复</el-option>
          <el-option value="draft_ready">草稿待确认</el-option>
          <el-option value="imported">已入库</el-option>
          <el-option value="failed">生成失败</el-option>
        </el-select>
        <el-button size="small" type="primary" @click="applyFilters()">筛选</el-button>
      </div>
    </div>

    <el-table v-loading="loading" :data="jobs" size="small" empty-text="暂无生成任务">
      <el-table-column label="#" width="70">
        <template #default="{ row }">
          <span class="font-medium">#{{ row.id }}</span>
        </template>
      </el-table-column>
      <el-table-column label="类型" min-width="140">
        <template #default="{ row }">
          <el-tag>{{ typeText(row) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag v-if="statusBadge(row.status) === 'default'">{{ statusText(row.status) }}</el-tag>
          <el-tag v-else :type="statusBadge(row.status)">{{ statusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="源文件" min-width="140">
        <template #default="{ row }">
          <span class="text-xs">{{ row.source_file_name || '未记录' }}</span>
        </template>
      </el-table-column>
      <el-table-column label="详情" width="180">
        <template #default="{ row }">
          <div class="flex flex-wrap gap-x-2 gap-y-0.5">
            <span v-if="row.draft_question_count" class="text-xs text-slate-400">{{ row.draft_question_count }} 题</span>
            <span v-if="row.repair_attempts" class="text-xs text-slate-400">修复{{ row.repair_attempts }}次</span>
            <span v-if="row.ai_model_snapshot" class="text-xs text-slate-400">{{ row.ai_model_snapshot }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="错误信息" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <el-popover v-if="row.error_message" placement="top" width="520" trigger="click">
            <pre class="max-h-72 overflow-auto whitespace-pre-wrap text-xs text-red-700">{{ row.error_message }}</pre>
            <template #reference>
              <el-button link type="danger" size="small">查看错误</el-button>
            </template>
          </el-popover>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <div class="flex flex-wrap gap-1">
            <RouterLink v-if="row.can_confirm" :to="`/ai-generation/workflows/${row.id}/draft`">
              <el-button size="small" type="primary">确认草稿</el-button>
            </RouterLink>
            <el-button v-if="row.status === 'failed'" size="small" @click="openRetry(row)">重新生成</el-button>
            <el-button v-if="row.status === 'failed' || row.status === 'draft_ready'" size="small" type="danger" plain @click="cancelRow(row)">撤销</el-button>
            <RouterLink v-if="row.bank_id" :to="`/banks/${row.bank_id}`">
              <el-button size="small">查看题库</el-button>
            </RouterLink>
          </div>
        </template>
      </el-table-column>
    </el-table>

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
        <div class="grid gap-3 sm:grid-cols-2">
          <el-form-item label="AI 模型">
            <el-select v-model="retryForm.aiProviderConfigId" class="w-full">
              <el-option v-for="config in configs" :key="config.id" :value="String(config.id)" :label="configLabel(config)" />
            </el-select>
          </el-form-item>
          <el-form-item label="生成模式">
            <el-select v-model="retryForm.generationMode" class="w-full">
              <el-option value="knowledge_generate" label="从知识库生成" />
              <el-option value="bank_parse" label="从题库解析" />
            </el-select>
          </el-form-item>
        </div>
        <div v-if="retryTarget?.purpose === 'create_bank'" class="grid gap-3 sm:grid-cols-2">
          <el-form-item label="题库名称"><el-input v-model="retryForm.title" /></el-form-item>
          <el-form-item label="入库后可见性">
            <el-select v-model="retryForm.desiredVisibility" class="w-full">
              <el-option value="private" label="私有" />
              <el-option value="public" label="公开" />
            </el-select>
          </el-form-item>
        </div>
        <div class="grid gap-3 sm:grid-cols-2">
          <el-form-item v-if="retryForm.generationMode === 'knowledge_generate'" label="题数">
            <el-checkbox v-model="retryForm.useQuestionCount">指定题数</el-checkbox>
          </el-form-item>
          <el-form-item v-if="retryForm.generationMode === 'knowledge_generate' && retryForm.useQuestionCount" label="题目数量">
            <el-input-number v-model="retryForm.questionCount" :min="1" :max="100" />
          </el-form-item>
        </div>
        <el-form-item v-if="retryTarget?.purpose === 'extend_bank'">
          <el-checkbox v-model="retryForm.inheritContext">继承题库 AI 上下文和历史生成摘要</el-checkbox>
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
          <el-upload :auto-upload="false" :limit="1" accept=".txt,.docx,.pdf" :on-change="onRetryUploadChange" :on-remove="onRetryUploadRemove">
            <el-button>选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="retryDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="retrying" @click="submitRetry">重新生成</el-button>
      </template>
    </el-dialog>
  </section>
</template>
