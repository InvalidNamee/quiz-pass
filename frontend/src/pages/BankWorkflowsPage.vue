<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Page, QuestionBankV2 } from '../api/types'
import { listBankWorkflows, type WorkflowListItem } from '../api/v2/aiGeneration'
import { getBank } from '../api/v2/banks'
import WorkflowTable from '../components/WorkflowTable.vue'
import WorkflowDetailDrawer from '../components/WorkflowDetailDrawer.vue'
import { isUnstableWorkflowStatus } from '../utils/generationStatus'
import { useAuthStore } from '../stores/auth'
import { Eye } from '@lucide/vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const bank = ref<QuestionBankV2 | null>(null)
const workflows = ref<WorkflowListItem[]>([])
const pageInfo = ref<Page<WorkflowListItem> | null>(null)
const status = ref('')
const loading = ref(true)
const detailDrawerVisible = ref(false)
const detailTarget = ref<WorkflowListItem | null>(null)
let pollingTimer: number | null = null

const bankId = () => Number(route.params.bankId)

function hasUnstableWorkflows() {
  return workflows.value.some((workflow) => isUnstableWorkflowStatus(workflow.status))
}

function stopPolling() {
  if (pollingTimer !== null) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

function syncPolling() {
  if (!hasUnstableWorkflows()) {
    stopPolling()
    return
  }
  if (pollingTimer === null) {
    pollingTimer = window.setInterval(() => {
      if (hasUnstableWorkflows()) void load(true)
      else stopPolling()
    }, 3000)
  }
}

async function load(silent = false) {
  status.value = String(route.query.status || '')
  if (!silent) loading.value = true
  try {
    const [bankData, workflowData] = await Promise.all([
      bank.value?.id === bankId() ? Promise.resolve(bank.value) : getBank(bankId()),
      listBankWorkflows(bankId(), { page: Number(route.query.page || 1), status: status.value || undefined }),
    ])
    bank.value = bankData
    pageInfo.value = workflowData
    workflows.value = workflowData.items
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

function canOpenDetail(row: WorkflowListItem) {
  return row.user_id === auth.user?.id
}

function openDetail(row: WorkflowListItem) {
  detailTarget.value = row
  detailDrawerVisible.value = true
}

onMounted(load)
watch(() => route.fullPath, () => { void load() })
watch(workflows, syncPolling, { deep: true })
onBeforeUnmount(stopPolling)
</script>

<template>
  <section class="qp-page">
    <div class="qp-titlebar">
      <div>
        <h1 class="qp-title">工作流日志</h1>
        <p v-if="bank" class="m-0 text-sm text-slate-500">{{ bank.title }}</p>
      </div>
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
          <el-option value="cancelled">已取消</el-option>
        </el-select>
        <el-button size="small" type="primary" @click="applyFilters()">筛选</el-button>
        <RouterLink v-if="bank" :to="`/banks/${bank.id}`"><el-button size="small">返回题库</el-button></RouterLink>
      </div>
    </div>

    <WorkflowTable :workflows="workflows" :loading="loading" :show-source-file="false" show-actions>
      <template #actions="{ row }">
        <el-tooltip v-if="canOpenDetail(row)" content="查看详情" placement="top">
          <el-button size="small" class="qp-icon-button is-blue" @click="openDetail(row)">
            <Eye :size="16" />
          </el-button>
        </el-tooltip>
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

    <WorkflowDetailDrawer
      v-model="detailDrawerVisible"
      :workflow="detailTarget"
      :show-actions="false"
    />
  </section>
</template>
