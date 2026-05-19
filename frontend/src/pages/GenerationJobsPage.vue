<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Page } from '../api/types'
import { listWorkflows, type WorkflowListItem } from '../api/v2/aiGeneration'

const route = useRoute()
const router = useRouter()
const jobs = ref<WorkflowListItem[]>([])
const status = ref('')
const pageInfo = ref<Page<WorkflowListItem> | null>(null)
const loading = ref(true)

async function load() {
  status.value = String(route.query.status || '')
  loading.value = true
  try {
    const data = await listWorkflows({ page: Number(route.query.page || 1), status: status.value || undefined })
    pageInfo.value = data
    jobs.value = data.items
  } finally {
    loading.value = false
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

onMounted(load)
watch(() => route.fullPath, load)
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
          <span v-if="row.error_message" class="text-xs text-red-600">{{ row.error_message }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <RouterLink v-if="row.can_confirm" :to="`/ai-generation/workflows/${row.id}/draft`">
            <el-button size="small" type="primary">确认草稿</el-button>
          </RouterLink>
          <RouterLink v-if="row.bank_id" :to="`/banks/${row.bank_id}`">
            <el-button size="small">查看题库</el-button>
          </RouterLink>
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
  </section>
</template>
